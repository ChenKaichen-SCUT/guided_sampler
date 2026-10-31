#!/usr/bin/env python3
"""Final immutable-artifact, bounded-run, correctness and official scoring audit."""
from common import *
BASE=ROOT/'results/round4'
def rows(p):return [json.loads(l) for l in p.open()] if p.exists() else []
def main():
 old=read(BASE/'history_before.json');changed=[]
 for name,st in old['files'].items():
  p=ROOT/name
  if not p.exists() or {'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}!=st:changed.append(name)
 for name,h in old['protected_sha256'].items():
  if digest(ROOT/name)!=h:changed.append(name)
 inputs=read(ROOT/'manifests/inputs.json');upstream=read(ROOT/'manifests/upstream.json')
 for item in inputs:
  if digest(ROOT.parent/item['path'])!=item['sha256']:changed.append(item['path'])
 for item in upstream['files']:
  if digest(UP/item['path'])!=item['sha256']:changed.append('upstream/'+item['path'])
 unchanged={'passed':not changed,'changed':changed,'old_file_metadata_checked':len(old['files']),'protected_sha256_checked':len(old['protected_sha256']),'input_hashes_checked':len(inputs),'upstream_source_hashes_checked':len(upstream['files']),'historical_baseline_executions':0};write(BASE/'BASELINE_UNCHANGED.json',unchanged);assert not changed
 stages={}
 for stage in ['M','S']:
  f=read(ROOT/f'manifests/round4_{stage}_implementation.json');assert f['short_plan_sha256']==digest(ROOT/'manifests/round4_short_plan.json');assert f['config_sha256']==digest(ROOT/'configs/round4.json');assert read(BASE/f'{stage}_FINISHED.json')['sessions']==6
  assert digest(ROOT/f'worktrees/round4_{stage}_release/HighDiv/highdiv')==f['binary_sha256'];assert digest(ROOT/f'deps/round4_{stage}_release/lib/libz3.so')==f['library_sha256']
  for rel,h in f['header_hashes'].items():assert digest(ROOT/rel)==h,rel
  for rel,entry in f['sources'].items():
   for variant in ['release','sanitize']:assert digest(ROOT/f'worktrees/round4_{stage}_{variant}'/rel)==entry['new_sha256'],(stage,variant,rel)
  for variant,v in f['validation'].items():
   assert v['passed'] and v['completion']['passed'];assert digest(ROOT/f'deps/round4_{stage}_{variant}/lib/libz3.so')==v['library_sha256'];assert digest(ROOT/f'worktrees/round4_{stage}_{variant}/HighDiv/highdiv')==v['binary_sha256']
  stages[stage]={'freeze_sha256':digest(ROOT/f'manifests/round4_{stage}_implementation.json'),'implementation_commit':read(BASE/f'{stage}_STARTED.json')['implementation_commit'],'validation':f['validation']}
 plan=read(ROOT/'manifests/round4_short_plan.json');assert len(plan['jobs'])==12;assert len(list((BASE/'runs').glob('*/attempt.json')))==12;sessions=[]
 for job in plan['jobs']:
  d=BASE/'runs'/job['id'];qs=rows(d/'queries.jsonl');summary=read(d/'summary.json');exact=read(d/'exact.json');assert read(d/'terminal.json')['exit_code']==0;assert sum(q['source']=='CDCL' for q in qs)==summary['cdcl_queries']<=job['cdcl_cap'];assert read(d/'target_audit.json')['passed'];assert read(d/'wire_coverage.command.json')['exit_code']==0;assert read(d/'wire_coverage.command.json')['metric_sha256']==digest(metric_path());assert exact['legal'];assert exact['models']==summary['formal_count']==read(d/'finalization.json')['formal_count'];assert summary['coverage'] is None or exact['covered']==summary['coverage'];assert digest(ROOT/job['input'])==job['input_sha256']
  for q in qs:
   if q['source']!='CDCL':continue
   g=q['guidance']
   if not g:continue
   for key in ['b_encoded','b_internalized','b_selected','guidance_created_bool_vars','guidance_added_assertions','guidance_marked_relevant']:assert g[key]==0,(job['id'],key)
   assert g['suggestions']<=4
   for a in g['actions']:assert a['native_var']==a['actual_var'] and a['decision_id']<=64
  sessions.append({'id':job['id'],'cdcl':summary['cdcl_queries'],'formal':exact['models'],'covered':exact['covered'],'total':exact['total'],'seconds':summary['elapsed'],'status':summary['status'],'raw':summary['raw_count'],'explicit':summary['guidance_cost'],'exposure':summary['A_exposure']})
 for stage in ['M','S']:assert read(BASE/f'analysis/{stage}/chain_summary.json')['passed'];assert read(BASE/f'analysis/{stage}_summary.json')['passed']
 m=read(BASE/'analysis/M_summary.json');assert m['mapping_check_calls']==16;assert m['new_mapping_demand_feasibility']['solver_calls']<=12
 assert read(BASE/'analysis/reused_blocker_proof.json')['passed'];assert read(BASE/'analysis/reused_blocker_proof.json')['additional_solver_calls']==0;assert read(BASE/'analysis/S_comparison.json')['passed'];assert read(BASE/'analysis/S_comparison.json')['solver_calls']==0;assert not read(BASE/'analysis/S_checklist.json')['oracle_models_used_online'];assert read(BASE/'analysis/S_summary.json')['additional_solver_calls']==0
 artifact_hashes={str(p.relative_to(BASE)):digest(p) for p in BASE.rglob('*') if p.is_file() and p.name not in ['artifact_hashes.json','audit_summary.json']};write(BASE/'artifact_hashes.json',artifact_hashes)
 result={'passed':True,'base_commit':old['base_commit'],'stages':stages,'sessions':sessions,'planned_short_runs':12,'seed':0,'extra_seeds':0,'new_900_second_runs':0,'HighDiv_reruns':0,'B_enabled':False,'relevance_interventions':0,'extra_LIA_value_moves':0,'controlled_template_XOR_calls':sum(read(p)['independent_XOR_checks'] for p in (BASE/'correctness').glob('*/semantic_correspondence.stdout')),'M_mapping_XOR_calls':16,'M_target_feasibility_calls':m['new_mapping_demand_feasibility']['solver_calls'],'S_oracle_calls':0,'baseline_unchanged':unchanged,'artifact_count':len(artifact_hashes),'limitations':['bounded short mechanism experiment, not full HighDiv performance comparison','policy-dependent trajectories, not same-state causal samples','buffer overflow and missing model/theory evidence remain Unknown']};write(BASE/'audit_summary.json',result);print(json.dumps({'passed':True,'sessions':sessions,'artifacts':len(artifact_hashes)},ensure_ascii=False))
if __name__=='__main__':main()
