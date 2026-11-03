import pathlib,sys,json
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement'))
from independent import *
x,y,z,w=z3.Ints('x y z w')
fs=[('box',z3.And(x>=0,x<=31,y>=0,y<=31),[[0,0],[1,0],[2,0]]),('protected',z3.Or(x==0,z3.And(y>=0,y<=31)),[[0,0],[1,0],[2,0]]),('disconnected',z3.And(x>=0,z3.Or(x<=3,x>=10),x<=15),[[0],[1],[10]]),('equality',z3.And(x+y==z,x>=0,y>=0,z<=31),[[0,0,0],[1,0,1],[1,1,2]]),('syntactic',z3.And(x-x==0,z3.Or(x==0,y>=0),z3.If(x>0,y,-y)>=0,w==w,z>=0),[[0,0,0,0],[0,1,1,1],[1,1,1,1]]),('nonlinear_invariant',z3.And(x>=0,x<=31,y*y>=0),[[0,0],[1,0],[2,0]])]
out=[]
for name,f,models in fs:
 a,ns,vs=export(f);assert all(observations(a,m)[0] for m in models),(name,[str(v) for v in vs]);out.append({'name':name,'ast':a,'models':[[str(v) for v in m] for m in models]})
p=ROOT/'tests/refinement_cost_repair/fixtures.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
