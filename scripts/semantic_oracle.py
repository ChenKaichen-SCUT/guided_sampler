"""Offline-only exact value and official short-circuit reach construction."""
from common import *
from evaluate_exact import load_metric
import collections
metric=load_metric();z3=metric.z3
def dag(root):
 nodes=[];ids={};todo=[root]
 while todo:
  e=todo.pop()
  if e.get_id() in ids:continue
  ids[e.get_id()]=len(nodes);nodes.append(e);todo.extend(reversed(e.children()))
 return nodes,ids
def variables(nodes):return {str(e.decl().name()):e for e in nodes if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED}
def reach_all(root):
 nodes,ids=dag(root);incoming=[0]*len(nodes);children=[]
 for e in nodes:
  cs=[ids[c.get_id()] for c in e.children()];children.append(cs)
  for c in cs:incoming[c]+=1
 q=collections.deque([0]);reach=[z3.BoolVal(False,ctx=root.ctx) for e in nodes];reach[0]=z3.BoolVal(True,ctx=root.ctx);processed=0
 while q:
  i=q.popleft();processed+=1;e=nodes[i];prefix=reach[i]
  for k,c in enumerate(children[i]):
   edge=prefix if z3.is_and(e) or z3.is_or(e) else z3.And(reach[i],e.arg(0) if k==1 else z3.Not(e.arg(0))) if z3.is_app_of(e,z3.Z3_OP_ITE) and k>0 else reach[i]
   reach[c]=z3.simplify(z3.Or(reach[c],edge));incoming[c]-=1
   if incoming[c]==0:q.append(c)
   if z3.is_and(e):prefix=z3.And(prefix,e.arg(k))
   elif z3.is_or(e):prefix=z3.And(prefix,z3.Not(e.arg(k)))
 assert processed==len(nodes)
 return nodes,reach
def value_condition(e,bit,desired):
 if z3.is_bool(e):assert bit==0;return e if desired else z3.Not(e)
 rem=e % (1<<(bit+1));return rem>=(1<<bit) if desired else rem<(1<<bit)
def parse_expr(s,decls):return z3.parse_smt2_string('(assert '+s+')',decls=decls,ctx=metric.CTX)[0]
class Witness(metric.WireCoverageStatistics):
 def __init__(self):super().__init__();self.current={}
 def evaluate_node(self,n,v):self.current[n]=v;super().evaluate_node(n,v)
def exact_value(e,assignment,decls):
 pairs=[(v,z3.IntVal(assignment[k],ctx=e.ctx) if z3.is_int(v) else z3.BoolVal(bool(assignment[k]),ctx=e.ctx)) for k,v in decls.items()]
 v=z3.simplify(z3.substitute(e,*pairs))
 return int(z3.is_true(v)) if z3.is_bool(v) and (z3.is_true(v) or z3.is_false(v)) else v.as_long() if z3.is_int_value(v) else None
