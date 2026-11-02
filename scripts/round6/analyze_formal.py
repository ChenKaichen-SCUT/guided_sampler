"""Post-F only; four independent official-scoring processes, then comparisons."""
from common6 import *
import concurrent.futures
def main():
    assert read(BASE/'F_FINISHED.json')['attempts']==32;plan=read(ROOT/'manifests/round6_formal_plan.json');out=BASE/'formal_analysis';out.mkdir(exist_ok=True);logs=BASE/'build_logs/F_scoring';logs.mkdir(exist_ok=True)
    for p,h in plan['historical_files'].items():assert digest(ROOT/p)==h,p
    def score(j):
        d=BASE/'formal'/j['id']
        if (d/'run_audit.json').exists():assert read(d/'run_audit.json')['passed'];return j['id'],0
        attempt=len(list(logs.glob(j['id']+'_*.log')))+1
        with (logs/(j['id']+f'_{attempt:02}.log')).open('x') as log:r=subprocess.run([str(python()),str(ROOT/'scripts/round6/score_formal_one.py'),j['id']],stdout=log,stderr=subprocess.STDOUT)
        print('F score',j['id'],r.returncode,flush=True);return j['id'],r.returncode
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:status=list(pool.map(score,plan['jobs']))
    write(out/'scoring_attempts.json',{'sessions':status,'workers':4,'after_F_finished':True,'new_sampler_calls':0})
    assert all(rc==0 for _,rc in status),'Retain all failures; no performance reruns'
    perf=[];audits=[];curves=out/'curves.csv'
    with curves.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=['run','instance','input_index','budget','mode','index','commit_complete','covered','total','new_covered','source']);writer.writeheader()
        for j in plan['jobs']:
            d=BASE/'formal'/j['id'];r=read(d/'run_analysis.json');perf.append(r);audits.append(read(d/'run_audit.json'));x=read(d/'exact.json')
            for p in x['prefixes']:writer.writerow({**{k:j[k] for k in ['instance','input_index','budget','mode']},'run':j['id'],**{k:p[k] for k in ['index','commit_complete','covered','total','new_covered','source']}})
    comparisons=[];historical=[]
    with (ROOT/'results/summary.csv').open() as f:old_summary={(r['input'],r['mode']):r for r in csv.DictReader(f) if r['config']=='highdiv'}
    for i,entry in enumerate(read(ROOT/'manifests/inputs.json')):
        for budget in ['time900','n100_t900']:
            left=next(r for r in perf if r['input_index']==i and r['budget']==budget and r['mode']=='RefG');right=next(r for r in perf if r['input_index']==i and r['budget']==budget and r['mode']=='Chosen')
            bdir=ROOT/'results/baseline_seed0_v1/highdiv'/budget/f'{i:02}';bx=read(bdir/'exact.json');bs=read(bdir/'summary.json');bo=old_summary[(pathlib.Path(entry['path']).name,budget)]
            assert bx['legal'] and bx['total']==right['total'];base={'run':'historical_HighDiv_'+str(i)+'_'+budget,'input_index':i,'instance':right['instance'],'budget':budget,'mode':'HighDiv','formal':bx['models'],'covered':bx['covered'],'total':bx['total'],'coverage_percent':100*bx['covered']/bx['total'],'wall':bs['elapsed'],'AUC_percent':float(bo['auc_percentage']),'seconds_to100':float(bo['time100']) if bo['time100'] else None,'raw_status':bs['status']};historical.append(base)
            for l,r,pair in [(left,right,'RefG_vs_Chosen'),(base,right,'HighDiv_vs_Chosen'),(base,left,'HighDiv_vs_RefG')]:
                strict=budget=='n100_t900' and l['formal']==r['formal']==100
                comparisons.append({'input_index':i,'instance':r['instance'],'budget':budget,'pair':pair,'left_models':l['formal'],'right_models':r['formal'],'left_covered':l['covered'],'right_covered':r['covered'],'total':r['total'],'covered_delta':r['covered']-l['covered'],'coverage_pp_delta':r['coverage_percent']-l['coverage_percent'],'strict100_eligible':strict,'strict100_pp_delta':r['coverage_percent']-l['coverage_percent'] if strict else None,'models_delta':r['formal']-l['formal'],'AUC_percent_delta':r['AUC_percent']-l['AUC_percent'],'wall_delta':r['wall']-l['wall'],'same_planned_current_cohort':pair=='RefG_vs_Chosen','same_internal_state_claim':False})
    aggregate=[]
    for pair in ['RefG_vs_Chosen','HighDiv_vs_Chosen','HighDiv_vs_RefG']:
        for budget in ['time900','n100_t900']:
            rr=[r for r in comparisons if r['pair']==pair and r['budget']==budget];strict=[r for r in rr if r['strict100_eligible']]
            assert len(rr)==8
            aggregate.append({'pair':pair,'budget':budget,'instances':8,'equal_weight_endpoint_mean_pp':sum(r['coverage_pp_delta'] for r in rr)/8,'positive_instances':[r['instance'] for r in rr if r['coverage_pp_delta']>0],'negative_instances':[r['instance'] for r in rr if r['coverage_pp_delta']<0],'strict100_completed_pairs':len(strict),'strict100_mean_pp':sum(r['strict100_pp_delta'] for r in strict)/len(strict) if strict else None,'strict100_positive_instances':[r['instance'] for r in strict if r['strict100_pp_delta']>0],'incomplete_not_scored_as_tie':[r['instance'] for r in rr if budget=='n100_t900' and not r['strict100_eligible']]})
    csvwrite(out/'performance.csv',perf);csvwrite(out/'historical_HighDiv_readonly.csv',historical);csvwrite(out/'comparisons.csv',comparisons);csvwrite(out/'aggregate.csv',aggregate)
    # Verify recorded fixed-slot FIFO and barrier; no counterfactual resource claim.
    dispatch=rows(BASE/'F_queue/dispatch.jsonl');assert len(dispatch)==32 and len({r['id'] for r in dispatch})==32
    byid={j['id']:j for j in plan['jobs']}
    for cpu in range(16):
        expected=[j for j in plan['jobs'] if j['cpu']==cpu];actual=[r for r in dispatch if r['cpu']==cpu];assert [r['id'] for r in actual]==[j['id'] for j in expected]
        first=read(BASE/'formal'/expected[0]['id']/'terminal.json');assert actual[1]['released']>=first['completed_monotonic']
    for r in dispatch:
        ready=read(BASE/'F_queue'/(r['id']+'.ready.json'));assert ready['affinity']==[r['cpu']] and ready['monotonic_ready']<=r['released']
    assert all(len(r['live'])<=16 and len({p['cpu_slot'] for p in r['live']})==len(r['live']) for r in rows(BASE/'F_queue/concurrency.jsonl'))
    write(out/'summary.json',{'passed':True,'chosen':'FullG','new_algorithm':False,'sessions':perf,'historical':historical,'comparisons':comparisons,'aggregate':aggregate,'formal_attempts':32,'new_HighDiv_runs':0,'seed':0,'resources_not_matched_to_historical_HighDiv':True,'new_algorithm_vs_FullG':'not_applicable; FullG directly promoted','single_seed_no_statistical_stability_claim':True})
    write(out/'independent_audit.json',{'passed':True,'stage':'F','attempts':32,'formal_models':sum(r['formal'] for r in perf),'yield_calls':sum(r['CCSS_yields'] for r in perf),'solver_checks_added':0,'same_release_for_all_controls':True,'strict_receipt_deadline_verified':True,'fixed_slot_FIFO_verified':True,'B_enabled':False,'rows':audits})
    print('F scored and audited32, formal models',sum(r['formal'] for r in perf),flush=True)
if __name__=='__main__':main()
