import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts/refinement'))
from independent import export,z3
x,y,z=z3.Ints('x y z')
fs=[('coordinated',z3.And(x>=0,y>=0,x<=y,y<=2*x),[0,0],[[1,0],[0,1],[1,1],[1,-1]]),('opposite_tight',z3.And(x>=0,x<=0),[0],[[1]]),('branch_equality',z3.Or(z3.And(x==0,y>=0),z3.And(x==2,y>=0)),[0,0],[[1,0]]),('or_far',z3.Or(x==0,x==2),[0],[[1]]),('integer_rounding',z3.And(x>=-1,x<=1,y==y),[0,0],[[2,1]]),('three_way',z3.And(x>=0,x<=y,y<=x,y<=z,z<=y),[0,0,0],[[1,0,0],[0,1,0],[0,0,1],[1,1,0],[1,0,1],[0,1,1],[1,1,1]]),('not_disconnected',z3.Not(z3.And(x>0,x<3)),[0],[[1]]),('dag',z3.Or(z3.And(x>=0,x<=3),z3.And(x>=0,x>=10)),[0],[[1]])]
blocking=[]
for name,f,a,ds in fs:
 ast,_,vs=export(f);blocking.append({'name':name,'ast':ast,'anchor':list(map(str,a)),'directions':[[[i,str(x)] for i,x in enumerate(d) if x] for d in ds]})
p=R/'tests/refinement_budget_delivery/fixtures.json';assert not p.exists();p.write_text(json.dumps({'search':json.loads((R/'tests/refinement_cost_repair/fixtures.json').read_text()),'blocking':blocking},indent=2)+'\n')
