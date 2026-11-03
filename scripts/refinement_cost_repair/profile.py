from runner import *
import argparse
p=argparse.ArgumentParser();p.add_argument('stage',choices=['legacy','new']);a=p.parse_args();cfg=read(ROOT/'configs/refinement_cost_repair.json');os.sched_setaffinity(0,{cfg['cpu']});out=attempt('probes',a.stage+'_v1');exe=ROOT/('build/cost_repair_worker_legacy' if a.stage=='legacy' else 'build/cost_repair_worker_release')
if a.stage=='new':assert read(MAN/'implementation.json')['correctness_passed']
source_files={str(p.relative_to(ROOT)):digest(p) for pattern in ['include/refinement/*.hpp','src/refinement/cost_repair_worker.cpp','scripts/refinement_cost_repair/*.py'] for p in ROOT.glob(pattern) if p.is_file()}
manifest={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'binary_sha256':digest(exe),'files':source_files,'cpu':cfg['cpu'],'cold_start':True,'preprocess_cap':2,'event_cap':.5,'worker_cap':5,'discrete_limits':cfg['limits']};exclusive(out/'STARTED.json',manifest)
# Preserve the exact instrumented Legacy sources, without binary/build-tree uploads.
if a.stage=='legacy':
    for rel in source_files:
        dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/rel).read_bytes())
for job in cfg['probes']:
    if (job['mode']=='Legacy')!=(a.stage=='legacy'):continue
    d=out/job['id'];d.mkdir();data=ROOT/'results/refinement/offline/inputs_v1'/(job['instance']+'.json');cmd=[exe,data,d,job['mode'],'probe'];exclusive(d/'attempt.json',{**job,**manifest,'command':list(map(str,cmd)),'input_sha256':digest(data),'historical_cpu_credit_proven':False,'diagnostic_only':True})
    terminal=run_worker(cmd,d,5);rs,truncated=stream_rows(d/'stream.jsonl');write(d/'completion.json',{'truncated':truncated,'completed_worker':any(r['kind']=='summary' for r in rs),'last_record_kind':rs[-1]['kind'] if rs else None,'event_count_including_first_context':sum(r['kind']=='event' for r in rs)});assert terminal['returncode']==0 or terminal['external_timeout'],terminal
    print(job['id'],[(r['kind'],r.get('status'),r.get('native_event_id'),r.get('completed_evaluations')) for r in rs if r['kind'] in ['preprocess','event']],flush=True)
write(out/'FINISHED.json',{'workers':3 if a.stage=='legacy' else 6,'maximum_positions':12 if a.stage=='legacy' else 24,'no_retry':True})
