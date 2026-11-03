from runner import *
cfg=read(ROOT/'configs/refinement_cost_repair.json');manifest=read(MAN/'implementation.json');assert manifest['correctness_passed'];os.sched_setaffinity(0,{cfg['cpu']});out=attempt('offline','frozen_v1');exe=ROOT/'build/cost_repair_worker_release';assert digest(exe)==manifest['artifacts'][str(exe.relative_to(ROOT))]
for rel,sha in manifest['files'].items():assert digest(ROOT/rel)==sha,rel
exclusive(out/'STARTED.json',{'manifest_sha256':digest(MAN/'implementation.json'),'jobs':len(cfg['offline']),'cold_each_worker':True,'cpu':cfg['cpu'],'no_parallel_work':True})
events=0
for job in cfg['offline']:
 d=out/job['id'];d.mkdir();data=ROOT/'results/refinement/offline/inputs_v1'/(job['instance']+'.json');track='component_only' if job['component_only'] else job['layer'];cmd=[exe,data,d,job['mode'],track]
 exclusive(d/'attempt.json',{**job,'command':list(map(str,cmd)),'implementation_commit':manifest['commit'],'implementation_sha256':digest(MAN/'implementation.json'),'binary_sha256':digest(exe),'input_sha256':digest(data),'cold_start':True,'cpu':cfg['cpu'],'historical_cpu_credit_proven':False,'source_receipts':read(data)['source_receipts'],'original_library_hashes':manifest['libraries'],'official_metric_sha256':manifest['official_metric_sha256']})
 terminal=run_worker(cmd,d,30);rs,truncated=stream_rows(d/'stream.jsonl');summary=[r for r in rs if r['kind']=='summary'];count=sum(r['kind']=='event_cost' for r in rs);events+=count
 write(d/'completion.json',{'completed':bool(summary),'truncated':truncated,'processed_events':count})
 if terminal['returncode']!=0 or not summary or any(r['kind']=='failure' for r in rs):
  write(out/'STOPPED.json',{'job':job,'reason':'worker_failure_correctness_or_incomplete_no_retry','terminal':terminal});raise RuntimeError('stop real scoring: '+job['id'])
 print(job['id'],summary[0]['effective_preprocess_status'],'covered',summary[0]['native_covered'],summary[0]['output_covered'],'completed',sum(r.get('completed_evaluations',0) for r in rs),flush=True)
assert events==559,events
write(out/'FINISHED.json',{'jobs':39,'source_models':43,'replayed_events':events,'no_retry':True,'historical_cpu_credit_proven':False})
