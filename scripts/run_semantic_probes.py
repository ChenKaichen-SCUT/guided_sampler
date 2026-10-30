#!/usr/bin/env python3
"""Exactly six capped seed=0 diagnostic sessions, sequential pairs on CPU 0."""
from common import *
import time
BASE=ROOT/'results/round3_semantics'
def main():
 binary=ROOT/'worktrees/round3_release/HighDiv/highdiv';library=ROOT/'deps/round3_release/lib/libz3.so'
 for variant in ['release','sanitize']:
  assert read(BASE/f'correctness/completion_{variant}/summary.json')['passed']
  passed=[p for p in (BASE/'correctness').glob(variant+'_*/summary.json') if read(p).get('passed')];assert passed,variant
 old=read(ROOT/'manifests/round2_a_plan.json')['runs'];jobs=[]
 for index,name,cap in [(4,'convert',32),(2,'SMT_random',8),(3,'SMT_real',8)]:
  source=old[index]
  for mode in ['observe_trace','apply_trace']:
   rid=name+'_'+mode;d=BASE/'traces'/rid;cmd=['taskset','-c','0',str(binary),'-i',str((ROOT/source['input']).resolve()),'-o',str(d),'-t','60','-s','0','--guidance',mode,'--unlimited-samples']
   jobs.append({'id':rid,'instance':name,'mode':mode,'input':source['input'],'input_sha256':source['input_sha256'],'wall':60,'cdcl_cap':cap,'seed':0,'cpu':0,'unmapped_limit':8 if mode=='observe_trace' else 0,'command':cmd,'output':str(d.relative_to(ROOT))})
 plan={'jobs':jobs,'binary_sha256':digest(binary),'library_sha256':digest(library),'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'seed':0,'B_enabled':False,'HighDiv_executions':0,'nine_hundred_second_runs':0}
 exclusive(ROOT/'manifests/round3_d1_plan.json',plan);exclusive(BASE/'D1_STARTED.json',{'plan_sha256':digest(ROOT/'manifests/round3_d1_plan.json')})
 for j in jobs:
  assert digest(ROOT/j['input'])==j['input_sha256'];d=ROOT/j['output'];d.mkdir(parents=True,exist_ok=False);write(d/'attempt.json',j);env=os.environ.copy()
  for k in ['GUIDED_A_DIAGNOSTIC','HIGHDIV_TEST_MAX_QUERIES','GUIDED_TEST_RNG_TRACE','HIGHDIV_NATIVE_DECISION_TRACE']:env.pop(k,None)
  env.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=j['id'],GUIDED_SEMANTIC_CDCL_LIMIT=str(j['cdcl_cap']),GUIDED_SEMANTIC_UNMAPPED_LIMIT=str(j['unmapped_limit']),HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'))
  start=time.monotonic()
  with (d/'stdout.log').open('x') as out,(d/'stderr.log').open('x') as err:
   try:r=subprocess.run(j['command'],cwd=ROOT,env=env,stdout=out,stderr=err,timeout=75);rc=r.returncode
   except subprocess.TimeoutExpired:rc='external_watchdog_75s'
  write(d/'terminal.json',{'exit_code':rc,'process_seconds':time.monotonic()-start,'no_retry':True});print(j['id'],rc,flush=True)
  if (d/'summary.json').exists():assert read(d/'summary.json')['cdcl_queries']<=j['cdcl_cap']
 exclusive(BASE/'D1_FINISHED.json',{'sessions':6,'plan_sha256':digest(ROOT/'manifests/round3_d1_plan.json')})
if __name__=='__main__':main()
