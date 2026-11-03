"""Independent exact integer-domain certificates. No C++ domain calls and no solver checks.
Supports the frozen AST operations, affine terms, invariant nonlinear numeric terms,
all Boolean domain operations supported by LineDomain; full interval identities.
"""
import json,sys,pathlib,itertools,math
NINF=float('-inf');PINF=float('inf');ALL=[(NINF,PINF)]
def normalize(xs):
 out=[]
 for l,h in sorted(xs):
  if l>h:continue
  if out and l<=out[-1][1]+1:out[-1]=(out[-1][0],max(h,out[-1][1]))
  else:out.append((l,h))
 return out
def union(a,b):return normalize(a+b)
def intersection(a,b):return normalize([(max(l,u),min(h,v)) for l,h in a for u,v in b if max(l,u)<=min(h,v)])
def complement(a):
 out=[];cursor=NINF
 for l,h in a:
  if l!=NINF and cursor<=l-1:out.append((cursor,l-1))
  if h==PINF:return out
  cursor=h+1
 if cursor!=PINF:out.append((cursor,PINF))
 return out
def packed(a):return [[('-inf' if l==NINF else str(l)),('+inf' if h==PINF else str(h))] for l,h in a]
def unpacked(a):return [(NINF if l=='-inf' else int(l),PINF if h=='+inf' else int(h)) for l,h in a]
def atomic(c,s,eq):
 if s==0:return ALL.copy() if (c==0 if eq else c<=0) else []
 if eq:return [(-c//s,-c//s)] if (-c)%s==0 else []
 return [(NINF,(-c)//s)] if s>0 else [(-((-(-c))//s),PINF)] # ceil((-c)/s) = -(c//s)
def nearest(u):
 candidates=[]
 for l,h in u:
  if h>=1 and max(1,l)<=h:candidates.append(max(1,l))
  if l<=-1 and min(-1,h)>=l:candidates.append(min(-1,h))
 return min(candidates,key=lambda x:(abs(x),x)) if candidates else None
class IndependentDomains:
 def __init__(self,ast,anchor,direction):
  self.ast=ast;self.ns=ast['nodes'];self.m=list(map(int,anchor));self.d={int(v):int(c) for v,c in direction if int(c)};self.deps={};self.poly={};self.values={};self.domains={};self.records={}
  seen=set();self.post=[]
  for root in range(len(self.ns)):
   todo=[(root,False)]
   while todo:
    n,ready=todo.pop()
    if n in seen:continue
    if not ready:todo.append((n,True));todo.extend((c,False) for c in reversed(self.ns[n]['children']))
    else:seen.add(n);self.post.append(n)
  for i in self.post:
   n=self.ns[i];cs=n['children'];op=n['op'];self.deps[i]=set().union(*(self.deps[c] for c in cs)) if cs else set()
   if op=='var':self.deps[i].add(n['variable'])
   p=None
   if n['sort']!='Bool':
    if op=='const':p=(int(n['value']),{})
    elif op=='var':p=(0,{n['variable']:1})
    elif op in ['add','sub','neg'] and all(self.poly[c] is not None for c in cs):
     k=0;coeff={}
     for j,c in enumerate(cs):
      sign=-1 if op=='neg' or op=='sub' and j>0 else 1;a,b=self.poly[c];k+=sign*a
      for v,x in b.items():coeff[v]=coeff.get(v,0)+sign*x
     p=(k,{v:x for v,x in coeff.items() if x})
    elif op=='mul' and all(self.poly[c] is not None for c in cs):
     factor=1;nonconstant=[]
     for c in cs:
      a,b=self.poly[c]
      if b:nonconstant.append((a,b))
      else:factor*=a
     if len(nonconstant)<=1:
      a,b=nonconstant[0] if nonconstant else (1,{})
      p=(factor*a,{v:factor*x for v,x in b.items() if factor*x})
   self.poly[i]=p
 def value(self,i):
  if i in self.values:return self.values[i]
  n=self.ns[i];cs=n['children'];op=n['op']
  if op=='const':v=int(n['value'])
  elif op=='var':v=self.m[n['variable']]
  elif op=='and':v=int(all(self.value(c) for c in cs))
  elif op=='or':v=int(any(self.value(c) for c in cs))
  elif op=='ite':v=self.value(cs[1] if self.value(cs[0]) else cs[2])
  else:
   a=[self.value(c) for c in cs]
   if op=='not':v=int(not a[0])
   elif op=='implies':v=int(not a[0] or bool(a[1]))
   elif op=='xor':v=sum(bool(x) for x in a)%2
   elif op=='eq':v=int(len(set(a))==1)
   elif op=='distinct':v=int(len(set(a))==len(a))
   elif op in ['le','lt','ge','gt']:v=int(all({'le':x<=y,'lt':x<y,'ge':x>=y,'gt':x>y}[op] for x,y in zip(a,a[1:])))
   elif op=='add':v=sum(a)
   elif op=='sub':v=a[0]-sum(a[1:])
   elif op=='neg':v=-a[0]
   elif op=='mul':v=math.prod(a)
   elif op=='div':v=a[0]//a[1] if a[1]>0 else -(a[0]//-a[1])
   elif op=='mod':v=a[0]%abs(a[1])
   else:raise NotImplementedError(op)
  self.values[i]=v;return v
 def term(self,i):
  p=self.poly[i]
  if p is not None:
   a,cs=p;return a+sum(c*self.m[v] for v,c in cs.items()),sum(c*self.d.get(v,0) for v,c in cs.items())
  assert not (self.deps[i]&self.d.keys()),('unsupported moving numeric',i)
  return self.value(i),0
 def domain(self,i=0):
  if i in self.domains:return self.domains[i]
  n=self.ns[i];op=n['op'];cs=n['children'];invariant=not bool(self.deps[i]&self.d.keys());comparisons=[]
  if invariant:u=ALL.copy() if self.value(i) else []
  else:
   children={c:self.domain(c) for c in cs if self.ns[c]['sort']=='Bool'}
   if op=='and':
    u=ALL.copy()
    for c in cs:u=intersection(u,children[c])
   elif op=='or':
    u=[]
    for c in cs:u=union(u,children[c])
   elif op=='not':u=complement(children[cs[0]])
   elif op=='implies':u=union(complement(children[cs[0]]),children[cs[1]])
   elif op=='xor':
    u=[]
    for c in cs:u=union(intersection(u,complement(children[c])),intersection(complement(u),children[c]))
   elif op=='ite':u=union(intersection(children[cs[0]],children[cs[1]]),intersection(complement(children[cs[0]]),children[cs[2]]))
   elif op in ['eq','distinct','le','lt','ge','gt']:
    u=ALL.copy()
    for l,r in itertools.combinations(range(len(cs)),2):
     if op!='distinct' and r!=l+1:continue
     if self.ns[cs[l]]['sort']=='Bool':
      assert op in ['eq','distinct'];a,b=children[cs[l]],children[cs[r]];atom=union(intersection(a,b),intersection(complement(a),complement(b)))
     else:
      a,da=self.term(cs[l]);b,db=self.term(cs[r]);c,s=a-b,da-db
      if op in ['ge','gt']:c,s=-c,-s
      if op in ['lt','gt']:c+=1
      eq=op in ['eq','distinct'];atom=atomic(c,s,eq)
      comparison={'left':cs[l],'right':cs[r],'constant':str(c),'slope':str(s),'normalized':'eq_zero' if eq else 'le_zero','before_distinct_complement':packed(atom)}
      if s:
       # C++ remainder truncates toward zero; Python % has divisor's sign.
       q=(abs(-c)//abs(s))*(-1 if (-c<0)!=(s<0) else 1)
       comparison.update(floor=str((-c)//s),ceil=str(-(c//s)),remainder=str(-c-q*s))
      comparisons.append(comparison)
     if op=='distinct':atom=complement(atom)
     u=intersection(u,atom)
   else:raise NotImplementedError(op)
  u=normalize(u);self.domains[i]=u;self.records[i]={'node':i,'operation':op,'children':cs,'invariant':invariant,'domain':packed(u),'comparisons':comparisons,'complete':True};return u
 def equalities(self):
  seen=set();todo=[0];rows=[]
  while todo:
   i=todo.pop()
   if i in seen:continue
   seen.add(i);n=self.ns[i];cs=n['children']
   if n['op']=='and':todo.extend(reversed(cs));continue
   if n['op']!='eq' or len(cs)<2 or self.ns[cs[0]]['sort']=='Bool' or any(self.poly[c] is None for c in cs):continue
   for j in cs[1:]:
    a,ac=self.poly[cs[0]];b,bc=self.poly[j];coeff={v:ac.get(v,0)-bc.get(v,0) for v in ac.keys()|bc.keys()};rows.append((i,a-b,{v:c for v,c in coeff.items() if c}))
  return rows
 def audit(self,row):
  u=self.domain();assert any(l<=0<=h for l,h in u),'root excludes legal anchor'
  assert packed(u)==row['root_domain'],'root domain mismatch'
  cert={x['node']:x for x in row['certificate']};assert len(cert)==len(row['certificate']);assert cert==self.records,'certificate mismatch'
  dots=[sum(c*self.d.get(v,0) for v,c in co.items()) for _,_,co in self.equalities()];assert all(x==0 for x in dots);assert list(map(str,dots))==row['all_equality_dots']
  return u
 def summary(self):
  mandatory=set();todo=[0]
  while todo:
   i=todo.pop()
   if i in mandatory:continue
   mandatory.add(i)
   if self.ns[i]['op']=='and':todo.extend(self.ns[i]['children'])
  details=[]
  for i,rec in sorted(self.records.items()):
   for c in rec['comparisons']:
    k,s=int(c['constant']),int(c['slope']);roles=[];u=unpacked(c['before_distinct_complement'])
    if s and c['normalized']=='eq_zero' and u==[(0,0)]:roles.append('nonzero_slope_equality_at_zero')
    if s and c['normalized']=='le_zero':
     if s>0 and (-k)//s==0:roles.append('positive_upper_zero')
     if s<0 and -(k//s)==0:roles.append('negative_lower_zero')
     if k<0 and (('positive_upper_zero' in roles) or ('negative_lower_zero' in roles)):roles.append('positive_slack_integer_rounding')
    if roles:details.append(dict(node=i,scope='mandatory_AND_path' if i in mandatory else 'conditional_boolean_structure',roles=roles,**c))
  return details
if __name__=='__main__':
 data=json.loads(pathlib.Path(sys.argv[1]).read_text());row=json.loads(pathlib.Path(sys.argv[2]).read_text());d=IndependentDomains(data['ast'],row['anchor'],row['coefficients']);d.audit(row);print('verified')
