import sys,pathlib,itertools,json,time
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement'))
from oracle_encoder import *
from independent import evaluate,covered
x,y=z3.Ints('x y');shared=x+y;fs=[z3.Or(x==0,x==y),z3.And(x>=0,z3.Or(x==1,y>0)),z3.And(z3.If(x>0,shared,-shared)>=0,z3.Or(x==0,shared==1))]
cases=0
for f in fs:
 a,ns,vs,reach=reach_conditions(f)
 for m in itertools.product(range(-2,3),repeat=len(vs)):
    sub=[(v,z3.IntVal(m[i])) for i,v in enumerate(vs)];valid,tr=evaluate(a,m)
    for i,r in enumerate(reach):assert z3.is_true(z3.simplify(z3.substitute(r,sub)))==(i in tr),(f,m,i)
    cases+=1
 a,ns,vs=export(f);models=[list(m) for m in itertools.product(range(-1,2),repeat=len(vs)) if evaluate(a,m)[0]]
 if len(models)<2:continue
 formula,meta=improvement_problem(f,models,2,time.monotonic()+10)
 if formula is None:continue
 history=observations(a,models[0])[1];native=observations(a,models[1])[1];protected=native-history
 for m in itertools.product(range(-2,3),repeat=len(vs)):
    valid,obs=observations(a,m);expected=valid and protected<=obs and covered(history|obs)>covered(history|native)
    sub=[(v,z3.IntVal(m[i])) for i,v in enumerate(vs)];actual=z3.is_true(z3.simplify(z3.substitute(formula,sub)));assert actual==expected,(f,m);cases+=1
print(json.dumps({'passed':True,'cases':cases,'solver_checks':0,'full_Reach_and_strict_covered_problem':True}))
