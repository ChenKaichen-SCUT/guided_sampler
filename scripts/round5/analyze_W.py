from common5 import *
from finalize_round2_stream import finalize
from evaluate_round2_official import evaluate
from audit_round4_targets import audit
from audit_round4_soft import targets
from coverage_partition import replay_official_observations,compare_pair

def advice(d,id,data):
    actions=rows(d/'a_actions.jsonl');records=[r for r in rows(d/'lifecycle.jsonl') if r.get('kind')=='round5_decision_audit'];decisions={(r['query_id'],r['backend_call_id'],r['decision_id']):r for r in records};outcomes={}
    for row in rows(d/'a_outcomes.independent.jsonl'):
        for a in row.get('outcomes',[]):outcomes[row['query_id'],a['backend_call_id'],a['decision_id']]=a
    quota=[];funnel=[];targetrows=[];counts=collections.Counter();concentration={}
    for r in records:
        strict=bool(r.get('raw_preferred_kind')=='coverage_support' and r.get('evidence_complete') and r.get('unassigned') and r.get('unattempted_demand_count',0)>0 and r['quota_before']>=4 and r.get('exposure_guard_at_audit') and r.get('cost_guard_at_audit'))
        quota.append({'run':id,**{k:r.get(k) for k in ['query_id','backend_call_id','decision_id','coverage_version','quota_before','quota_after','prior_support','prior_avoid','raw_preferred_kind','unattempted_demand_count','reason','actual_source','changed_vs_native','changed_vs_local_fallback','exposure_guard_at_audit','cost_guard_at_audit']},'support_quota_only_blocked':strict,'avoid_occupied_quota_before_support':strict and r['prior_avoid']>0,'local_counterfactual_only':True})
        counts['scored_or_early_decisions']+=1;counts['reason_'+r['reason']]+=1
        if r.get('raw_preferred_kind'):counts['opportunity_'+r['raw_preferred_kind']]+=1
        if r.get('raw_preferred_kind') and r.get('unattempted_demand_count')==0:counts['raw_score_all_targets_attempted']+=1
        counts['support_quota_only_blocked']+=strict;counts['avoid_occupied_before_support']+=strict and r['prior_avoid']>0
    for source in ['coverage_support','avoid_direct_blocker','inherited_reference']:
        subset=[a for a in actions if a['preference_source']==source];atom=collections.Counter(a['canonical_key'] for a in subset);demands=collections.Counter();unique_hit=set();same_query_hit=set();new=set();nodevariables=set();records_count=0
        for a in subset:
            key=(a['query_id'],a['backend_call_id'],a['decision_id']);di=decisions[key];oc=outcomes.get(key);ts=targets(a['support']);demands.update(ts)
            for n,b,value in ts:
                bit=n*64+b;session=bit in data['prefix'][-1]['seen'][value];unique_hit.update([(n,b,value)] if session else [])
                node=data['nodes'][n];children=[node];visited=set()
                while children:
                    e=children.pop()
                    if e.get_id() in visited:continue
                    visited.add(e.get_id());children.extend(e.children())
                    if not e.children() and e.decl().kind()==45102:nodevariables.add(str(e.decl().name()))
                outcome=next((t for t in oc['targets'] if t['node']==n),None) if oc else None
                hit=None if outcome is None else bool(int(outcome['hit_one_mask' if value else 'hit_zero_mask'])>>b&1)
                newly=None if outcome is None else bool(int(outcome['new_one_mask' if value else 'new_zero_mask'])>>b&1)
                if hit:same_query_hit.add((n,b,value))
                if newly:new.add((n,b,value))
                targetrows.append({'run':id,'query':a['query_id'],'provider':a['backend_call_id'],'decision':a['decision_id'],'source':source,'node':n,'node_fingerprint':data['fingerprints'][n],'sort':str(node.sort()),'bit':b,'desired':value,'same_query_hit':hit,'same_query_new_observation':newly,'same_query_reached':outcome['reached'] if outcome else None,'session_hit':session,'canonical_key':a['canonical_key']})
            assert a['phase_changed']==(a['native_phase']!=a['effective_phase'])
            if source!='inherited_reference':assert di['quota_after']==di['quota_before']+1
        row={'run':id,'source':source,'opportunities':counts['opportunity_'+source] if source!='inherited_reference' else None,'suggestions':len(subset),'actual_phase_changes':sum(a['phase_changed'] for a in subset),'same_native_phase':sum(not a['phase_changed'] for a in subset),'changed_local_fallback':sum(decisions[a['query_id'],a['backend_call_id'],a['decision_id']].get('changed_vs_local_fallback',False) for a in subset),'action_target_records':sum(demands.values()),'unique_demands':len(demands),'unique_nodes':len({t[0] for t in demands}),'unique_variables':len(nodevariables),'unique_atoms':len(atom),'same_query_observed_unique':len(same_query_hit),'same_query_new_unique':len(new),'session_observed_unique':len(unique_hit)}
        funnel.append(row);concentration[source]={'top10_atoms':atom.most_common(10),'top10_demands':[[list(k),v] for k,v in demands.most_common(10)],'variables':sorted(nodevariables),'bit_bands':dict(collections.Counter('low_0_7' if b<8 else 'mid_8_31' if b<32 else 'high_32_63' for (n,b,d),cnt in demands.items() for _ in range(cnt)))}
    return funnel,quota,targetrows,{'counts':counts,'concentration':concentration}

