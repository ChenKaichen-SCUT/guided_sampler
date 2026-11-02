"""Official scoring, exact compact bitsets, yield chains and matched controls. No checks."""
from common6 import *
from finalize_round2_stream import finalize
from evaluate_round2_official import evaluate
from audit_round4_targets import audit as audit_targets
from audit_round4_soft import targets
from semantic_oracle import Witness,metric,z3,dag
def load_bits(formula,d):
    witness=Witness();m=metric.ManualSatisfiesMetric(pathlib.Path(formula).read_text(),witness);nodes,ids=dag(z3.And(m._solver.assertions()));stored=read(d/'original_nodes.json');assert len(nodes)==len(stored)
    universe=0;known=0
    for i,n in enumerate(nodes):
        assert stored[i]['sort']==str(n.sort()) and stored[i]['children']==[ids[c.get_id()] for c in n.children()]
        if n.get_id() in witness._storage:universe|=((1 if z3.is_bool(n) else (1<<64)-1)<<(64*i))
    for a in rows(d/'a_atom_catalog.jsonl'):
        for r in a['rules']:known|=(int(r['known_one'])|int(r['known_zero']))<<(64*r['node'])
    seen0=seen1=0;prefix=[];receipts=rows(d/'formal_receipts.jsonl')
    with (d/'samples.formal').open() as f:
        for i,sample in enumerate(metric.parse_samples(f)):
            witness.current={};assert m.count_sample(sample)
            for astid,value in witness.current.items():
                n=ids[astid];mask=1 if z3.is_bool(nodes[n]) else (1<<64)-1;v=int(value)&mask;seen0|=(mask^v)<<(64*n);seen1|=v<<(64*n)
            covered=seen0&seen1
            if receipts[i]['covered'] is not None:assert covered.bit_count()==receipts[i]['covered']
            prefix.append((seen0,seen1,covered))
    return {'prefix':prefix,'universe':universe,'known':known,'receipts':receipts,'fingerprints':[sha_text(n.sexpr()) for n in nodes],'sha':digest(formula)}
def at(r,n):return r['prefix'][n-1] if n else (0,0,0)
def partition(l,r):
    assert l['universe']==r['universe'];u=l['universe'];L=at(l,1) if l['prefix'] else (0,0,0);R=at(r,1) if r['prefix'] else (0,0,0);diff=((L[0]^R[0])|(L[1]^R[1]))&u;g0=L[2]&~diff;g3=u&~(L[0]|L[1])&~diff;g1=l['known']&r['known']&(L[0]^L[1])&(R[0]^R[1])&~diff&u;g2=u&~(diff|g0|g1|g3);groups={'G0':g0,'G1':g1,'G2':g2,'G3':g3,'G4_initial_difference':diff};assert sum(x.bit_count() for x in groups.values())==u.bit_count();return groups
def compare(l,r,identity):
    groups=partition(l,r);out=[];details=[];n=min(len(l['prefix']),len(r['prefix']));align=[('full_session',len(l['prefix']),len(r['prefix'])),('common_prefix',n,n)]
    for k in [1,3,10,20]:
        if k<=n:align.append(('strict_prefix_'+str(k),k,k))
    for name,ln,rn in align:
        lc=at(l,ln)[2];rc=at(r,rn)[2]
        for g,mask in groups.items():
            gain=rc&~lc&mask;loss=lc&~rc&mask;out.append({**identity,'alignment':name,'group':g,'partition_size':mask.bit_count(),'left_models':ln,'right_models':rn,'left_covered':lc.bit_count(),'right_covered':rc.bit_count(),'left_only':loss.bit_count(),'right_only':gain.bit_count(),'net':gain.bit_count()-loss.bit_count()})
            if name=='full_session':
                for side,bits in [('left',loss),('right',gain)]:
                    other=at(r,rn) if side=='left' else at(l,ln)
                    while bits:
                        bit=(bits&-bits).bit_length()-1;bits&=bits-1;node,b=divmod(bit,64);details.append({**identity,'group':g,'covered_only':side,'node':node,'fingerprint':l['fingerprints'][node],'bit':b,'other_seen0':bool((other[0]>>bit)&1),'other_seen1':bool((other[1]>>bit)&1),'input_sha256':l['sha']})
    return out,details
