"""Independent contract checks over saved artifacts; never calls a solver."""
from common6 import *
def main():
    stage=sys.argv[1];assert stage in ['G2','candidate'];cfg=read(ROOT/'configs/round6_guard.json');jobs=cfg[stage]
    name='guard' if stage=='G2' else 'candidate';root=BASE/(name+'_short');out=BASE/(name+'_analysis')
    mf=ROOT/'manifests'/('round6_implementation.json' if stage=='G2' else 'round6_candidate_implementation.json');f=read(mf)
    assert read(BASE/(stage+'_FINISHED.json'))['attempts']==len(jobs)
    assert len(list(root.glob('*/attempt.json')))==len(jobs)
    assert f['config_sha256']==digest(ROOT/'configs/round6_guard.json')
    for p,h in f['code_files'].items():assert digest(ROOT/p)==h,p
    for v,files in f['sources'].items():
        tree=ROOT/f'worktrees/round6_{v}' if stage=='G2' else ROOT/f'worktrees/round6_candidate_{v}'
        assert digest(tree/'HighDiv/highdiv')==f['validation'][v]['binary_sha256']
        lib=ROOT/f'deps/round6_{v}/lib/libz3.so' if stage=='G2' else ROOT/f'deps/round6_candidate_{v}/lib/libz3.so'
        assert digest(lib)==f['validation'][v]['library_sha256']
        for p,h in files.items():assert digest(tree/p)==h['sha256'],(v,p)
    summary=read(out/'summary.json');assert summary['passed'] and len(summary['sessions'])==len(jobs)
    evidence=[];total_calls=total_yields=total_formal=0
    for j in jobs:
        d=root/j['id'];a=read(d/'attempt.json');s=read(d/'summary.json');x=read(d/'exact.json');t=read(d/'terminal.json')
        assert a['seed']==0 and a['cpu']==j['cpu'] and a['command'][a['command'].index('-t')+1]=='120'
        assert a['binary_sha256']==f['validation']['release']['binary_sha256'] and a['library_sha256']==f['validation']['release']['library_sha256']
        assert digest(ROOT/j['input'])==j['input_sha256'];assert t['exit_code']==0
        worker=read(BASE/(stage+'_batches')/str(j['batch'])/(j['id']+'.worker.json'))
        ready=read(BASE/(stage+'_batches')/str(j['batch'])/(j['id']+'.ready.json'));gate=read(BASE/(stage+'_batches')/str(j['batch'])/'RELEASE.json')
        assert ready['affinity']==[j['cpu']] and ready['monotonic_ready']<=gate['monotonic']
        assert len(set(gate['cpu_slots']))==len(gate['cpu_slots'])==(4 if stage=='G2' else 3)
        assert not any('MAX_QUERIES' in k or 'QUERY_CAP' in k or 'MAX_CDCL' in k for k in worker['environment'])
        assert s['wall_limit']==120 and s['cdcl_query_limit']==0
        assert s['sample_limit']==j['model_limit']
        assert x['legal'] and x['models']==s['formal_count']==read(d/'finalization.json')['formal_count']
        if s['coverage'] is not None:assert x['covered']==s['coverage']
        assert read(d/'target_audit.json')['passed']
        official=read(d/'wire_coverage.command.json');assert official['exit_code']==0 and official['metric_sha256']==digest(metric_path())
        assert official['samples_sha256']==digest(d/'samples.formal') and official['input_sha256']==j['input_sha256']
        rr=rows(d/'formal_receipts.jsonl');assert all(r['commit_complete']<120 and r['legal'] and not r['duplicate'] for r in rr)
        assert len({json.dumps(r['typed'],sort_keys=True) for r in rr})==len(rr)
        native=rows(d/'ccss_guard.jsonl');host=rows(d/'ccss_guard_host.jsonl');queries=rows(d/'queries.jsonl');qmap={q['query']:q for q in queries};hostmap={r['source_query_id']:r for r in host}
        assert len(hostmap)==len(host)==sum(q['source']=='CCSS' for q in queries)
        assert len({n['call_id'] for n in native})==len(native)
        final_native={n['source_query_id']:n for n in native}
        guarded=stage=='candidate' or j['mode'].endswith('G')
        for n in native:
            h=hostmap[n['source_query_id']];q=qmap[n['source_query_id']]
            assert q['source']=='CCSS'
            assert h['native_call_id']==final_native[n['source_query_id']]['call_id'] and h['native_exit_reason']==final_native[n['source_query_id']]['exit_reason']
            assert n['guard_enabled']==guarded and n['stagnation_limit']==65536
            assert n['consumed_map_sha256']==sha_text(json.dumps(n['consumed_map'],sort_keys=True,separators=(',',':'),ensure_ascii=False))
            assert all(len(n[k])==64 for k in ['map_sha256','rng_before_sha256','rng_after_sha256'])
            assert n['restart_count']==max(0,n['initialization_count']-1)
            if n['search_started']:
                assert n['search_cpu_seconds']>=0 and n['search_wall_seconds']>=0 and n['exit_step_exact']>=n['last_improvement_step']
            if n['exit_reason']=='ccss_stagnation_yield':
                assert guarded and n['last_global_best']>0 and not n['model_produced']
                assert n['exit_step_exact']-n['last_improvement_step']==65536
                if n is final_native[n['source_query_id']]:assert q['result']=='unknown' and not any(r['query']==q['query'] for r in rr)
            if n['exit_reason']=='sat':assert n['last_global_best']==0 and n['model_produced']
            if n['exit_reason'] in ['exception','arith_unknown']:
                review=read(BASE/'guard_analysis/presearch_exception_review.json');assert review['passed']
                assert n['exit_reason']=='exception' and n['exception_text']=='Input string is not a valid number'
                assert not n['search_started'] and not n['model_produced'] and q['result']=='unknown'
                assert not any(r['query']==q['query'] for r in rr)
        for q in queries:
            if q['source']=='CDCL':assert q['assumptions']==[]
            g=q['guidance']
            if not g:continue
            assert all(g[k]==0 for k in ['b_encoded','b_internalized','b_selected','guidance_created_bool_vars','guidance_added_assertions','guidance_marked_relevant'])
            assert g['suggestions']<=4
            for act in g['actions']:
                assert act['decision_id']<=64 and act['native_var']==act['actual_var']
                if j['mode'].startswith('Ref'):assert act['preference_source']=='inherited_reference'
        assert not any(x.get('target_buffer_overflow',False) for x in rows(d/'lifecycle.jsonl'))
        assert not any(r.get('status')=='invalid' for r in rows(d/'sample_receipts.jsonl'))
        total_calls+=len(native);total_yields+=sum(n['exit_reason']=='ccss_stagnation_yield' for n in native);total_formal+=len(rr)
        evidence.append({'run':j['id'],'passed':True,'formal':len(rr),'native_calls':len(native),'hashes':{p.name:digest(p) for p in d.iterdir() if p.is_file()}})
    write(out/'independent_audit.json',{'passed':True,'stage':stage,'attempts':len(jobs),'formal_models':total_formal,'native_calls':total_calls,'yield_calls':total_yields,'solver_checks_added':0,'same_release_for_all_controls':True,'strict_receipt_deadline_verified':True,'seed':0,'B_enabled':False,'rows':evidence,'meaning_of_passed':'evidence, legality, fixed policy and budget audit; not performance success'})
    print(stage,'independent audit passed',len(jobs),total_formal)
if __name__=='__main__':main()
