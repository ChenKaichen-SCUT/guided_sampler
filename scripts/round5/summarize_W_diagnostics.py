from common5 import *
def main():
    out=[]
    for d in sorted((BASE/'W').iterdir()):
        q=rows(d/'queries.jsonl');last=rows(d/'cost_ledger.jsonl')[-1];s=read(d/'summary.json');term=read(d/'terminal.json');a=rows(d/'a_actions.jsonl');r=rows(d/'formal_receipts.jsonl');pre=[x for x in rows(d/'lifecycle.jsonl') if x.get('kind')=='round5_decision_audit']
        out.append({'run':d.name,'wall_seconds':s['elapsed'],'configured_wall':60,'wall_overrun_seconds':max(s['elapsed']-60,0),'cpu_seconds':term['user_cpu']+term['system_cpu'],'cumulative_last_ledger':last['categories'],'last_ledger_explicit_seconds':last['explicit_seconds'],'final_summary_explicit_seconds':s['guidance_cost'],'query_prepare_seconds':sum(x['guidance_prepare_seconds'] for x in q),'first_model_hash':r[0]['model_hash'],'first_full_avoid_action':next(({'query':x['query_id'],'decision':x['decision_id'],'atom':x['canonical_key']} for x in a if x['preference_source']=='avoid_direct_blocker'),None),'decision_audit_target_overflows':sum(x.get('target_buffer_overflow',False) for x in pre),'fields_not_individually_measured':['exchange producer per-write logging CPU','whole-function model recovery outside recorded reconstruction timer'],'last_ledger_is_before_final_logging':True,'formal_deadline_seconds':60,'overrun_not_counted_as_extra_formal_budget':True})
    write(BASE/'analysis/W_cost_and_limit_details.json',out)
    summary=[]
    with (BASE/'analysis/W_bit_differences.csv').open() as f:
        count=collections.Counter()
        for x in csv.DictReader(f):
            if x['alignment']!='full_session':continue
            count[x['instance'],x['pair'],x['group'],x['covered_only'],x['other_visited'],x['missing_value_available_without_reach'],x['covered_source']]+=1
        for key,n in sorted(count.items()):summary.append(dict(zip(['instance','pair','group','covered_only','other_visited','missing_value_available_without_reach','covered_source'],key),bits=n))
    csvwrite(BASE/'analysis/W_loss_diagnosis.csv',summary)
    print('Saved cumulative cost, overrun, trace bounds, and bit loss/source summaries')
if __name__=='__main__':main()
