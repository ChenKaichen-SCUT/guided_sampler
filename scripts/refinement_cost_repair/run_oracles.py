from runner import *
cfg=read(ROOT/'configs/refinement_cost_repair.json');manifest=read(MAN/'implementation.json');assert manifest['correctness_passed'];assert (BASE/'offline/frozen_v1/FINISHED.json').exists();os.sched_setaffinity(0,{cfg['cpu']});out=attempt('oracle','frozen_v1')
for rel,sha in manifest['files'].items():assert digest(ROOT/rel)==sha,rel
exclusive(out/'STARTED.json',{'manifest_sha256':digest(MAN/'implementation.json'),'cases':24,'cold':True,'wall_cap':3,'check_cap':2,'cpu':cfg['cpu']})
for job in cfg['oracles']:
 d=out/job['id'];d.mkdir();data=ROOT/'results/refinement/offline/inputs_v1'/(job['instance']+'.json');cmd=[python(),ROOT/'scripts/refinement_cost_repair/oracle_worker.py',data,str(job['position']),d,job['mode']]
 exclusive(d/'attempt.json',{**job,'command':list(map(str,cmd)),'implementation_commit':manifest['commit'],'implementation_sha256':digest(MAN/'implementation.json'),'input_sha256':digest(data),'cpu':cfg['cpu'],'cold_start':True,'max_checks':1,'wall_cap':3,'check_cap':2})
 terminal=run_worker(cmd,d,3);stages,truncated=stream_rows(d/'stages.jsonl');r=read(d/'result.json') if (d/'result.json').exists() else {};count=sum(s['stage']=='check_attempt' and s['state']=='entered' for s in stages);assert count<=1
 write(d/'completion.json',{'last_stage':stages[-1] if stages else None,'truncated_stage_log':truncated,'checks_attempted':count,'check_return':any(s['stage']=='check_return' for s in stages),'result_present':bool(r),'within_case_result':bool(r and any(s['stage']=='result_write' and s['state']=='completed' and s['wall']<=3 for s in stages) and not terminal['external_timeout']),'validated_delivery':bool(r.get('validated_within_case') and not terminal['external_timeout'])})
 print(job['id'],r.get('status','parent_deadline'),stages[-1]['stage'] if stages else 'no_stage','checks',count,flush=True)
write(out/'FINISHED.json',{'cases':24,'max_real_checks':24,'no_retry':True})