def yield_chains(d,id,exact):
    q=rows(d/'queries.jsonl');rr=[{**r,**p} for r,p in zip(rows(d/'formal_receipts.jsonl'),exact['prefixes'])];native=rows(d/'ccss_guard.jsonl');host={r['source_query_id']:r for r in rows(d/'ccss_guard_host.jsonl')};ys=[r for r in native if r['exit_reason']=='ccss_stagnation_yield'];events=[]
    for i,y in enumerate(ys):
        query=y['source_query_id'];hq=host.get(query,{});end=hq.get('host_end');futureq=[r for r in q if r['query']>query];fm=[r for r in rr if r['query']>query];positive=[r for r in fm if r['new_covered']>0];nextyield=ys[i+1]['source_query_id'] if i+1<len(ys) else float('inf');assigned=[r for r in fm if r['query']<nextyield];nextcdcl=next((r for r in futureq if r['source']=='CDCL'),None)
        events.append({'run':id,'query':query,'call_id':y['call_id'],'map_sha256':y['map_sha256'],'consumed_map_sha256':y['consumed_map_sha256'],'host_call_start':hq.get('start'),'last_global_best':y['last_global_best'],'last_improvement_step':y['last_improvement_step'],'last_improvement_wall':'not_measured_in_integer_only_hot_path','exit_step_exact':y['exit_step_exact'],'guard_search_wall':y['search_wall_seconds'],'guard_search_cpu':y['search_cpu_seconds'],'host_return':end,'next_CDCL_query':nextcdcl['query'] if nextcdcl else None,'next_CDCL_start':nextcdcl['start'] if nextcdcl else None,'next_formal_query':fm[0]['query'] if fm else None,'next_formal_time':fm[0]['commit_complete'] if fm else None,'next_formal_latency':fm[0]['commit_complete']-end if fm and end is not None else None,'next_positive_covered_query':positive[0]['query'] if positive else None,'next_positive_covered_time':positive[0]['commit_complete'] if positive else None,'next_positive_covered_latency':positive[0]['commit_complete']-end if positive and end is not None else None,'no_later_formal':not fm,'nonoverlapping_post_yield_models':len(assigned),'nonoverlapping_post_yield_new_covered':sum(r['new_covered'] for r in assigned),'future_CDCL_checks':sum(r['source']=='CDCL' for r in futureq),'future_CCSS_checks':sum(r['source']=='CCSS' for r in futureq),'causal_interpretation':'temporal chain only; suffix counts overlap and must not be summed'})
    repeat=[];raw=[r for r in rows(d/'sample_receipts.jsonl') if r.get('kind') in ['prepare','reject'] and r.get('legal') and r.get('source')=='CDCL']
    for l,r in zip(native,native[1:]):
        if l['exit_reason']==r['exit_reason']=='ccss_stagnation_yield' and l['consumed_map_sha256']==r['consumed_map_sha256']:
            middle=[z for z in raw if l['source_query_id']<z['query']<r['source_query_id']];repeat.append({'run':id,'left_query':l['source_query_id'],'right_query':r['source_query_id'],'same_consumed_map':True,'intervening_legal_CDCL_raw':len(middle),'eligible_cooldown_evidence':not middle})
    return events,repeat
