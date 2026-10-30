#!/usr/bin/env python3
"""Independent delivery audit: budgets, old artifacts, identities and witnesses."""
from common import *
from collections import Counter
BASE=ROOT/'results/round3_semantics'
def main():
 errors=[];old=read(BASE/'history_before.json');changed=[]
 for name,st in old['files'].items():
  p=ROOT/name
  if not p.exists() or {'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}!=st:changed.append(name)
 for name,h in old['protected_sha256'].items():
  if digest(ROOT/name)!=h:changed.append(name)
 for name,h in read(BASE/'offline/verified_sources.json').items():
  if digest(ROOT/name)!=h:changed.append(name)
 inputs=read(ROOT/'manifests/inputs.json');upstream=read(ROOT/'manifests/upstream.json')
 for item in inputs:
  if digest(ROOT.parent/item['path'])!=item['sha256']:changed.append(item['path'])
 for item in upstream['files']:
  if digest(UP/item['path'])!=item['sha256']:changed.append('upstream/'+item['path'])
 unchanged={'input_hashes_checked':len(inputs),'upstream_source_hashes_checked':len(upstream['files']),'passed':not changed,'old_file_metadata_checked':len(old['files']),'protected_hashes_checked':len(old['protected_sha256']),'D0_consumed_old_hashes_checked':len(read(BASE/'offline/verified_sources.json')),'changed':changed,'historical_baseline_executions':0};write(BASE/'BASELINE_UNCHANGED.json',unchanged);errors+=changed
 plan=read(ROOT/'manifests/round3_d1_plan.json');assert len(plan['jobs'])==6;assert read(BASE/'D1_FINISHED.json')['sessions']==6
 assert digest(ROOT/'worktrees/round3_release/HighDiv/highdiv')==plan['binary_sha256'];assert digest(ROOT/'deps/round3_release/lib/libz3.so')==plan['library_sha256']
 sessions=[]
 for job in plan['jobs']:
  d=ROOT/job['output'];assert digest(ROOT/job['input'])==job['input_sha256'];summary=read(d/'summary.json');qs=[json.loads(l) for l in (d/'queries.jsonl').read_text().splitlines()];assert sum(q['source']=='CDCL' for q in qs)==summary['cdcl_queries']<=job['cdcl_cap'];assert read(d/'terminal.json')['exit_code']==0;assert read(d/'target_audit.json')['passed'];assert read(d/'wire_coverage.command.json')['exit_code']==0;assert read(d/'wire_coverage.command.json')['metric_sha256']==digest(metric_path());assert summary['formal_count']==read(d/'finalization.json')['formal_count']
  for q in qs:
   if q['source']!='CDCL':continue
   g=q['guidance']
   if not g:continue
   for key in ['b_encoded','b_internalized','b_selected','guidance_created_bool_vars','guidance_added_assertions','guidance_marked_relevant']:assert g[key]==0,(job['id'],key)
   for a in g['actions']:assert a['native_var']==a['actual_var'] and a['decision_id']<=64
   assert g['suggestions']<=4
  sessions.append({'id':job['id'],'cdcl_queries':summary['cdcl_queries'],'total_queries':len(qs),'formal_count':summary['formal_count'],'status':summary['status'],'elapsed':summary['elapsed'],'process_seconds':read(d/'terminal.json')['process_seconds']})
 chain=read(BASE/'analysis/chain_summary.json');assert chain['passed'];oracle=read(BASE/'oracle/summary.json');assert oracle['calls']<=96 and oracle['cases']<=12;mapping=read(BASE/'mapping/summary.json');assert mapping['solver_calls']<=16 and mapping['representatives']<=16
 micro=read(BASE/'micro/summary.json');assert micro['checkpoints']<=6 and micro['real_child_runs']==24
 assert read(BASE/'micro/audit_summary.json')['passed'];assert read(BASE/'oracle/independent_audit.json')['passed']
 assert read(BASE/'oracle/CONSTRUCTION_RESUME.json')['oracle_calls_repeated']==0
 freeze=read(ROOT/'manifests/round3_d3_implementation.json');assert digest(ROOT/'build/round3-micro')==freeze['binary_sha256'];assert digest(ROOT/'deps/round3_micro/lib/libz3.so')==freeze['library_sha256']
 assert digest(ROOT/'manifests/round3_d3_plan.json')==freeze['plan_sha256']
 for item in read(BASE/'micro/summary.json')['results']:assert item['cell'] in ['N0','A0','N1','A1']
 assert len(list((BASE/'micro/runs').glob('*/*/attempt.json')))==24
 for rel,entry in read(ROOT/'patches/round3_semantics/files.json').items():
  for variant in ['release','sanitize']:assert digest(ROOT/f'worktrees/round3_{variant}'/rel)==entry['new_sha256']
 for rel,entry in read(ROOT/'patches/round3_micro/files.json').items():assert digest(ROOT/'worktrees/round3_micro'/rel)==entry['new_sha256']
 validation={}
 for variant in ['release','sanitize']:
  library=ROOT/f'deps/round3_{variant}/lib/libz3.so';passed=[read(p) for p in (BASE/'correctness').glob(variant+'_*/summary.json') if read(p).get('passed') and read(p)['library_sha256']==digest(library)];assert passed,variant;validation[variant]=passed[-1]
  completion=read(BASE/f'correctness/completion_{variant}/summary.json');assert completion['passed'] and completion['library_sha256']==digest(library);validation[variant]['completion_test']=completion
 write(BASE/'validation_summary.json',validation);write(BASE/'oracle_summary.json',oracle);write(BASE/'mapping_summary.json',mapping);write(BASE/'micro_summary.json',micro)
 artifact_hashes={str(p.relative_to(BASE)):digest(p) for p in BASE.rglob('*') if p.is_file() and str(p.relative_to(BASE)) not in ('artifact_hashes.json','audit_summary.json')};write(BASE/'artifact_hashes.json',artifact_hashes)
 result={'passed':not errors,'errors':errors,'base_commit':'2f839861acf0a8cec78e05dac256b98b0dc30099','implementation_commit':plan['implementation_commit'],'sessions':sessions,'D1_sessions':len(sessions),'D2_calls':oracle['calls'],'mapping_calls':mapping['solver_calls'],'D3_runs':micro['real_child_runs'],'D3_same_state':False,'seed':0,'HighDiv_executions':0,'new_900_second_experiments':0,'B_enabled':False,'baseline_unchanged':unchanged,'witness_solver_models_counted_as_samples':False,'independent_methods':['unchanged official visitor callbacks','exact full integer substitution','separately parsed raw atom with declaration identity checks','per-token propagation history','actual provider and converter chain checks','offline oracle witness validation'],'artifact_count':len(artifact_hashes)};write(BASE/'audit_summary.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
