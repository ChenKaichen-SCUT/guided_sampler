from common_bd import *
import itertools,hashlib,platform
assert not (MAN/'plan.json').exists()
restored=ROOT/'build/budget_delivery_restore';old=restored/'results/refinement_cost_repair'
proof=read(MAN/'restore.json');assert proof['all_verified']
rows_real=rows(old/'probes/new_v1/SMT_real_ValueCache/stream.jsonl');meta=next(x['metadata'] for x in rows_real if x['kind']=='metadata');directions={x['id']:x for x in meta['directions']}
data=read(ROOT/'results/refinement/offline/inputs_v1/SMT_real.json')
sha=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
requests=[]
for ev in [x for x in rows_real if x['kind']=='event' and x['native_event_id'] in [2,3,4,5]]:
 position=ev['native_event_id'];selected=ev['selected_direction_order'];singleton=sorted(x['direction_id'] for x in ev['directions'] if x.get('intervals')==[['0','0']]);pairs=list(itertools.combinations(singleton,2));combinations=[]
 for same in [True,False]:
  for i,j in [p for p in pairs if (directions[p[0]]['component']==directions[p[1]]['component'])==same][:8]:
   for sign in [1,-1]:combinations.append({'left':i,'right':j,'sign':sign,'same_component':same})
 requests.append({'position':position,'anchor':data['models'][position-1],'anchor_sha256':sha(data['models'][position-1]),'ast_sha256':sha(data['ast']),'selected':[dict(directions[i],old_domain=next(x['intervals'] for x in ev['directions'] if x['direction_id']==i)) for i in selected],'combinations':combinations})
assert sum(len(x['selected']) for x in requests)==64 and sum(len(x['combinations']) for x in requests)<=128
# Fixture is extracted, never supplied to the production worker or selector.
convrows=rows(old/'probes/new_v1/convert_ValueCache/stream.jsonl');ev=next(x for x in convrows if x['kind']=='event' and x['native_event_id']==3)
exclusive(ROOT/'tests/refinement_budget_delivery/frozen_witness.json',{'source_stream_sha256':digest(old/'probes/new_v1/convert_ValueCache/stream.jsonl'),'position':3,'native':ev['native_assignment'],'result':ev['chosen'],'protected':ev['protected_masks'],'native_gain':[ev['base_gain_covered'],ev['base_gain_observed']]})
offline=[]
for r,order in enumerate([['V0','V1','V2','V3'],['V2','V3','V0','V1'],['V3','V0','V1','V2']],1):
 for v in order:offline.append({'id':f'convert_{v}_L2_r{r}','instance':'convert','configuration':v,'track':'L2','repeat':r})
for r,order in enumerate([['V0','V3'],['V3','V0'],['V0','V3']],1):
 for v in order:offline.append({'id':f'convert_{v}_L1_r{r}','instance':'convert','configuration':v,'track':'L1','repeat':r})
for instance in ['SMT_real','SMT_random']:
 for v in ['V0','V3']:offline.append({'id':f'{instance}_{v}_L2_r1','instance':instance,'configuration':v,'track':'L2','repeat':1})
config={'base':'2dde70ab203009afdb07e4337eb3cdd637906704','branch':'refinement-budget-delivery','configurations':['V0','V1','V2','V3'],'source_models':43,'replayed_events':518,'cpu':0,'sibling':pathlib.Path('/sys/devices/system/cpu/cpu0/topology/thread_siblings_list').read_text().strip(),'historical_cpu_credit_proven':False,'stop_policy':'FirstCovered','probes_stop_policy':'AuditAll','budgets':{'preprocess':.100,'preprocess_soft':.096,'event':.020,'search_soft':.018,'sequence':6,'probe_preprocess':2,'probe_event':.5,'probe_worker_wall':6,'real_preprocess':2,'real_original_stage':8,'real_original_direction':.5,'real_combination_stage':8,'real_combination':.25,'real_worker_wall':25,'evidence_bytes':64*1024*1024},'limits':read(ROOT/'configs/refinement_cost_repair.json')['limits'],'offline':offline,'probes':[{'id':'convert_'+v,'instance':'convert','configuration':v,'track':'probe'} for v in ['V0','V1','V2','V3']],'real_requests':requests,'new_native_sampling':0,'real_solver_checks':0,'oracle_runs':0,'online_sessions':0,'B':False,'guard':65536,'retry':'none; correctness errors only, invalidated attempts retained'}
exclusive(ROOT/'configs/refinement_budget_delivery.json',config)
inputs={}
for instance in ['convert','SMT_random','SMT_real']:
 p=ROOT/f'results/refinement/offline/inputs_v1/{instance}.json';j=read(p);inputs[instance]={'path':str(p.relative_to(ROOT)),'sha256':digest(p),'models':len(j['models']),'ast_sha256':sha(j['ast']),'assignments_sha256':[sha(m) for m in j['models']],'input':j['input'],'input_sha256':digest(pathlib.Path(j['input'])),'source_receipts':j['source_receipts']}
exclusive(MAN/'plan.json',{'configuration_sha256':digest(ROOT/'configs/refinement_budget_delivery.json'),'guide_sha256':digest(ROOT/'docs/refinement_budget_delivery/execution_guide.zh.md'),'inputs':inputs,'official_metric_sha256':digest(metric_path()),'toolchain':subprocess.check_output(['g++','--version'],text=True),'system':platform.uname()._asdict(),'cpu_info':pathlib.Path('/proc/cpuinfo').read_text(),'physical_core':pathlib.Path('/sys/devices/system/cpu/cpu0/topology/core_id').read_text().strip(),'cold_state':'new process, empty anchor caches, pool/index/state reconstructed; OS pages not flushed','no_exclusive_host_claim':True,'archive_restore_sha256':digest(MAN/'restore.json')})
print('plan frozen: 22 sequences, 4 probes, 4 real workers;',sum(len(x['combinations']) for x in requests),'combination requests')
