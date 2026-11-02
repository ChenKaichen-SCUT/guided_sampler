from common5 import *
from batch_runner import run_batch
config=read(ROOT/'configs/round5_diagnosis.json');freeze=read(ROOT/'manifests/round5_implementation.json');assert freeze['config_sha256']==digest(ROOT/'configs/round5_diagnosis.json')
host=ROOT/'worktrees/round5_release/HighDiv/highdiv';library=ROOT/'deps/round5_release/lib/libz3.so';assert digest(host)==freeze['validation']['release']['binary_sha256'];assert digest(library)==freeze['validation']['release']['library_sha256']
jobs=[]
for j in config['jobs']:
    d=BASE/'W'/j['id'];assert digest(ROOT/j['input'])==j['input_sha256']
    env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL','TMPDIR'] if k in os.environ};env.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=j['id'],GUIDED_SEMANTIC_CDCL_LIMIT=str(j['cdcl_cap']),GUIDED_SEMANTIC_UNMAPPED_LIMIT='0',HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'),GUIDED_R5_DECISION_AUDIT='1')
    if j['instance']=='convert':env['GUIDED_R5_EXCHANGE_DIR']=str(d)
    cmd=[str(host),'-i',str((ROOT/j['input']).resolve()),'-o',str(d),'-t','60','-s','0','--guidance',j['mode'],'--unlimited-samples']
    jobs.append({**j,'directory':str(d),'command':cmd,'environment':env,'binary_sha256':digest(host),'library_sha256':digest(library)})
assert len(jobs)==9
exclusive(BASE/'W_STARTED.json',{'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'freeze_sha256':digest(ROOT/'manifests/round5_implementation.json'),'jobs':[j['id'] for j in jobs]})
results=run_batch(jobs,BASE/'W_batch',75)
exclusive(BASE/'W_FINISHED.json',{'attempts':9,'results':results,'no_retries':True})
print('Completed all 9 W attempts',flush=True)
