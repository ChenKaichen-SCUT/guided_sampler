from common_bd import *
from runner import run_worker,stream_rows
import argparse
p=argparse.ArgumentParser();p.add_argument('stage',choices=['probes','offline','real_diagnosis']);a=p.parse_args()
cfg=read(ROOT/'configs/refinement_budget_delivery.json');frozen=read(MAN/'implementation.json');assert frozen['correctness_passed']
for rel,sha in frozen['files'].items():assert digest(ROOT/rel)==sha,rel
for rel,sha in frozen['artifacts'].items():assert digest(ROOT/rel)==sha,rel
assert digest(ROOT/'configs/refinement_budget_delivery.json')==read(MAN/'plan.json')['configuration_sha256']
os.sched_setaffinity(0,{cfg['cpu']})
if a.stage=='offline':assert (BASE/'probes/frozen_v1/completion.json').exists();assert read(BASE/'analysis/probe_equivalence_v1/summary.json')['passed']
if a.stage=='real_diagnosis':assert (BASE/'offline/frozen_v1/completion.json').exists()
root=attempt(a.stage,'frozen_v1');completion=[]
jobs=cfg['probes'] if a.stage=='probes' else cfg['offline'] if a.stage=='offline' else [{'id':f'SMT_real_{r["position"]:02d}','instance':'SMT_real','position':r['position']} for r in cfg['real_requests']]
for job in jobs:
 d=root/job['id'];d.mkdir();inp=ROOT/f'results/refinement/offline/inputs_v1/{job["instance"]}.json'
 if a.stage=='real_diagnosis':exe=ROOT/'build/budget_delivery_blocking_release';cmd=[exe,inp,ROOT/'configs/refinement_budget_delivery.json',job['position'],d];deadline=25
 else:exe=ROOT/'build/budget_delivery_worker_release';cmd=[exe,inp,d,job['configuration'],job['track']];deadline=6 if a.stage=='probes' else 30
 exclusive(d/'attempt.json',{**job,'stage':a.stage,'input_sha256':digest(inp),'binary_sha256':digest(exe),'source_commit':frozen['commit'],'configuration_sha256':digest(ROOT/'configs/refinement_budget_delivery.json'),'command':list(map(str,cmd)),'cpu_affinity':[cfg['cpu']],'historical_cpu_credit_proven':False,'cold_start':True,'real_solver_checks':0,'native_sampling':0})
 terminal=run_worker(cmd,d,deadline);rs,truncated=stream_rows(d/'stream.jsonl');failure=[r for r in rs if r['kind']=='failure'];summary=next((r for r in rs if r['kind']=='summary'),None)
 result={'job':job['id'],'terminal':terminal,'truncated_stream':truncated,'failure_records':failure,'summary_present':summary is not None};write(d/'completion.json',result);completion.append(result);print(a.stage,job['id'],terminal['returncode'],terminal['parent_wall'],flush=True)
 if failure or (terminal['returncode']!=0 and not terminal['external_timeout']):raise RuntimeError(('correctness/process failure; no automatic retry',job['id']))
 # Deadlines are retained outcomes, never rerun or replaced by an easier job.
exclusive(root/'completion.json',{'attempts':completion,'count':len(completion),'new_sampling':0,'real_solver_checks':0,'no_retry':True})
