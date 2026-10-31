#!/usr/bin/env python3
from common import *
import time
stage=sys.argv[1];assert stage in ('M','S');BASE=ROOT/'results/round4';plan=read(ROOT/'manifests/round4_short_plan.json');freeze=read(ROOT/f'manifests/round4_{stage}_implementation.json');assert freeze['short_plan_sha256']==digest(ROOT/'manifests/round4_short_plan.json');assert freeze['config_sha256']==digest(ROOT/'configs/round4.json')
if stage=='S':assert read(BASE/'analysis/M_summary.json')['passed'] and (BASE/'M_FINISHED.json').exists()
binary=ROOT/f'worktrees/round4_{stage}_release/HighDiv/highdiv';library=ROOT/f'deps/round4_{stage}_release/lib/libz3.so';assert digest(binary)==freeze['binary_sha256'] and digest(library)==freeze['library_sha256'];jobs=[r for r in plan['jobs'] if r['stage']==stage];assert len(jobs)==6
exclusive(BASE/(stage+'_STARTED.json'),{'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'freeze_sha256':digest(ROOT/f'manifests/round4_{stage}_implementation.json'),'jobs':jobs})
for j in jobs:
 d=BASE/'runs'/j['id'];d.mkdir(parents=True,exist_ok=False);assert digest(ROOT/j['input'])==j['input_sha256'];cmd=['taskset','-c',str(j['cpu']),str(binary),'-i',str((ROOT/j['input']).resolve()),'-o',str(d),'-t',str(j['wall_seconds']),'-s','0','--guidance',j['mode'],'--unlimited-samples'];write(d/'attempt.json',{**j,'command':cmd,'binary_sha256':digest(binary),'library_sha256':digest(library)})
 env=os.environ.copy()
 for k in ['GUIDED_A_DIAGNOSTIC','HIGHDIV_TEST_MAX_QUERIES','GUIDED_TEST_RNG_TRACE','HIGHDIV_NATIVE_DECISION_TRACE','GUIDED_R4_MAPPING_OFF']:env.pop(k,None)
 env.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=j['id'],GUIDED_SEMANTIC_CDCL_LIMIT=str(j['cdcl_cap']),GUIDED_SEMANTIC_UNMAPPED_LIMIT='0',HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'));t=time.monotonic()
 with (d/'stdout.log').open('x') as stdout,(d/'stderr.log').open('x') as stderr:
  try:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=75);rc=r.returncode
  except subprocess.TimeoutExpired:rc='external_watchdog_75s'
 write(d/'terminal.json',{'exit_code':rc,'process_seconds':time.monotonic()-t,'no_retry':True});print(j['id'],rc,flush=True)
 if (d/'summary.json').exists():assert read(d/'summary.json')['cdcl_queries']<=j['cdcl_cap']
exclusive(BASE/(stage+'_FINISHED.json'),{'sessions':6,'freeze_sha256':digest(ROOT/f'manifests/round4_{stage}_implementation.json')})