def main():
    stage=sys.argv[1];assert stage in ['G2','candidate'];root=BASE/('guard_short' if stage=='G2' else 'candidate_short');out=BASE/('guard_analysis' if stage=='G2' else 'candidate_analysis');out.mkdir(exist_ok=True);jobs=read(ROOT/'configs/round6_guard.json')[stage];perf=[];curves=[];chains=[];repeat=[];funnel=[];groups=[];details=[];comparisons=[]
    for inst in ['convert','SMT_random','SMT_real']:
        for budget in ['time120','n20_t120']:
            data={};current={}
            for j in [j for j in jobs if j['instance']==inst and j['budget']==budget]:
                d=root/j['id'];assert (d/'terminal.json').exists()
                if not (d/'finalization.json').exists():finalize(d,120,j['model_limit'])
                if not (d/'exact.json').exists():assert evaluate(d,ROOT/j['input'])=={'official_exit':0,'exact_exit':0}
                if not (d/'target_audit.json').exists():assert audit_targets(d,ROOT/j['input'])['passed']
                x=read(d/'exact.json');s=read(d/'summary.json');t=read(d/'terminal.json');q=rows(d/'queries.jsonl');raw=rows(d/'sample_receipts.jsonl');native=rows(d/'ccss_guard.jsonl');ec,er=yield_chains(d,j['id'],x);chains+=ec;repeat+=er;ps=x['prefixes'];auc=0;last_time=0;last_cov=0;end=120 if budget=='time120' else min(120,s['elapsed'])
                for p in ps:
                    moment=p['commit_complete'];auc+=last_cov*(moment-last_time);last_time=moment;last_cov=p['covered'];curves.append({'run':j['id'],**p})
                auc+=last_cov*max(0,end-last_time);r={'run':j['id'],'instance':inst,'budget':budget,'mode':j['mode'],'formal':x['models'],'raw':s['raw_count'],'duplicates':sum(z.get('status')=='duplicate' for z in raw),'invalid':sum(z.get('status')=='invalid' for z in raw),'covered':x['covered'],'total':x['total'],'coverage_percent':100*x['covered']/x['total'],'covered_first10':ps[9]['covered'] if len(ps)>=10 else None,'covered_first20':ps[19]['covered'] if len(ps)>=20 else None,'strict20_completed':len(ps)>=20,'seconds_to20':ps[19]['commit_complete'] if len(ps)>=20 else None,'covered_bit_seconds_AUC':auc,'normalized_coverage_AUC_percent':100*auc/x['total']/end if end else None,'AUC_interval_seconds':end,'wall':s['elapsed'],'exit_delay':max(0,s['elapsed']-120),'user_cpu':t['user_cpu'],'system_cpu':t['system_cpu'],'max_rss_kb':t['max_rss_kb'],'process_exit':t['exit_code'],'raw_status':s['status'],'formal_CDCL':sum(p['source']=='CDCL' for p in ps),'formal_CCSS':sum(p['source']=='CCSS' for p in ps),'CDCL_checks':sum(z['source']=='CDCL' for z in q),'CCSS_checks':sum(z['source']=='CCSS' for z in q),'CDCL_unknown':sum(z['source']=='CDCL' and z['result']=='unknown' for z in q),'CCSS_unknown':sum(z['source']=='CCSS' and z['result']=='unknown' for z in q),'CCSS_yields':len(ec),'yield_search_wall':sum(z['guard_search_wall'] for z in ec),'yield_search_cpu':sum(z['guard_search_cpu'] for z in ec),'post_yield_formal_nonoverlap':sum(z['nonoverlapping_post_yield_models'] for z in ec),'post_yield_covered_nonoverlap':sum(z['nonoverlapping_post_yield_new_covered'] for z in ec),'yields_without_later_formal':sum(z['no_later_formal'] for z in ec),'native_exit_reasons':dict(collections.Counter(z['exit_reason'] for z in native)),'guidance_explicit_seconds':s['guidance_cost'],'guidance_exposure_seconds':s['A_exposure'],'official_legal':x['legal']};perf.append(r);current[j['mode']]=r
                acts=rows(d/'a_actions.jsonl');outcomes={(z['query_id'],a['backend_call_id'],a['decision_id']):a for z in rows(d/'a_outcomes.independent.jsonl') for a in z.get('outcomes',[])}
                for source in ['coverage_support','avoid_direct_blocker','inherited_reference']:
                    aa=[a for a in acts if a['preference_source']==source];unique=set();hit=set()
                    for a in aa:
                        ts=targets(a['support']);unique.update(ts);oc=outcomes.get((a['query_id'],a['backend_call_id'],a['decision_id']))
                        if oc:
                            for n,b,value in ts:
                                target=next((t for t in oc['targets'] if t['node']==n),None)
                                if target and (int(target['new_one_mask' if value else 'new_zero_mask'])>>b)&1:hit.add((n,b,value))
                    funnel.append({'run':j['id'],'source':source,'suggestions':len(aa),'actual_phase_changes':sum(a['phase_changed'] for a in aa),'unique_demands':len(unique),'same_query_new_observed_unique':len(hit)})
                data[j['mode']]=load_bits(ROOT/j['input'],d);print(stage,j['id'],x['models'],x['covered'],len(ec),flush=True)
            pairs=[('Ref','RefG'),('Full','FullG'),('RefG','FullG')] if stage=='G2' else [('RefG','FullG'),('RefG','Chosen'),('FullG','Chosen')]
            for left,right in pairs:
                ident={'instance':inst,'budget':budget,'pair':left+'_vs_'+right};a,b=compare(data[left],data[right],ident);groups+=a;details+=b;l=current[left];r=current[right];strict=budget=='n20_t120' and l['formal']==r['formal']==20
                comparisons.append({**ident,'left_models':l['formal'],'right_models':r['formal'],'covered_delta':r['covered']-l['covered'],'coverage_pp_delta':r['coverage_percent']-l['coverage_percent'],'strict20_eligible':strict,'strict20_pp_delta':r['coverage_percent']-l['coverage_percent'] if strict else None,'extra_formal':r['formal']-l['formal'],'extra_CDCL':r['CDCL_checks']-l['CDCL_checks'],'extra_CCSS':r['CCSS_checks']-l['CCSS_checks'],'duplicates_delta':r['duplicates']-l['duplicates'],'wall_delta':r['wall']-l['wall'],'CPU_delta':r['user_cpu']+r['system_cpu']-l['user_cpu']-l['system_cpu'],'AUC_percent_delta':r['normalized_coverage_AUC_percent']-l['normalized_coverage_AUC_percent'],'paired_same_state_causal_claim':False})
    for name,data_ in [('performance',perf),('curves',curves),('yield_chains',chains),('repeated_maps',repeat),('target_funnel',funnel),('coverage_partitions',groups),('bit_details',details),('matched_comparisons',comparisons)]:csvwrite(out/(name+'.csv'),data_)
    write(out/'summary.json',{'passed':True,'stage':stage,'sessions':perf,'comparisons':comparisons,'yield_events':len(chains),'eligible_repeat_map_pairs':sum(r['eligible_cooldown_evidence'] for r in repeat),'official_metric_unchanged':True,'solver_checks_added':0,'last_improvement_wall_not_recorded':True});print(stage,'analysis complete',len(perf),flush=True)
if __name__=='__main__':main()
