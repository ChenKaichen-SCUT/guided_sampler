#!/usr/bin/env python3
"""D3: fixed six or fewer real checkpoints x four independent fresh-query cells."""
from common import *
import time,collections
BASE=ROOT/'results/round3_semantics';OUT=BASE/'micro';BINARY=ROOT/'build/round3-micro';LIBRARY=ROOT/'deps/round3_micro/lib/libz3.so'
def invoke(spec,formula,snapshot,cell,out):
 out.mkdir(parents=True,exist_ok=False);env=os.environ.copy();env.update(GUIDED_D3_CASE=str(spec),GUIDED_D3_CELL=cell,GUIDED_SEMANTIC_TRACE_DIR=str(out),GUIDED_SEMANTIC_RUN_ID=out.parent.name+'_'+cell,GUIDED_SEMANTIC_UNMAPPED_LIMIT='0',GUIDED_TEST_RNG_TRACE=str(out/'rng.txt'),HIGHDIV_NATIVE_DECISION_TRACE=str(out/'native_decisions.txt'));env.pop('GUIDED_A_DIAGNOSTIC',None)
 cmd=['taskset','-c','0',str(BINARY),cell,str(spec),str(formula),str(snapshot),str(out)];write(out/'attempt.json',{'command':cmd,'cell':cell,'parent_deadline_seconds':5,'state_relation':'same_query_not_same_state','fork_used':False});t=time.monotonic()
 with (out/'stdout.log').open('x') as stdout,(out/'stderr.log').open('x') as stderr:
  try:r=subprocess.run(cmd,cwd=out,env=env,stdout=stdout,stderr=stderr,timeout=5);rc=r.returncode
  except subprocess.TimeoutExpired:rc='external_deadline'
 elapsed=time.monotonic()-t;terminal={'exit_code':rc,'parent_seconds':elapsed,'deadline_overrun':max(0,elapsed-5)};write(out/'terminal.json',terminal)
 return {**terminal,**(read(out/'result.json') if (out/'result.json').exists() else {'result':'unknown','reason_unknown':'external_deadline_or_process_error','checkpoint_seen':False}),'cell':cell}
def prepare():
 assert read(BASE/'oracle/summary.json')['calls']<=96;cases=read(BASE/'analysis/conditional_checkpoint_candidates.json');assert 0<len(cases)<=6;OUT.mkdir(exist_ok=False);snap=OUT/'snapshots';snap.mkdir();plan=[]
 for i,c in enumerate(cases):
  case={**c,'case_id':f'checkpoint_{i:02}'};source=BASE/'traces'/c['run_id'];q=next(q for q in map(json.loads,(source/'queries.jsonl').read_text().splitlines()) if q['query']==c['query_id']);coverage=next(r for r in map(json.loads,(source/'coverage_snapshots.jsonl').read_text().splitlines()) if r['query_id']==c['query_id']);case['query']={'query':c['query_id'],'assumptions':q['assumptions']};assert coverage['coverage_version']==c['coverage_version'];case['input_sha256']=digest(ROOT/c['input']);write(snap/(case['case_id']+'.case.json'),case);masks=coverage['seen_masks'];write(snap/(case['case_id']+'.state.json'),{'version':coverage['coverage_version'],'nodes':masks,'covered':sum((int(a)&int(b)).bit_count() for a,b in masks),'observed':sum(int(a).bit_count()+int(b).bit_count() for a,b in masks)});plan.append(case)
 exclusive(ROOT/'manifests/round3_d3_plan.json',{'selection':'first six sorted D1 applied checkpoints with final assignment / actual leaf discrepancy, no direct transmission observed, no overflow, original declaration identities verified','cases':plan,'cells':['N0','A0','N1','A1'],'max_real_child_runs':24,'max_seconds_each':5,'state_relation':'same_query_not_same_state','fork_used':False,'reason':'Existing sampler has a watchdog; ordinary Z3 timed calls can add timer threads. No verified single-thread, lock-free historical process snapshot is available.','scope_contract':{'push':'context::decide calls push_scope before apply_A_phase_hint','activation':'context::mark_as_relevant invokes native relevancy propagator','undo':'relevancy_propagator::push saves relevant_exprs/trail limits; pop unmarks and undoes; context::pop_scope_core invokes it'},'D1_unchanged':True})
def main():
 if not OUT.exists():prepare()
 if len(sys.argv)!=2 or sys.argv[1] not in ('prepare','execute'):raise RuntimeError('Choose prepare or execute')
 if sys.argv[1]=='prepare':
  fixture=OUT/'controlled';fixture.mkdir(exist_ok=False);(fixture/'input.smt2').write_text('(declare-const p Bool)(declare-const q Bool)(assert (and (or p q) (or q (not q))))\n');write(fixture/'case.json',{})
  subprocess.run([BINARY,'fixture',fixture/'case.json',fixture/'input.smt2',fixture/'state.json',fixture],check=True,capture_output=True)
  control=[]
  for cell in ['N0','A0','N1','A1']:
   result=invoke(fixture/'case.json',fixture/'input.smt2',fixture/'state.json',cell,fixture/cell);assert result['exit_code']==0 and result['result']=='sat' and result['checkpoint_seen'],(cell,result);control.append(result)
  assert [r['checkpoint']['activation'] for r in control]==[False,False,True,True];assert all(r['checkpoint']['native_var']==r['checkpoint']['actual_var'] and r['checkpoint']['assertions_before']==r['checkpoint']['assertions_after'] for r in control);write(fixture/'summary.json',{'passed':True,'runs':control,'real_checkpoint_runs':0})
  return
 assert read(OUT/'controlled/summary.json')['passed']
 freeze=read(ROOT/'manifests/round3_d3_implementation.json');assert digest(BINARY)==freeze['binary_sha256'] and digest(LIBRARY)==freeze['library_sha256'];assert digest(ROOT/'manifests/round3_d3_plan.json')==freeze['plan_sha256']
 plan=read(ROOT/'manifests/round3_d3_plan.json');exclusive(OUT/'STARTED.json',{'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'binary_sha256':digest(BINARY),'library_sha256':digest(LIBRARY),'plan_sha256':digest(ROOT/'manifests/round3_d3_plan.json')});results=[]
 for case in plan['cases']:
  cid=case['case_id'];assert digest(ROOT/case['input'])==case['input_sha256']
  for cell in plan['cells']:
   result=invoke(OUT/'snapshots'/(cid+'.case.json'),ROOT/case['input'],OUT/'snapshots'/(cid+'.state.json'),cell,OUT/'runs'/cid/cell);result['checkpoint_id']=cid;results.append(result);print(cid,cell,result['result'],'checkpoint_seen',result['checkpoint_seen'],flush=True)
 write(OUT/'summary.json',{'checkpoints':len(plan['cases']),'real_child_runs':len(results),'controlled_fixture_runs':4,'same_state':False,'state_relation':'same_query_not_same_state','fork_used':False,'seen':sum(r['checkpoint_seen'] for r in results),'results':results,'D1_binary_sha256_unchanged':digest(ROOT/'worktrees/round3_release/HighDiv/highdiv')==read(ROOT/'manifests/round3_d1_plan.json')['binary_sha256']})
if __name__=='__main__':main()
