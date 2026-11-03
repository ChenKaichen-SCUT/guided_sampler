import pathlib,sys,json,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement_budget_delivery'));sys.path.insert(0,str(ROOT/'scripts/refinement'))
from common_bd import *
from independent import observations,covered
from runner import stream_rows
variant=sys.argv[1];out=pathlib.Path(sys.argv[2]);out.mkdir(exist_ok=False,parents=True);env=os.environ.copy()
if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
fixtures=read(ROOT/'tests/refinement_budget_delivery/fixtures.json')['search'][:2];checks=0;replacements=0
for fixture in fixtures:
 data={'ast':fixture['ast'],'models':fixture['models']};input=out/(fixture['name']+'.json');write(input,data)
 for mode in ['V0','V1','V2','V3']:
  for track in ['L1','L2']:
   d=out/(fixture['name']+'_'+mode+'_'+track);d.mkdir();exe=ROOT/f'build/budget_delivery_worker_{variant}'
   with (d/'stdout').open('w') as o,(d/'stderr').open('w') as e:r=subprocess.run([exe,input,d,mode,track],stdout=o,stderr=e,env=env,timeout=30)
   assert r.returncode==0,(d,(d/'stderr').read_text());rs,trunc=stream_rows(d/'stream.jsonl');assert not trunc;s=next(r for r in rs if r['kind']=='summary');history=set();native_history=set()
   for row in s['receipts']:
    pos=row['native_event_id'];native=observations(data['ast'],data['models'][pos-1])[1];actual=row['candidate_assignment'] if row['actually_delivered'] else data['models'][pos-1];legal,obs=observations(data['ast'],actual);assert legal and native-history<=obs
    if row['actually_delivered']:
     assert track=='L2' and row['budget_eligible'] and row['preprocess_eligible'];assert row['event_total_cpu']<.020 and row['event_total_wall']<.020;assert row['candidate_gain']['covered']>=row['native_gain']['covered'];replacements+=1
    if track=='L1':assert not row['actually_delivered']
    history|=obs;native_history|=native;assert native_history<=history;assert row['output_covered']==covered(history) and row['native_covered']==covered(native_history);checks+=1
   assert s['output_covered']==covered(history)
assert replacements>0,('worker isolation fixture did not actually deliver',variant)
write(out/'summary.json',{'passed':True,'events':checks,'actual_replacements':replacements,'binary_sha256':digest(ROOT/f'build/budget_delivery_worker_{variant}'),'new_real_workers':0,'real_solver_checks':0});print('synthetic worker PASS',variant,checks,replacements)
