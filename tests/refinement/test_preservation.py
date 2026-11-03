import sys,pathlib,json,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement'))
from independent import *
x,y=z3.Ints('x y');f=z3.Or(x==0,z3.And(y>=0,y<=31));ast,_,_=export(f)
S=observations(ast,['0','0'])[1];N=observations(ast,['1','0'])[1];Q=observations(ast,['3','31'])[1]
assert covered(S|Q)>covered(S|N) and not N-S<=Q
hidden=observations(ast,['0','0'])[1];_,trace=evaluate(ast,['1','0']);yids=[i for i,n in enumerate(ast['nodes']) if n.get('op')=='var' and ast['variables'][n['variable']]['name']=='y'];assert len(yids)==1;yi=yids[0];assert (yi,0,0) in N and (yi,0,0) not in hidden
request={'op':'sequence','ast':ast,'models':[['0','0'],['1','0'],['2','0']],'bounded':False,'layer':'L2'}
p=subprocess.run([ROOT/'build/refinement_cli'],input=json.dumps(request)+'\n',capture_output=True,text=True,check=True);r=json.loads(p.stdout);assert r['ok'];history=set();native_history=set()
for row,m in zip(r['result']['events'],request['models']):
    n=observations(ast,m)[1];q=observations(ast,row['output_assignment'])[1];assert n-history<=q;native_history|=n;history|=q;assert native_history<=history
    for c in row['candidates']:
        if c.get('kind')=='candidate' and 'missing_observations' in c:
            # Candidate masks are independently checked against that event's
            # frozen protected masks, including unvisited nodes.
            masks=row['protected_masks'];expected=set()
            for node,z,o in masks:
                for bit in range(64):
                    if z>>bit&1:expected.add((node,bit,0))
                    if o>>bit&1:expected.add((node,bit,1))
            actual=observations(ast,c['assignment'])[1];assert set(map(tuple,c['missing_observations']))==expected-actual
h={'op':'hits','a':'1','c':'0','bit':1,'desired':True,'intervals':[['0','0'],['10','10']]};r2=json.loads(subprocess.run([ROOT/'build/refinement_cli'],input=json.dumps(h)+'\n',capture_output=True,text=True,check=True).stdout);assert r2['result']['parameters']==['10']
print(json.dumps({'passed':True,'scalar_covered_counterexample':{'native_gain':covered(S|N)-covered(S),'candidate_gain':covered(S|Q)-covered(S),'lost_first_sides':len((N-S)-Q)},'same_y_value_unvisited_rejected':True,'cross_OR_parameter':10,'prefixes':3,'solver_checks':0}))
