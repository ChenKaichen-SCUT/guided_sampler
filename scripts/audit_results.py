#!/usr/bin/env python3
import concurrent.futures,collections,json,math,pathlib,subprocess
from common import *
from finalize_samples import finalize,records
from evaluate_official import evaluate

def audit(run):
    d=ROOT/run['output'];result={'id':run['id'],'input':run['input_name'],'config':run['config'],'mode':run['mode'],'errors':[]}
    try:
        terminal=read(d/'terminal.json');final=finalize(d,run['wall'],run['limit']);metric=evaluate(d,ROOT/run['input']);result.update(metric)
        if metric['official_exit'] or metric['exact_exit']:result['errors'].append('metric_or_legality_failure')
        if not (d/'exact.json').exists():raise RuntimeError('Missing exact audit')
        exact=read(d/'exact.json');assert exact['models']==final['formal_count']
        output=(d/'wire_coverage.stdout').read_text().strip()
        if exact['official_class_result'] not in output:result['errors'].append('official_percentage_mismatch')
        if not exact['legal']:result['errors'].append('illegal_formal_model')
        for row in records(d/'models.jsonl'):
            if row.get('legal') is False:result['errors'].append('illegal_raw_candidate')
        sources=collections.Counter(p['source'] for p in exact['prefixes']);times=[p['commit_complete'] for p in exact['prefixes']]
        counts=[p['covered'] for p in exact['prefixes']];auc=0;last_t=0;last_c=0
        for t,c in zip(times,counts):auc+=(t-last_t)*last_c;last_t=t;last_c=c
        auc+=(run['wall']-last_t)*last_c;auc=auc/run['wall']/exact['total']*100 if exact['total'] else 0
        time_curves={str(t):next((p['covered'] for p in reversed(exact['prefixes']) if p['commit_complete']<=t),0) for t in [1,5,10,30,60,120,300,600,900]}
        sample_curves={str(n):counts[n-1] if len(counts)>=n else None for n in [1,2,5,10,20,50,100]}
        guidance=collections.Counter();query_counts=collections.Counter();costs=collections.Counter()
        routes=collections.defaultdict(list)
        owners=set()
        for route in records(d/'routes.jsonl'):routes[route['check_epoch']].append(route['backend']);owners.add(route['solver'])
        if len(owners)>1:result['errors'].append('multiple_combined_solver_route_owners')
        cdcl_epoch=0;enriched=[]
        for q in records(d/'queries.jsonl'):
            query_counts[q['source']+'_'+q['result']]+=1;costs[q['source']+'_check_seconds']+=q['check_seconds']
            g=q.get('guidance',{})
            if q['source']=='CDCL':
                cdcl_epoch+=1;route=routes.get(cdcl_epoch,[])
                if not route:result['errors'].append('missing_backend_receipt')
                q['actual_backend_path']=route;q['actual_fallback']=len(route)>1
                if g and route and g.get('backend')!={'smt':2,'tactic':1}[route[-1]]:result['errors'].append('guidance_backend_receipt_mismatch')
            else:q['actual_backend_path']=['tactic_ccss'];q['actual_fallback']=False
            enriched.append(q)
            for k in ['ordinary','a_used','b_used','a_live','b_internalized','b_relevant','propagated','special','cap','deferred','a_changed','a_same','native_registered_targets','unsupported','fallback']:guidance[k]+=g.get(k,0)
            for k in ['prepare_seconds','broker_seconds']:costs[k]+=g.get(k,0)
            if g.get('a_used',0)> (2 if run['config']=='a_plus_b' else 4):result['errors'].append('A_budget_violation')
            if g.get('b_used',0)> (2 if run['config']=='a_plus_b' else 4):result['errors'].append('B_budget_violation')
            used=[]
            for e in g.get('events',[]):
                used+=e['targets']
                if e['ordinary']>64:result['errors'].append('decision_window_violation')
                if e['source']=='A' and e['native_var']!=e['actual_var']:result['errors'].append('A_changed_variable')
            if len(set(used))!=len(used):result['errors'].append('target_attempt_repeated_in_epoch')
        with open(d/'queries.audited.jsonl','x') as f:
            for q in enriched:f.write(json.dumps(q)+'\n')
        windows=collections.Counter();target_ids=set()
        for e in records(d/'guidance_events.jsonl'):
            if 'target_id' in e:
                windows[e.get('sort','unknown')]+=1;windows['low' if e['bit']<16 else 'mid' if e['bit']<48 else 'high']+=1
                windows['a_static_match']+=int(e.get('a_static_match',0)>0);windows[e.get('encoding','A_only')]+=1;target_ids.add(e['target_id'])
        host=read(d/'summary.json') if (d/'summary.json').exists() else {}
        if host.get('formal_count') is not None and host['formal_count']!=final['formal_count']:result['errors'].append('online_formal_count_mismatch')
        if terminal['exit_code'] not in (0,-15,-9):result['errors'].append('unexpected_exit')
        result.update(models=exact['models'],complete100=exact['models']>=100,time100=times[99] if len(times)>=100 else None,
            first_model=times[0] if times else None,covered=exact['covered'],total=exact['total'],percentage=100*exact['covered']/exact['total'],official=output,
            auc_percentage=auc,source_models=dict(sources),status=host.get('status','process_failed'),terminal=terminal,
            queries=dict(query_counts),guidance=dict(guidance),costs={**dict(costs),'explicit_seconds':host.get('guidance_cost')},
            window=dict(windows),distinct_targets=len(target_ids),time_curve=time_curves,sample_curve=sample_curves,
            new_observed=exact['observed'],new_covered=exact['covered'],late=sum(x['reason']=='late' for x in final['omitted']),raw_rejections=dict(collections.Counter(x['reason'] for x in final['omitted'])))
        result['valid']=not result['errors']
    except Exception as e:result['errors'].append(str(e));result['valid']=False
    write(d/'audit.json',result)
    hashes={str(p.relative_to(d)):digest(p) for p in sorted(d.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'}
    write(d/'artifact_hashes.json',hashes)
    return result

def main():
    assert (ROOT/'results/QUEUE_FINISHED.json').exists(),'No independent audit during sampling'
    plan=read(ROOT/'manifests/plan.json')
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:results=list(pool.map(audit,plan['runs']))
    write(ROOT/'results/audit_summary.json',{'runs':results,'passed':all(r['valid'] for r in results),'count':len(results)})
    baseline=[r for r in plan['runs'] if r['config']=='highdiv'];assert len(baseline)==16
    freeze={'baseline_id':'baseline_seed0_v1','plan_sha256':digest(ROOT/'manifests/plan.json'),'build':plan['artifacts']['baseline'],'metric':plan['artifacts']['metric'],
        'runs':{r['id']:{'input_sha256':r['input_sha256'],'artifact_manifest_sha256':digest(ROOT/r['output']/'artifact_hashes.json'),'artifacts':read(ROOT/r['output']/'artifact_hashes.json')} for r in baseline}}
    exclusive(ROOT/'results/baseline_seed0_v1/BASELINE_FROZEN.json',freeze)
    print(json.dumps({'runs':len(results),'valid':sum(r['valid'] for r in results),'errors':[(r['id'],r['errors']) for r in results if r['errors']]}))
if __name__=='__main__':main()
