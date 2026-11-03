"""Independent Python arithmetic/short-circuit auditor. No sampler imports."""
import json,pathlib,sys,hashlib,importlib.util
import z3
sys.setrecursionlimit(200000)
ROOT=pathlib.Path(__file__).resolve().parents[2]
OPS={getattr(z3,'Z3_OP_'+k):v for k,v in [('AND','and'),('OR','or'),('NOT','not'),('IMPLIES','implies'),('XOR','xor'),('ITE','ite'),('EQ','eq'),('DISTINCT','distinct'),('LE','le'),('LT','lt'),('GE','ge'),('GT','gt'),('ADD','add'),('MUL','mul'),('SUB','sub'),('UMINUS','neg'),('IDIV','div'),('MOD','mod')]}
def export(root,sha='synthetic'):
    ns=[];ids={};todo=[root]
    while todo:
        e=todo.pop()
        if e.get_id() in ids:continue
        ids[e.get_id()]=len(ns);ns.append(e);todo.extend(reversed(e.children()))
    vs=sorted([e for e in ns if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED],key=lambda e:str(e.decl().name()));vi={e.get_id():i for i,e in enumerate(vs)}
    out={'input_sha':sha,'variables':[{'name':str(e.decl().name()),'sort':str(e.sort())} for e in vs],'nodes':[]}
    for e in ns:
        n={'sort':str(e.sort()),'children':[ids[c.get_id()] for c in e.children()]}
        if z3.is_int_value(e) or z3.is_true(e) or z3.is_false(e):n.update(op='const',value=str(e.as_long() if z3.is_int_value(e) else int(z3.is_true(e))))
        elif e.get_id() in vi:n.update(op='var',variable=vi[e.get_id()])
        else:n['op']=OPS.get(e.decl().kind(),'unknown')
        out['nodes'].append(n)
    return out,ns,vs

def evaluate(ast,model):
    vals={};nodes=ast['nodes']
    def ev(i):
        if i in vals:return vals[i]
        n=nodes[i];op=n['op'];cs=n['children']
        if op=='const':v=int(n['value'])
        elif op=='var':v=int(model[n['variable']])
        elif op=='and':v=int(all(ev(c)!=0 for c in cs))
        elif op=='or':v=int(any(ev(c)!=0 for c in cs))
        elif op=='ite':v=ev(cs[1] if ev(cs[0]) else cs[2])
        else:
            a=[ev(c) for c in cs]
            if op=='not':v=int(not a[0])
            elif op=='implies':v=int(not a[0] or bool(a[1]))
            elif op=='xor':v=sum(bool(x) for x in a)%2
            elif op=='eq':v=int(len(set(a))==1)
            elif op=='distinct':v=int(len(set(a))==len(a))
            elif op=='le':v=int(all(x<=y for x,y in zip(a,a[1:])))
            elif op=='lt':v=int(all(x<y for x,y in zip(a,a[1:])))
            elif op=='ge':v=int(all(x>=y for x,y in zip(a,a[1:])))
            elif op=='gt':v=int(all(x>y for x,y in zip(a,a[1:])))
            elif op=='add':v=sum(a)
            elif op=='mul':
                v=1
                for x in a:v*=x
            elif op=='sub':v=a[0]-sum(a[1:])
            elif op=='neg':v=-a[0]
            elif op=='div':v=a[0]//a[1] if a[1]>0 else -(a[0]//-a[1])
            elif op=='mod':v=a[0]%abs(a[1])
            else:raise ValueError(op)
        vals[i]=v;return v
    legal=ev(0)!=0
    trace={i:(int(v)&((1<<(1 if nodes[i]['sort']=='Bool' else 64))-1),int(v)) for i,v in vals.items()}
    return legal,trace

def observations(ast,m):
    legal,trace=evaluate(ast,m);s=set()
    for i,(bits,_) in trace.items():
        for b in range(1 if ast['nodes'][i]['sort']=='Bool' else 64):s.add((i,b,(bits>>b)&1))
    return legal,s

def covered(s):return sum((i,b,1-v) in s for i,b,v in s)//2

def metric_module():
    p=ROOT/'worktrees/baseline/HighDiv/my_scripts/calc_metric.py';sp=importlib.util.spec_from_file_location('frozen_official_metric',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def official_trace(root,values):
    m=metric_module();ids={e.get_id():i for i,e in enumerate(export(root)[1])}
    class Stats:
        def __init__(self):self.values={}
        def register_node(self,i,t):pass
        def evaluate_node(self,i,v):self.values[ids[i]]=int(v)
    obj=m.ManualSatisfiesMetric.__new__(m.ManualSatisfiesMetric);obj._statistics=Stats();f=obj._build_evaluator(root);valid=f(values);return bool(valid),obj._statistics.values
