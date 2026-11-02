"""Read-only temporal chains for every F yield; no sampling or solver checks."""
from common6 import *
from analyze_short import yield_chains

def main():
    plan=read(ROOT/'manifests/round6_formal_plan.json');events=[];repeats=[];summary=[]
    for j in plan['jobs']:
        d=BASE/'formal'/j['id'];a=read(d/'run_analysis.json')
        if not a['CCSS_yields']:continue
        exact=read(d/'exact.json');chains,rep=yield_chains(d,j['id'],exact)
        assert len(chains)==a['CCSS_yields']
        for r in chains:
            assert r['exit_step_exact']-r['last_improvement_step']==65536
            assert r['last_global_best']>0
            assert r['host_return'] is not None
            if r['next_CDCL_start'] is not None:assert r['next_CDCL_start']>=r['host_return']
            if r['next_formal_latency'] is not None:assert r['next_formal_latency']>=0
        events.extend(chains);repeats.extend(rep)
        summary.append({'run':j['id'],'mode':j['mode'],'budget':j['budget'],'yields':len(chains),'search_wall':sum(r['guard_search_wall'] for r in chains),'search_cpu':sum(r['guard_search_cpu'] for r in chains),'post_yield_models_nonoverlap':sum(r['nonoverlapping_post_yield_models'] for r in chains),'post_yield_covered_nonoverlap':sum(r['nonoverlapping_post_yield_new_covered'] for r in chains),'no_later_formal':sum(r['no_later_formal'] for r in chains)})
    out=BASE/'formal_analysis';csvwrite(out/'yield_chains.csv',events);csvwrite(out/'repeated_maps.csv',repeats);csvwrite(out/'yield_summary.csv',summary)
    assert len(events)==read(out/'independent_audit.json')['yield_calls']
    write(out/'yield_chain_audit.json',{'passed':True,'events':len(events),'rows':summary,'sampler_executions':0,'solver_checks':0,'interpretation':'Temporal suffixes, not counterfactual causal gains; disjoint segments can be summed only within a run.','last_global_improvement_wall':'not measured','files':{p.name:digest(p) for p in [out/'yield_chains.csv',out/'repeated_maps.csv',out/'yield_summary.csv']}})
    print('Audited F temporal yield chains:',len(events),flush=True)

if __name__=='__main__':main()
