import sys,pathlib,itertools
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts'))
from semantic_oracle import *
a,b=z3.Bools('a b',ctx=metric.CTX);x=z3.Int('x',ctx=metric.CTX)
forms=[z3.Or(a,b),z3.And(a,b),z3.If(a,x+1,x-1)==0,z3.Or(z3.And(a,b),z3.And(z3.Not(a),b)),z3.Or(a,z3.And(b,x<0))]
checked=0
for f in forms:
 smt='(declare-const a Bool)(declare-const b Bool)(declare-const x Int)(assert '+f.sexpr()+')';stat=Witness();manual=metric.ManualSatisfiesMetric(smt,stat);F=z3.And(manual._solver.assertions());nodes,rs=reach_all(F)
 for av,bv,xv in itertools.product([0,1],[0,1],[-3,-1,0,1,3]):
  values={'a':av,'b':bv,'x':xv};vs=variables(nodes);values={k:values[k] for k in vs};stat.current={};manual.count_sample(list(values.items()))
  for e,R in zip(nodes,rs):assert exact_value(R,values,vs)==int(e.get_id() in stat.current);checked+=1
for v in [-2**70,-2**63,-3,-1,0,1,2**63,2**70+3]:
 for bit in [0,1,62,63]:
  for desired in [0,1]:assert z3.is_true(z3.simplify(value_condition(z3.IntVal(v,ctx=metric.CTX),bit,desired)))==(((v>>bit)&1)==desired);checked+=1
print(json.dumps({'passed':True,'checks':checked,'solver_calls':0}))
