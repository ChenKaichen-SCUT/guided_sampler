"""Apply preregistered gates to completed, independently audited evidence."""
from common6 import *
def promotion(summary,pair,useful,correctness):
    cs=[r for r in summary['comparisons'] if r['pair']==pair]
    time=[r for r in cs if r['budget']=='time120'];n20=[r for r in cs if r['budget']=='n20_t120' and r['strict20_eligible']]
    mean_time=sum(r['coverage_pp_delta'] for r in time)/len(time) if time else None
    mean_n20=sum(r['strict20_pp_delta'] for r in n20)/len(n20) if n20 else None
    positive=sorted({r['instance'] for r in time if r['coverage_pp_delta']>0}&{r['instance'] for r in n20 if r['strict20_pp_delta']>0})
    right=pair.split('_vs_')[1];lookup={(r['instance'],r['budget'],r['mode']):r for r in summary['sessions']}
    disasters=[]
    for r in summary['sessions']:
        if r['mode']!=right:continue
        ref=lookup[(r['instance'],r['budget'],'RefG')]
        if r['covered']<.5*ref['covered']:disasters.append(r['run'])
    conditions={'three_time_instances':len(time)==3,'time_mean_positive':mean_time is not None and mean_time>0,'two_completed_n20_pairs':len(n20)>=2,'strict_n20_mean_positive':mean_n20 is not None and mean_n20>0,'two_instances_positive_in_both':len(positive)>=2,'correctness':bool(correctness),'useful_guard':bool(useful),'no_unexplained_disaster':not disasters}
    return {'passed':all(conditions.values()),'conditions':conditions,'time_mean_pp':mean_time,'strict20_mean_pp':mean_n20,'strict20_paired_instances':[r['instance'] for r in n20],'positive_in_both':positive,'large_regressions_requiring_review':disasters,'failed_conditions':[k for k,v in conditions.items() if not v]}
def main():
    out=BASE/'guard_analysis';assert not (out/'G3_decision.json').exists();audit=read(out/'independent_audit.json');assert audit['passed']
    summary=read(out/'summary.json');local=read(out/'G1_audit.json');sessions={(r['instance'],r['budget'],r['mode']):r for r in summary['sessions']}
    useful=[];supply=[];real_early=[]
    for r in summary['comparisons']:
        if r['budget']!='time120' or r['pair'] not in ['Ref_vs_RefG','Full_vs_FullG']:continue
        g=sessions[(r['instance'],r['budget'],r['pair'].split('_vs_')[1])]
        if r['extra_formal']>0:supply.append(r)
        if r['extra_CDCL']>0 and r['extra_formal']>0 and r['covered_delta']>0 and g['post_yield_formal_nonoverlap']>0 and g['post_yield_covered_nonoverlap']>0:useful.append(r)
    for r in summary['sessions']:
        d=BASE/'guard_short'/r['run'];qs={q['query']:q for q in rows(d/'queries.jsonl')}
        for n in rows(d/'ccss_guard.jsonl'):
            if n['exit_reason']=='ccss_stagnation_yield' and n['search_wall_seconds']<qs[n['source_query_id']]['granted_timeout']:real_early.append({'run':r['run'],'query':n['source_query_id']})
    gtime=local['local_time_halved'] and bool(real_early);p=promotion(summary,'RefG_vs_FullG',bool(useful),audit['passed'])
    with (out/'coverage_partitions.csv').open() as f:parts=list(csv.DictReader(f))
    quality=[]
    for inst in ['convert','SMT_random','SMT_real']:
        for budget in ['time120','n20_t120']:
            rr=[r for r in parts if r['instance']==inst and r['budget']==budget and r['pair']=='RefG_vs_FullG' and r['alignment']=='common_prefix']
            net=sum(int(r['net']) for r in rr);outside=sum(int(r['net']) for r in rr if r['group'] in ['G2','G3'])
            if net<0 and outside<0:quality.append({'instance':inst,'budget':budget,'common_prefix_net':net,'G2_G3_net':outside})
    if not local['passed']:chosen='No-Go';reason='G1 failed'
    elif not gtime:chosen='No-Go';reason='No registered time recovery'
    elif p['passed']:chosen='FullG';reason='FullG already meets promotion; no new mechanism'
    elif useful and quality:chosen='A';reason='Useful supply, but equal-prefix quality lost outside G1; fixed Full/Ref alternation'
    elif not supply and summary['eligible_repeat_map_pairs']>0:chosen='B';reason='No additional legal supply and repeated identical consumed map without intervening legal CDCL'
    else:chosen='No-Go';reason='Evidence does not satisfy a registered single-factor candidate or direct promotion'
    exclusive(out/'G3_decision.json',{'chosen':chosen,'reason':reason,'G_PASS_LOCAL':local['passed'],'G_PASS_TIME':gtime,'G_PASS_USEFUL':bool(useful),'G_PASS_COVERAGE':p['passed'],'useful_matched_rows':useful,'supply_increase_rows':supply,'real_early_yields':real_early,'quality_loss_rows':quality,'FullG_promotion':p,'audit_sha256':digest(out/'independent_audit.json'),'summary_sha256':digest(out/'summary.json'),'decision_commit_parent':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'candidate_implementation_started':False,'formal900_started':False})
    print('G3:',chosen,reason,p)
if __name__=='__main__':main()