def main():
    perf=[];prefix=[];bits=[];partitions=[];funnels=[];quota=[];targets_=[];details={};data={}
    for j in read(ROOT/'configs/round5_diagnosis.json')['jobs']:
        d=BASE/'W'/j['id'];assert (d/'terminal.json').exists();rc=read(d/'terminal.json')['exit_code']
        if not (d/'finalization.json').exists():finalize(d,60,None)
        if not (d/'exact.json').exists():assert evaluate(d,ROOT/j['input'])=={'official_exit':0,'exact_exit':0}
        if not (d/'target_audit.json').exists():assert audit(d,ROOT/j['input'])['passed']
        x=read(d/'exact.json');s=read(d/'summary.json');qs=rows(d/'queries.jsonl');rs=rows(d/'sample_receipts.jsonl');term=read(d/'terminal.json');r=replay_official_observations(ROOT/j['input'],d);r['elapsed']=s['elapsed'];data[j['id']]=r
        af,aq,at,ad=advice(d,j['id'],r);funnels+=af;quota+=aq;targets_+=at;details[j['id']]=ad
        perf.append({'run':j['id'],'instance':j['instance'],'mode':j['mode'],'exit_code':rc,'status':s['status'],'formal':s['formal_count'],'raw':s['raw_count'],'duplicates':sum(row.get('status')=='duplicate' for row in rs),'invalid':sum(row.get('status')=='invalid' for row in rs),'covered':x['covered'],'total':x['total'],'wall_seconds':s['elapsed'],'user_cpu':term['user_cpu'],'system_cpu':term['system_cpu'],'CDCL_seconds':sum(q['check_seconds'] for q in qs if q['source']=='CDCL'),'CCSS_seconds':sum(q['check_seconds'] for q in qs if q['source']=='CCSS'),'CDCL_queries':sum(q['source']=='CDCL' for q in qs),'CCSS_queries':sum(q['source']=='CCSS' for q in qs),'CDCL_unknown':sum(q['source']=='CDCL' and q['result']=='unknown' for q in qs),'CCSS_unknown':sum(q['source']=='CCSS' and q['result']=='unknown' for q in qs),'formal_CDCL':sum(z['source']=='CDCL' for z in r['receipts']),'formal_CCSS':sum(z['source']=='CCSS' for z in r['receipts']),'explicit_guidance_seconds':s['guidance_cost'],'intervened_query_exposure_seconds':s['A_exposure'],'official_legal':x['legal']})
        print(j['id'],x['covered'],s['formal_count'],flush=True)
    for inst in ['convert','SMT_random','SMT_real']:
        for l,r in [('S_ref','S_full'),('S_ref','S_support'),('S_full','S_support')]:
            pair=l+'_vs_'+r;left=data[inst+'_'+l];right=data[inst+'_'+r];ss,dd,pp=compare_pair(left,right,inst,BASE/'analysis');prefix += [{**x,'pair':pair} for x in ss];bits += [{**x,'pair':pair} for x in dd];partitions += [{**x,'pair':pair} for x in pp]
    csvwrite(BASE/'analysis/W_performance.csv',perf);csvwrite(BASE/'analysis/W_prefix_comparisons.csv',prefix);csvwrite(BASE/'analysis/W_coverage_partition.csv',partitions);csvwrite(BASE/'analysis/W_bit_differences.csv',bits);csvwrite(BASE/'analysis/W_advice_funnel.csv',funnels);csvwrite(BASE/'analysis/W_quota_opportunities.csv',quota);csvwrite(BASE/'analysis/W_target_uniques.csv',targets_);write(BASE/'analysis/W_advice_details.json',details)
    write(BASE/'analysis/W_summary.json',{'passed':True,'sessions':perf,'solver_checks':0,'coverage_equal_official':True,'comparisons':'same new build; policy-dependent trajectories, no statistical or full-HighDiv claim'})
if __name__=='__main__':main()
