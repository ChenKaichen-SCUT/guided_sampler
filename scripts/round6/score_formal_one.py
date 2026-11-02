"""One completed F session: frozen official scoring and streaming contract audit."""
from common6 import *
from finalize_round2_stream import finalize
from evaluate_round2_official import evaluate
from audit_round4_targets import audit as audit_targets
def stream(p):
    if p.exists():
        with p.open() as f:
            for line in f:yield json.loads(line)
def main():
    assert (BASE/'F_FINISHED.json').exists(),'No scoring during timed sessions'
    plan=read(ROOT/'manifests/round6_formal_plan.json');j=next(j for j in plan['jobs'] if j['id']==sys.argv[1]);d=BASE/'formal'/j['id'];a=read(d/'attempt.json');s=read(d/'summary.json');t=read(d/'terminal.json')
    assert t['exit_code']==0 and a['cpu']==j['cpu'] and a['seed']==0
    assert a['binary_sha256']==plan['release']['binary_sha256'] and a['library_sha256']==plan['release']['library_sha256']
    assert digest(ROOT/j['input'])==j['input_sha256'];assert s['sample_limit']==j['model_limit'] and s['wall_limit']==900 and s['cdcl_query_limit']==0
    if not (d/'finalization.json').exists():finalize(d,900,j['model_limit'])
    if not (d/'exact.json').exists():assert evaluate(d,ROOT/j['input'])=={'official_exit':0,'exact_exit':0}
    if not (d/'target_audit.json').exists():assert audit_targets(d,ROOT/j['input'])['passed']
    x=read(d/'exact.json');assert x['legal'] and x['models']==s['formal_count']==read(d/'finalization.json')['formal_count']
    if s['coverage'] is not None:assert x['covered']==s['coverage']
    assert read(d/'target_audit.json')['passed'];metric=read(d/'wire_coverage.command.json');assert metric['exit_code']==0 and metric['metric_sha256']==plan['metric_sha256'] and metric['samples_sha256']==digest(d/'samples.formal')
    receipts=[]
    for r in stream(d/'formal_receipts.jsonl'):
        assert r['legal'] and not r['duplicate'] and r['commit_complete']<900
        receipts.append({k:r[k] for k in ['query','source','formal_index','commit_complete']})
    assert len(receipts)==x['models'];formal_queries={r['query'] for r in receipts}
    qc=collections.Counter();qtime=collections.Counter();qmap={};cdcl=[];acts=collections.Counter();backend=collections.Counter();limits=[]
    for q in stream(d/'queries.jsonl'):
        qc[q['source']+'_checks']+=1;qc[q['source']+'_'+q['result']]+=1;qtime[q['source']]+=q['check_seconds']
        if q['source']=='CDCL':assert q['assumptions']==[];cdcl.append({'query':q['query'],'start':q['start']})
        else:qmap[q['query']]={k:q[k] for k in ['result','start','end','granted_timeout','ccss_exit_reason','ccss_native_exit_reason']}
        g=q.get('guidance',{})
        if not g:continue
        assert all(g[k]==0 for k in ['b_encoded','b_internalized','b_selected','guidance_created_bool_vars','guidance_added_assertions','guidance_marked_relevant'])
        assert g['suggestions']<=4
        for bc in g.get('backend_calls',[]):
            backend['metadata_received_calls']+=bool(bc.get('metadata_received'))
            backend['ordinary_decisions']+=bc.get('ordinary_decisions',0)
            backend['exact_matches']+=bc.get('exact_matches',0)
            backend['normalized_matches']+=bc.get('normalized_matches',0)
        backend['binding_seconds']+=g.get('binding_seconds',0)
        backend['hot_callback_seconds']+=g.get('hot_callback_seconds',0)
        for act in g['actions']:
            assert act['decision_id']<=64 and act['native_var']==act['actual_var']
            if j['mode']=='RefG':assert act['preference_source']=='inherited_reference'
            acts[act['preference_source']]+=1;acts[act['preference_source']+'_phase_changes']+=act['phase_changed']
        if g.get('exposure_limit') or g.get('explicit_limit'):limits.append(q['query'])
    host={h['source_query_id']:h for h in stream(d/'ccss_guard_host.jsonl')};assert len(host)==qc['CCSS_checks']
    reasons=collections.Counter();errors=collections.Counter();yields=[];ncount=0;calls=[];seen_ids=set();search_cpu=search_wall=whole_wall=0
    for n in stream(d/'ccss_guard.jsonl'):
        ncount+=1;assert n['call_id'] not in seen_ids;seen_ids.add(n['call_id']);q=qmap[n['source_query_id']];h=host[n['source_query_id']]
        assert n['guard_enabled'] and n['stagnation_limit']==65536 and n['restart_count']==max(0,n['initialization_count']-1)
        assert n['consumed_map_sha256']==sha_text(json.dumps(n['consumed_map'],sort_keys=True,separators=(',',':'),ensure_ascii=False))
        assert all(len(n[k])==64 for k in ['map_sha256','rng_before_sha256','rng_after_sha256'])
        reasons[n['exit_reason']]+=1;search_cpu+=n['search_cpu_seconds'] or 0;search_wall+=n['search_wall_seconds'] or 0;whole_wall+=n['whole_ccss_wall_seconds']
        if n['exit_reason']=='ccss_stagnation_yield':
            assert n['last_global_best']>0 and n['exit_step_exact']-n['last_improvement_step']==65536 and not n['model_produced']
            if n['call_id']==h['native_call_id']:assert q['result']=='unknown' and n['source_query_id'] not in formal_queries
            yields.append({**{k:v for k,v in n.items() if k!='consumed_map'},'host_start':h['start'],'host_return':h['host_end']})
        if n['exit_reason']=='sat':assert n['last_global_best']==0 and n['model_produced']
        if n['exit_reason'] in ['exception','arith_unknown']:
            errors[n['exception_text'] or 'bounds_not_representable']+=1
            assert not n['model_produced']
            if n['call_id']==h['native_call_id']:assert q['result']=='unknown' and n['source_query_id'] not in formal_queries
        calls.append({'run':j['id'],'host_exit_reason':h['exit_reason'],**{k:v for k,v in n.items() if k!='consumed_map'}})
    raw=collections.Counter()
    for r in stream(d/'sample_receipts.jsonl'):
        if r['kind']=='reject':raw[r['status']]+=1
    assert raw['invalid']==0
    for r in stream(d/'lifecycle.jsonl'):assert not r.get('target_buffer_overflow',False)
    # Temporal links, disjoint intervals. No counterfactual causal attribution.
    events=[];ps=x['prefixes']
    for k,y in enumerate(yields):
        qid=y['source_query_id'];nextid=yields[k+1]['source_query_id'] if k+1<len(yields) else float('inf');later=[i for i,r in enumerate(receipts) if r['query']>qid];assigned=[i for i in later if receipts[i]['query']<nextid];positive=[i for i in later if ps[i]['new_covered']>0];nextcdcl=next((q for q in cdcl if q['query']>qid),None)
        events.append({'run':j['id'],'query':qid,'call_id':y['call_id'],'host_start':y['host_start'],'last_improvement_step':y['last_improvement_step'],'last_improvement_wall':'not_measured','exit_step_exact':y['exit_step_exact'],'host_return':y['host_return'],'next_CDCL_query':nextcdcl['query'] if nextcdcl else None,'next_CDCL_start':nextcdcl['start'] if nextcdcl else None,'next_formal_time':ps[later[0]]['commit_complete'] if later else None,'next_positive_covered_time':ps[positive[0]]['commit_complete'] if positive else None,'nonoverlapping_formal':len(assigned),'nonoverlapping_new_covered':sum(ps[i]['new_covered'] for i in assigned),'no_later_formal':not later})
    csvwrite(d/'ccss_calls.csv',calls);csvwrite(d/'yield_chains.csv',events)
    end=900 if j['budget']=='time900' else min(900,s['elapsed']);auc=0;lastt=lastc=0
    for p in ps:auc+=lastc*(p['commit_complete']-lastt);lastt=p['commit_complete'];lastc=p['covered']
    auc+=lastc*max(0,end-lastt)
    result={'run':j['id'],'input_index':j['input_index'],'instance':j['instance'],'budget':j['budget'],'mode':j['mode'],'formal':x['models'],'raw':s['raw_count'],'duplicates':raw['duplicate'],'duplicate_rate':raw['duplicate']/s['raw_count'] if s['raw_count'] else 0,'invalid':raw['invalid'],'late':sum(z['reason']=='late' for z in read(d/'finalization.json')['omitted']),'omitted_by_reason':dict(collections.Counter(z['reason'] for z in read(d/'finalization.json')['omitted'])),'covered':x['covered'],'total':x['total'],'coverage_percent':100*x['covered']/x['total'],'strict100_completed':x['models']>=100,'seconds_to100':ps[99]['commit_complete'] if len(ps)>=100 else None,'covered_first100':ps[99]['covered'] if len(ps)>=100 else None,'formal_CDCL':sum(r['source']=='CDCL' for r in receipts),'formal_CCSS':sum(r['source']=='CCSS' for r in receipts),'AUC_bit_seconds':auc,'AUC_percent':100*auc/x['total']/end if end else 0,'AUC_interval_seconds':end,'wall':s['elapsed'],'process_wall':t['wall_from_slot_release'],'process_exit_delay':max(0,t['wall_from_slot_release']-900),'user_cpu':t['user_cpu'],'system_cpu':t['system_cpu'],'max_rss_kb':t['max_rss_kb'],'process_exit':t['exit_code'],'raw_status':s['status'],**qc,'CDCL_seconds':qtime['CDCL'],'CCSS_seconds':qtime['CCSS'],'native_calls':ncount,'native_exit_reasons':dict(reasons),'native_exception_texts':dict(errors),'native_search_cpu':search_cpu,'native_search_wall':search_wall,'native_whole_wall':whole_wall,'CCSS_yields':len(yields),'post_yield_formal_nonoverlap':sum(e['nonoverlapping_formal'] for e in events),'post_yield_covered_nonoverlap':sum(e['nonoverlapping_new_covered'] for e in events),'yields_without_later_formal':sum(e['no_later_formal'] for e in events),'guidance_explicit_seconds':s['guidance_cost'],'guidance_exposure_seconds':s['A_exposure'],'guidance_disabled':s['A_disabled'],'guidance_disabled_reason':s['A_disabled_reason'],'cost_limit_queries':limits,'actions':dict(acts),'backend':dict(backend),'official_legal':x['legal']}
    write(d/'run_analysis.json',result)
    write(d/'run_audit.json',{'passed':True,'run':j['id'],'formal_models':x['models'],'yield_calls':len(yields),'native_construction_or_arithmetic_failures_retained':dict(errors),'strict_receipt_deadline_verified':True,'solver_checks_added':0,'hashes':{p.name:digest(p) for p in d.iterdir() if p.is_file() and p.name!='run_audit.json'}})
    print(j['id'],x['models'],x['covered'],dict(reasons),flush=True)
if __name__=='__main__':main()
