#!/usr/bin/env python3
"""Execute the sealed 36-call mechanism suite once, including negative results."""
from common import *
import time
def main():
 root=ROOT/'results/round2_a/micro';plan=read(root/'selection_plan.json');binary=ROOT/'build/round2-micro-release';prefix=ROOT/'deps/round2_release'
 assert len(plan['jobs'])<=36 and not (root/'STARTED.json').exists()
 cmd=['g++','-std=c++20','-O3','-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(ROOT/'tests/round2/micro.cpp'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(binary)]
 subprocess.run(cmd,check=True)
 cases={c['case_id']:c for c in plan['cases']};snap=root/'snapshots';snap.mkdir(exist_ok=False)
 for cid,c in cases.items():
  assert digest(ROOT/c['input'])==c['input_sha256'];assert digest(ROOT/c['source_samples'])==c['source_samples_sha256'];write(snap/(cid+'.case.json'),c)
  subprocess.run([binary,'snapshot',snap/(cid+'.case.json'),ROOT/c['input'],ROOT/c['source_samples'],snap/(cid+'.state.json')],check=True)
 exclusive(root/'STARTED.json',{'plan_sha256':digest(root/'selection_plan.json'),'binary_sha256':digest(binary),'library_sha256':digest(prefix/'lib/libz3.so'),'calls_planned':len(plan['jobs'])})
 rows=[]
 for job in plan['jobs']:
  cid=job['case_id'];c=cases[cid];d=root/'runs'/cid/job['mode'];d.mkdir(parents=True,exist_ok=False)
  cmd=list(map(str,[binary,job['mode'],snap/(cid+'.case.json'),ROOT/c['input'],snap/(cid+'.state.json'),d]));exclusive(d/'attempt.json',{'command':cmd,**job})
  env=os.environ.copy();env.update(GUIDED_A_DIAGNOSTIC='1',HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'),HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'))
  start=time.monotonic()
  with (d/'stdout.log').open('x') as out,(d/'stderr.log').open('x') as err:
   try:p=subprocess.run(cmd,cwd=d,env=env,stdout=out,stderr=err,timeout=120);rc=p.returncode
   except subprocess.TimeoutExpired:rc='harness_timeout'
  row={**job,'exit_code':rc,'process_seconds':time.monotonic()-start};write(d/'terminal.json',row);rows.append(row);print(job,rc,flush=True)
 comparisons=[]
 for cid in cases:
  d=root/'runs'/cid;off=d/'a_off_test';observe=d/'a_observe_test'
  if (off/'result.json').exists() and (observe/'result.json').exists():
   a,b=read(off/'result.json'),read(observe/'result.json');same=(off/'native_decisions.txt').read_bytes()==(observe/'native_decisions.txt').read_bytes() if (off/'native_decisions.txt').exists() and (observe/'native_decisions.txt').exists() else None
   comparisons.append({'case_id':cid,'native_trace_equal':same,'result_equal':a['result']==b['result'],'projection_equal':a.get('projection')==b.get('projection'),'timeout_comparison_is_not_invariant':a['result']=='unknown' or b['result']=='unknown'})
 exclusive(root/'FINISHED.json',{'calls':len(rows),'jobs':rows,'off_observe':comparisons,'learned_state_reconstructed':False,'tuned_on_results':False})
if __name__=='__main__':main()
