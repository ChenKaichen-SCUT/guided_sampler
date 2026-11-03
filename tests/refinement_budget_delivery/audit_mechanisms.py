import pathlib,sys,json,copy
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement_budget_delivery'));sys.path.insert(0,str(ROOT/'scripts/refinement'))
from independent import observations,covered,evaluate,official_trace,export,z3
from check_blocking import IndependentDomains
r=json.loads(pathlib.Path(sys.argv[1]).read_text());candidate_checks=0;direction_checks=0
for event in r['fixed_workload']+r['four_configurations']:
 ast=event['ast'];history=set()
 for m in event['history_assignments']:history|=observations(ast,m)[1]
 legal,native=observations(ast,event['native']);assert legal
 protected=native-history;rr=event['result'];expected={(i,b,v) for i,z,o in rr['protected_masks'] for b in range(64) for v in (0,1) if (o if v else z)>>b&1};assert expected==protected
 for c in rr['candidates']:
  if c['kind']!='candidate' or 'missing_observations' not in c:continue
  legal,actual=observations(ast,c['assignment']);assert legal
  assert set(map(tuple,c['missing_observations']))==protected-actual
  assert c['gain_covered']==covered(history|actual)-covered(history) and c['gain_observed']==len(actual-history)
  recorded={(i,b,v) for i,z,o,_ in c['actual_observations'] for b in range(64) for v in (0,1) if (o if v else z)>>b&1};assert recorded==actual;candidate_checks+=1
 if 'metadata' in event:
  for d in event['metadata']['directions']:
   independent=IndependentDomains(ast,event['native'],d['coefficients']);affected=[i for i in range(len(ast['nodes'])) if independent.deps[i]&independent.d.keys()];assert affected==d['affected']
   assert all(sum(c*independent.d.get(v,0) for v,c in cs.items())==0 for _,_,cs in independent.equalities());direction_checks+=1
certificates=0;mutations=0
for row in r['blocking']:
 d=IndependentDomains(row['ast'],row['anchor'],row['coefficients']);d.audit(row);certificates+=1
 for kind in ['atom','operation','endpoint','child']:
  changed=copy.deepcopy(row)
  if kind=='atom':
   item=next((q for n in changed['certificate'] for q in n['comparisons']),None)
   if item is None:continue
   item['slope']=str(int(item['slope'])+1)
  elif kind=='operation':changed['certificate'][-1]['operation']='xor'
  elif kind=='endpoint':changed['certificate'][-1]['domain']=[['1','1']]
  else:
   item=next((n for n in changed['certificate'] if n['children']),None)
   if item is None:continue
   item['children']=item['children']+[0]
  failed=False
  try:d.audit(changed)
  except AssertionError:failed=True
  assert failed,kind;mutations+=1
# Frozen +43 is only read by this auditor, never the worker or search code.
f=json.loads((ROOT/'tests/refinement_budget_delivery/frozen_witness.json').read_text());data=json.loads((ROOT/'results/refinement/offline/inputs_v1/convert.json').read_text());history=set()
for m in data['models'][:2]:history|=observations(data['ast'],m)[1]
legal,native=observations(data['ast'],f['native']);assert legal
legal,witness=observations(data['ast'],f['result']['assignment']);assert legal and native-history<=witness
assert covered(history|witness)-covered(history|native)==43
assert len(native-history)==1049
root=z3.And(z3.parse_smt2_file(data['input']));ast,_,_=export(root);assert ast['nodes']==data['ast']['nodes'];ok,tr=official_trace(root,{v['name']:int(x) for v,x in zip(ast['variables'],f['result']['assignment'])});assert ok and tr=={i:v for i,(_,v) in evaluate(ast,f['result']['assignment'])[1].items()}
out={'passed':True,'independent_candidate_evaluations':candidate_checks,'independent_direction_checks':direction_checks,'complete_certificates':certificates,'rejected_certificate_mutations':mutations,'frozen_witness':{'protected':1049,'extra_covered':43,'used_by_selector':False},'real_solver_checks':0}
pathlib.Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print('independent mechanisms PASS',out)
