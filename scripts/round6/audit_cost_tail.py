"""Read-only active-vs-disabled cost accounting; never changes frozen behavior."""
from common6 import *
assert (BASE/'F_FINISHED.json').exists();out=BASE/'formal_analysis';out.mkdir(exist_ok=True);result=[]
for j in read(ROOT/'manifests/round6_formal_plan.json')['jobs']:
    d=BASE/'formal'/j['id'];first=None;last=None
    with (d/'cost_ledger.jsonl').open() as f:
        for line in f:
            r=json.loads(line);last=r
            if first is None and r['disabled']:first=r
    s=read(d/'summary.json');tail={k:v-(first['categories'].get(k,0) if first else v) for k,v in (last or {}).get('categories',{}).items()};tail={k:v for k,v in tail.items() if abs(v)>1e-9};actions_after=metadata_after=0
    if first:
        with (d/'queries.jsonl').open() as f:
            for line in f:
                q=json.loads(line)
                if q['query']>first['query_id']:
                    g=q.get('guidance',{});actions_after+=len(g.get('actions',[]));metadata_after+=sum(bool(b.get('metadata_received')) for b in g.get('backend_calls',[]))
    assert actions_after==metadata_after==0,'Disabled guidance still intervened; correctness review required'
    result.append({'run':j['id'],'instance':j['instance'],'budget':j['budget'],'mode':j['mode'],'disabled':s['A_disabled'],'reason':s['A_disabled_reason'],'first_disabled_query':first['query_id'] if first else None,'explicit_at_first_disabled_ledger':first['explicit_seconds'] if first else None,'final_explicit_counter':s['guidance_cost'],'counter_above45':s['guidance_cost']>45,'active_phase_actions_after_disabled':actions_after,'actual_backend_metadata_after_disabled':metadata_after,'post_disable_counter_increase':(last['explicit_seconds']-first['explicit_seconds']) if first else 0,'post_disable_cost_categories':tail,'post_disable_reference_and_input_cost':sum(v for k,v in tail.items() if k in ['reference_collection_and_inputs_log_seconds','reference_source_log_seconds']),'exposure_counter':s['A_exposure']})
csvwrite(out/'cost_tail.csv',result);write(out/'cost_tail_audit.json',{'passed':True,'meaning_of_passed':'Attribution and shutdown audit, not a claim that all guidance costs stayed below45','rows':result,'over45_runs':sum(r['counter_above45'] for r in result),'post_disable_counter_seconds_total':sum(r['post_disable_counter_increase'] for r in result),'active_interventions_after_disabled':0,'total_guidance_cost_bounded_by45':not any(r['counter_above45'] for r in result),'cause':'Inherited soft-reference collection/input logging and reference-source logging remain charged after guidance->disabled. Active backend registration and phase suggestions stop, but these host costs do not.','scope':'Read-only diagnosis; production code and all completed sessions unchanged','next_single_factor_not_implemented':'Stop constructing unused reference preferences and full reference diagnostic payloads after permanent guidance shutdown, while preserving exact original RNG consumption and native m_ls/map exchange; keep required guard logs.'});print('Cost-tail audit retained',sum(r['counter_above45'] for r in result),'counter overruns')
