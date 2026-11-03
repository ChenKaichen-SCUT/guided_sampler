import pathlib,sys,itertools,json,time,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement'));sys.path.insert(0,str(ROOT/'scripts/refinement_cost_repair'))
import oracle_encoder as old
import cost_oracle_encoder as new
from independent import *
x,y=z3.Ints('x y');shared=x+y
fs=[z3.Or(x==0,x==y),z3.And(x>=0,z3.Or(x==1,y>0)),z3.And(z3.If(x>0,shared,-shared)>=0,z3.Or(x==0,shared==1))]
for width in (1,2,8,64):
 cs=[z3.Or(x==i%3,z3.And(y>=i%2,z3.Not(shared==i%5))) for i in range(width)]
 fs.extend([z3.And(cs),z3.Or(cs),z3.And(z3.Not(z3.Or(cs)),z3.If(x>0,shared,-shared)>=0)])
points=0;old150=0;request_stats=[]
for fi,f in enumerate(fs):
 a,ns,vs,reach=old.reach_conditions(f);a2,ns2,vs2=export(f);nr=new.reach_conditions(f,time.monotonic()+120,True,(a2,ns2,vs2));lr=new.reach_conditions(f,time.monotonic()+120,False,(a2,ns2,vs2));assert a==a2
 for m in itertools.product(range(-2,3),repeat=len(vs)):
  sub=[(v,z3.IntVal(m[i])) for i,v in enumerate(vs)];valid,tr=evaluate(a,m)
  for i in range(len(ns)):
   vals=[z3.is_true(z3.simplify(z3.substitute(r[i],sub))) for r in (reach,lr,nr)];assert vals==[i in tr]*3,(fi,m,i)
  points+=1
  if fi<3:old150+=1
 models=[list(m) for m in itertools.product(range(-1,2),repeat=len(vs)) if evaluate(a,m)[0]]
 if len(models)<2:continue
 ref,meta=old.improvement_problem(f,models,2,time.monotonic()+120)
 problems=[]
 for mode in ('OracleLegacy','OracleShared'):
  pr,stats,ct=new.problem(f,models,2,time.monotonic()+120,mode);problems.append(pr);request_stats.append({'fixture':fi,'mode':mode,**stats})
 if ref is None:assert all(p is None for p in problems);continue
 history=observations(a,models[0])[1];native=observations(a,models[1])[1];protect=native-history
 for m in itertools.product(range(-2,3),repeat=len(vs)):
  legal,seen=observations(a,m);expected=legal and protect<=seen and covered(history|seen)>covered(history|native);sub=[(v,z3.IntVal(m[i])) for i,v in enumerate(vs)]
  for pr in [ref]+problems:assert z3.is_true(z3.simplify(z3.substitute(pr,sub)))==expected,(fi,m)
  points+=1
  if fi<3:old150+=1
assert old150==150
out={'passed':True,'cases':points,'old_cases':old150,'solver_checks':0,'all_Reach_and_complete_problem_equivalent':True,'stats':request_stats}
pathlib.Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n');print('oracle encoding PASS',points)
