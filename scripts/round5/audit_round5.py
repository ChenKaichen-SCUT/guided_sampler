"""Independent bounded-attempt, source, official-score and protected-history audit."""
from common5 import *
def main():
    old=read(ROOT/'manifests/round5_protected_before.json');changed=[]
    for name,st in old['metadata'].items():
        p=ROOT/name
        if not p.exists() or {'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}!=st:changed.append(name)
    for name,h in old['protected_sha256'].items():
        if digest(ROOT/name)!=h:changed.append(name)
    inputs=read(ROOT/'manifests/inputs.json');upstream=read(ROOT/'manifests/upstream.json')
    for r in inputs:
        if digest(ROOT.parent/r['path'])!=r['sha256']:changed.append(r['path'])
    for r in upstream['files']:
        if digest(UP/r['path'])!=r['sha256']:changed.append('upstream/'+r['path'])
    unchanged={'passed':not changed,'changed':changed,'old_file_metadata_checked':len(old['metadata']),'protected_sha256_checked':len(old['protected_sha256']),'input_hashes_checked':len(inputs),'upstream_source_hashes_checked':len(upstream['files']),'historical_baseline_executions':0};write(BASE/'BASELINE_UNCHANGED.json',unchanged);assert not changed,changed
    freeze=read(ROOT/'manifests/round5_implementation.json');cfg=read(ROOT/'configs/round5_diagnosis.json');assert freeze['config_sha256']==digest(ROOT/'configs/round5_diagnosis.json')
    for v,c in freeze['validation'].items():
        assert c['passed'] and c['exchange_edges']['passed'];assert digest(ROOT/f'worktrees/round5_{v}/HighDiv/highdiv')==c['binary_sha256'];assert digest(ROOT/f'deps/round5_{v}/lib/libz3.so')==c['library_sha256'];assert digest(ROOT/f'build/round5-ccss-replay-{v}')==c['replay_sha256']
        for rel,entry in freeze['sources'].items():assert digest(ROOT/f'worktrees/round5_{v}'/rel)==entry['sha256'],(v,rel)
    for p,h in freeze['code_files'].items():assert digest(ROOT/p)==h,p
    assert len(list((BASE/'W').glob('*/attempt.json')))==len(cfg['jobs'])==9;assert read(BASE/'W_FINISHED.json')['attempts']==9
    for j in cfg['jobs']:
        d=BASE/'W'/j['id'];a=read(d/'attempt.json');assert a['seed']==0 and a['cpu']==j['cpu'];assert a['binary_sha256']==freeze['validation']['release']['binary_sha256'];assert read(d/'target_audit.json')['passed']
        x=read(d/'exact.json');s=read(d/'summary.json');assert x['legal'];assert x['models']==s['formal_count']==read(d/'finalization.json')['formal_count'];assert x['covered']==s['coverage'];assert s['cdcl_queries']<=j['cdcl_cap'];assert read(d/'wire_coverage.command.json')['exit_code']==0
        for q in rows(d/'queries.jsonl'):
            if q['source']=='CDCL':assert q['assumptions']==[]
            g=q['guidance']
            if not g:continue
            assert all(g[k]==0 for k in ['b_encoded','b_internalized','b_selected','guidance_created_bool_vars','guidance_added_assertions','guidance_marked_relevant']);assert g['suggestions']<=4
            for act in g['actions']:
                assert act['decision_id']<=64 and act['native_var']==act['actual_var']
                if j['mode']=='S_support':assert act['preference_source']!='avoid_direct_blocker'
    evidence=read(ROOT/'manifests/round5_W_evidence.json')
    for p,h in evidence['files'].items():assert digest(ROOT/p)==h,('frozen_W_capture_modified',p)
    assert read(BASE/'analysis/X_capture_details.json')['passed']
    assert read(BASE/'analysis/X_independent_arithmetic_audit.json')['passed']
    for d in (BASE/'W').iterdir():
        assert not any(x.get('target_buffer_overflow',False) for x in rows(d/'lifecycle.jsonl'))
        assert not any(x.get('kind')=='trace_overflow' for x in rows(d/'exchange_events.jsonl'))
        assert all(r['output_complete']<=60 for r in rows(d/'formal_receipts.jsonl'))
    cap=read(ROOT/'manifests/round5_capture.json');assert cap['audit_sha256']==digest(BASE/'analysis/X_capture_fidelity.json')
    for p,h in cap['files'].items():assert digest(ROOT/p)==h,p
    xp=read(ROOT/'manifests/round5_X_plan.json');assert len(xp['rows'])==8;assert len(list((BASE/'replay').glob('*/attempt.json')))==sum(x['execute'] for x in xp['rows'])<=8
    for r in xp['rows']:
        if not r['execute']:continue
        d=BASE/'replay'/r['id'];assert read(d/'attempt.json')['native_cutoff_seconds']==read(ROOT/r['recipe'])['cutoff_seconds']<=60;assert digest(ROOT/r['recipe'])==r['recipe_sha256'];assert digest(ROOT/r['map'])==r['map_sha256']
    required=['W_performance.csv','W_prefix_comparisons.csv','W_coverage_partition.csv','W_advice_funnel.csv','W_target_uniques.csv','W_quota_opportunities.csv','X_capture_fidelity.json','X_producer_consumer_diff.csv','X_initialization_diff.csv','X_replay_results.csv','X_search_progress.jsonl','root_cause_matrix.csv','next_change_decision.json']
    for f in required:assert (BASE/'analysis'/f).exists(),f
    decision=read(BASE/'analysis/next_change_decision.json');assert len(decision['priority_changes'])<=1
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ['audit_summary.json','artifact_hashes.json']};write(BASE/'artifact_hashes.json',hashes)
    perf=read(BASE/'analysis/W_summary.json')['sessions'];xs=read(BASE/'analysis/X_summary.json')['results'];limits=read(BASE/'analysis/known_limits_and_missing.json')
    write(BASE/'audit_summary.json',{'passed':True,'meaning_of_passed':'evidence integrity, legality in the stated validation scope, frozen implementation and bounded attempt counts; not performance success or perfect wall-clock conformance','base_commit':cfg['base_commit'],'W_attempts':9,'X_attempts':sum(r['execute'] for r in xp['rows']),'X_skipped':sum(not r['execute'] for r in xp['rows']),'new_HighDiv_runs':0,'new_seeds':0,'new_900_second_runs':0,'B_enabled':False,'validation':freeze['validation'],'baseline_unchanged':unchanged,'artifact_count':len(hashes),'official_and_independent_score_verified':True,'W_formal':sum(r['formal'] for r in perf),'W_raw':sum(r['raw'] for r in perf),'W_duplicates':sum(r['duplicates'] for r in perf),'W_invalid':sum(r['invalid'] for r in perf),'W_CDCL_unknown':sum(r['CDCL_unknown'] for r in perf),'W_CCSS_unknown':sum(r['CCSS_unknown'] for r in perf),'W_nonzero_process_exits':sum(r['exit_code']!=0 for r in perf),'X_reduced_SAT':sum(r.get('SAT') is True for r in xs),'X_native_cutoff':sum(r.get('result')=='native_cutoff' for r in xs),'X_nonzero_process_exits':sum(r.get('process_exit')!=0 for r in xs if r['execute']),'wall_limit_exit_overrun_runs':sum(r['wall_seconds']>60 for r in perf),'strict_process_wall_conformance':not any(r['wall_seconds']>60 for r in perf),'missing_and_limits':limits,'limitations':['single-seed bounded diagnostics','policy-dependent trajectories','CCSS reconstruction only within recorded input/initialization boundary','replay candidates do not enter formal samples']})
    print('Round5 final audit passed',len(hashes),'artifacts')
if __name__=='__main__':main()
