"""Audit actual quota use and replay pure scores/dedup on the frozen encountered prefix."""
from common5 import *
from audit_round4_soft import targets

def evidence(cat,masks,key):
    support=[set(),set()];block=[set(),set()]
    for r in cat.get(key,{}).get('rules',[]):
        n=r['node'];s0,s1=map(int,masks[n]);p=int(r['phase'])
        for d,want,known,opp in [(1,s0&~s1,int(r['known_one']),int(r['known_zero'])),(0,s1&~s0,int(r['known_zero']),int(r['known_one']))]:
            for bit in range(64):
                if want>>bit&1:
                    if known>>bit&1:support[p].add((n,bit,d))
                    if opp>>bit&1:block[p].add((n,bit,d))
    return support,block

def audit(directory,run):
    cat={r['key']:r for r in rows(directory/'a_atom_catalog.jsonl')};snap={r['query_id']:r for r in rows(directory/'coverage_snapshots.jsonl')};actions=rows(directory/'a_actions.jsonl');aa={(r['query_id'],r['backend_call_id'],r['decision_id']):r for r in actions};used=collections.defaultdict(set);refs=collections.defaultdict(set);quota=collections.Counter();kindquota=collections.defaultdict(collections.Counter);out=[];counts=collections.Counter();bykind={};encounters=[]
    for s in rows(directory/'semantic.jsonl'):
        if s['kind']=='semantic_snapshot':
            for e in s['encounters']:
                if 'preference_source' in e:encounters.append((s,e))
    for s,e in sorted(encounters,key=lambda x:(x[0]['external_query_id'],x[1]['decision_id'],x[0]['backend_call_id'])):
        q=s['external_query_id'];provider=s['backend_call_id'];key=e['canonical_key'];neg=e['canonical_negated'];support,block=evidence(cat,snap[q]['seen_masks'],key);scores=[(len(support[p]),-len(block[p])) for p in range(2)];best=None if not e['evidence_complete'] or scores[0]==scores[1] else scores[1]>scores[0];kind=None if best is None else 'coverage_support' if len(support[0])!=len(support[1]) else 'avoid_direct_blocker'
        candidate=set() if best is None else (support[best] if kind=='coverage_support' else block[not best]-block[best]);untried={t for t in candidate if (key,best,kind,t) not in used[q]};ref=e['reference_phase'];rk=(key,(ref is True)!=neg);fallback=ref if ref is not None and rk not in refs[q] else e['native_phase'];a=aa.get((q,provider,e['decision_id']));before=quota[q];qa=kindquota[q]['avoid_direct_blocker'];qs=kindquota[q]['coverage_support']
        potential=bool(kind=='coverage_support' and untried and before>=4)
        if potential:counts['recorded_support_candidates_after_quota']+=1;counts['with_prior_avoid_quota']+=bool(qa)
        if best is not None and candidate and not untried:counts['raw_score_but_all_targets_attempted']+=1
        for p,label in [(0,'false'),(1,'true')]:
            if e['evidence_complete']:assert len(support[p!=neg])==e['support_'+label] and len(block[p!=neg])==e['block_'+label]
        if a:
            counts['actions']+=1;source=a['preference_source'];counts[source]+=1;counts[source+'_changed_vs_native']+=a['phase_changed'];counts[source+'_changed_vs_fallback']+=a['effective_phase']!=fallback
            if source in ['coverage_support','avoid_direct_blocker']:
                assert before<4 and targets(a['support'])==untried
                quota[q]+=1;kindquota[q][source]+=1;used[q].update((key,best,kind,t) for t in untried)
            else:refs[q].add((key,a['effective_phase']!=neg))
        out.append(dict(run=run,query=q,provider=provider,decision=e['decision_id'],coverage_version=s['coverage_version'],native_key=key,native_phase=e['native_phase'],negated=neg,support_false=e['support_false'],support_true=e['support_true'],block_false=e['block_false'],block_true=e['block_true'],evidence_complete=e['evidence_complete'],reference_phase=ref,raw_preferred_kind=kind,unattempted_demand_count=len(untried),quota_before=before,quota_after=quota[q],prior_support=qs,prior_avoid=qa,source=a['preference_source'] if a else 'no_action',changed_vs_native=a['phase_changed'] if a else False,local_fallback_phase=fallback,changed_vs_local_fallback=a['effective_phase']!=fallback if a else False,quota_limited_support_candidate=potential,support_quota_only_blocked='not_recorded' if potential else False,guard_at_exact_decision='not_recorded',score_provenance='recomputed_from_frozen_prefix',unassigned='true_by_executed_hook_guard'))
    assert counts['actions']==len(actions)
    for source in ['coverage_support','avoid_direct_blocker','inherited_reference']:
        subset=[a for a in actions if a['preference_source']==source];ts=collections.Counter(t for a in subset for t in targets(a['support']));atoms=collections.Counter(a['canonical_key'] for a in subset);n=len(subset)
        bykind[source]={'actions':n,'same_native':sum(not a['phase_changed'] for a in subset),'changed_native':sum(a['phase_changed'] for a in subset),'changed_local_fallback':counts[source+'_changed_vs_fallback'],'action_target_records':sum(ts.values()),'unique_demands':len(ts),'unique_nodes':len({t[0] for t in ts}),'unique_atoms':len(atoms),'top10_demands':[[list(t),c] for t,c in ts.most_common(10)],'top10_atoms':atoms.most_common(10),'top10_atom_action_fraction':sum(c for k,c in atoms.most_common(10))/n if n else None,'bit_bands':dict(collections.Counter('low_0_7' if t[1]<8 else 'mid_8_31' if t[1]<32 else 'high_32_63' for t in ts.elements()))}
    counts['recorded_scored_opportunities']=len(encounters)
    return out,{'run':run,'counts':counts,'by_source':bykind,'strict_quota_only_count':'not_recorded','actual_actions_complete':True,'source_hashes':{f:digest(directory/f) for f in ['a_actions.jsonl','semantic.jsonl','coverage_snapshots.jsonl','a_atom_catalog.jsonl']}}

def main():
    allrows=[];summaries=[]
    for j in read(ROOT/'manifests/round4_short_plan.json')['jobs']:
        if j['stage']!='S':continue
        r,s=audit(OLD/'runs'/j['id'],j['id']);allrows+=r;summaries.append(s);print(j['id'],dict(s['counts']),flush=True)
    csvwrite(BASE/'readonly/advice_quota_audit.csv',allrows);write(BASE/'readonly/advice_summary.json',{'passed':True,'runs':summaries,'solver_calls':0})
    write(BASE/'readonly/old_log_missing_fields.json',{'missing':{'exact_guard_status_at_each_rejected_decision':'not_recorded; cannot prove quota was sole refusal','pre_guard_early_exit_decision_record':'not_recorded; unsupported normalization/already propagated cannot be inferred from no action','all_candidate_masks_before_dedup':'recomputed_from_frozen_prefix using actual atom catalog and snapshot','local_fallback_reference_attempted':'recomputed_from_frozen_prefix using committed reference actions','whole_counterfactual_ref_trajectory':'not_observable; local fallback is not S_ref trajectory','internal_CDCL_exchange_map':'not_recorded; formal original projection is not a substitute','exchange_producer_lifecycle':'not_recorded','CCSS_recipe_R0_R3_initialization':'not_recorded'},'not_recorded_is_not_zero':True,'solver_calls':0})
if __name__=='__main__':main()
