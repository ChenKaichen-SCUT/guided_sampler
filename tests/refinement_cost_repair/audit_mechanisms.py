import pathlib,sys,json
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement'))
from independent import *
r=json.loads(pathlib.Path(sys.argv[1]).read_text());checks=0
for event in r['fixed_workload']:
 ast=event['ast'];history=set()
 for m in event['history_assignments']:history|=observations(ast,m)[1]
 legal,native=observations(ast,event['native']);assert legal
 protect=native-history;rr=event['result'];expected={(i,b,v) for i,z,o in rr['protected_masks'] for b in range(64) for v in (0,1) if (o if v else z)>>b&1};assert expected==protect
 for c in rr['candidates']:
  if c['kind']!='candidate' or 'actual_observations' not in c:continue
  legal,actual=observations(ast,c['assignment']);assert legal
  assert set(map(tuple,c['missing_observations']))==protect-actual
  assert c['gain_covered']==covered(history|actual)-covered(history)
  assert c['gain_observed']==len(actual-history)
  recorded={(i,b,v) for i,z,o,_ in c['actual_observations'] for b in range(64) for v in (0,1) if (o if v else z)>>b&1};assert recorded==actual
  checks+=1
pathlib.Path(sys.argv[2]).write_text(json.dumps({'passed':True,'independent_candidate_evaluations':checks,'events':len(r['fixed_workload']),'solver_checks':0},indent=2)+'\n');print('independent mechanisms PASS',checks)
