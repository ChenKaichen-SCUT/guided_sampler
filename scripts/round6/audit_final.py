"""Historical immutability and bounded execution audit, without solver calls."""
from common6 import *
def main():
    old=read(ROOT/'manifests/round6_protected_before.json');changed=[]
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
    assert digest(ROOT/'manifests/round5_implementation.json')==old['frozen_R5_implementation_sha256']
    assert digest(ROOT/'manifests/round5_W_evidence.json')==old['frozen_R5_evidence_sha256']
    old_impl=read(ROOT/'manifests/round5_implementation.json')
    for v in ['release','sanitize']:
        for rel,entry in old_impl['sources'].items():assert digest(ROOT/f'worktrees/round5_{v}'/rel)==entry['sha256'],(v,rel)
    unchanged={'passed':not changed,'changed':changed,'old_file_metadata_checked':len(old['metadata']),'protected_sha256_checked':len(old['protected_sha256']),'input_hashes_checked':len(inputs),'upstream_source_hashes_checked':len(upstream['files']),'historical_baseline_executions':0}
    write(BASE/'BASELINE_UNCHANGED.json',unchanged);assert not changed,changed
    f=read(ROOT/'manifests/round6_implementation.json');cfg=read(ROOT/'configs/round6_guard.json');plan=read(ROOT/'manifests/round6_plan.json')
    assert f['config_sha256']==plan['config_sha256']==digest(ROOT/'configs/round6_guard.json')
    assert f['guide_sha256']==plan['guide_sha256']==digest(ROOT/'docs/round6/execution_guide.zh.md')
    for v,c in f['validation'].items():
        assert c['passed'];assert digest(ROOT/f'worktrees/round6_{v}/HighDiv/highdiv')==c['binary_sha256'];assert digest(ROOT/f'deps/round6_{v}/lib/libz3.so')==c['library_sha256'];assert digest(ROOT/f'build/round6-ccss-replay-{v}')==c['replay_sha256']
        assert digest(ROOT/'tests/lsan-upstream.supp')==c['sole_leak_suppression_sha256']
        for rel,h in f['sources'][v].items():assert digest(ROOT/f'worktrees/round6_{v}'/rel)==h['sha256']
    for p,h in f['code_files'].items():assert digest(ROOT/p)==h,p
    g1=read(BASE/'guard_analysis/G1_audit.json');assert g1['passed'];assert len(list((BASE/'replay_guard').glob('*/attempt.json')))==6
    for r in g1['rows']:
        assert r['passed']
        for p,h in r['files'].items():assert digest(ROOT/p)==h,p
    a=read(BASE/'guard_analysis/independent_audit.json');g3=read(BASE/'guard_analysis/G3_decision.json');assert a['passed'];assert g3['audit_sha256']==digest(BASE/'guard_analysis/independent_audit.json');assert g3['summary_sha256']==digest(BASE/'guard_analysis/summary.json')
    stages={'G2':{'attempts':len(list((BASE/'guard_short').glob('*/attempt.json'))),'audit':a}}
    assert stages['G2']['attempts']==24
    cn=len(list((BASE/'candidate_short').glob('*/attempt.json')));fn=len(list((BASE/'formal').glob('*/attempt.json')))
    if g3['chosen'] in ['A','B']:
        ca=read(BASE/'candidate_analysis/independent_audit.json');assert ca['passed'] and cn==18;stages['candidate']={'attempts':cn,'audit':ca};promotion=read(BASE/'candidate_analysis/promotion.json')
    else:
        assert cn==0;promotion=g3['FullG_promotion'] if g3['chosen']=='FullG' else {'passed':False}
    if promotion['passed']:
        fa=read(BASE/'formal_analysis/independent_audit.json');assert fa['passed'] and fn==32;stages['formal']={'attempts':fn,'audit':fa}
    else:assert fn==0 and not (BASE/'F_STARTED.json').exists()
    for st in stages.values():
        for row in st['audit']['rows']:
            name=row['run'];folder='guard_short' if name in [j['id'] for j in cfg['G2']] and st is stages['G2'] else 'candidate_short' if st is stages.get('candidate') else 'formal'
            for p,h in row['hashes'].items():assert digest(BASE/folder/name/p)==h,(name,p)
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ['audit_summary.json','artifact_hashes.json']}
    write(BASE/'artifact_hashes.json',hashes)
    write(BASE/'audit_summary.json',{'passed':True,'meaning_of_passed':'artifact integrity, declared validation scope and bounded experiments; not performance superiority','base_commit':cfg['base_commit'],'G1_attempts':6,'G2_attempts':24,'candidate_attempts':cn,'formal_attempts':fn,'selected':g3['chosen'],'promotion_passed':promotion['passed'],'new_HighDiv_runs':0,'additional_seeds':0,'B_enabled':False,'native_guard_threshold':65536,'baseline_unchanged':unchanged,'G0_validation':f['validation'],'artifact_count':len(hashes),'pre_freeze_failed_checks_retained':['guard_release_01 arithmetic expectation','guard_sanitize_01 pure Boolean direct-construction leak'],'new_leak_suppressions':0,'stages':{k:{'attempts':v['attempts'],'formal_models':v['audit']['formal_models'],'yield_calls':v['audit'].get('yield_calls')} for k,v in stages.items()},'known_missing':['last global improvement wall timestamp: deliberately absent from integer-only search hot path','no exact same-internal-state causal saving from divergent complete sessions','existing pure-Boolean direct-construction preprocessing defect retained'],'single_seed':True})
    print('Final round6 integrity audit passed',len(hashes),'artifacts')
if __name__=='__main__':main()
