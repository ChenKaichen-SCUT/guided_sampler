from common_r import *
import statistics
out=BASE/'oracle/frozen_v1';records=[];cfg=read(ROOT/'configs/refinement.json')
for name in cfg['offline_inputs']:
    data=read(BASE/'offline/frozen_v1'/f'{name}_L1_main/result.json')['result'];amort_w=data['preprocess_wall']/(cfg['offline_inputs'][name]-1);amort_c=data['preprocess_cpu']/(cfg['offline_inputs'][name]-1)
    for pos in cfg['oracle_positions']:
        d=out/f'{name}_{pos:02}';r=read(d/'result.json');e=read(d/'execution.json');event=data['events'][pos-1];chosen=event['chosen'];success=bool(chosen and chosen['gain_covered']>event['base_gain_covered']);common=success and r['status']=='sat' and r.get('independent_validation',False);cw=event.get('event_wall',0)+amort_w;cc=event.get('event_cpu',0)+amort_c
        records.append({'instance':name,'position':pos,'candidate_strict_covered_success':success,'candidate_reason':event['reason'],'candidate_cpu_with_amortized_preprocess':cc,'candidate_wall_with_amortized_preprocess':cw,'oracle_status':r['status'],'oracle_checks':r.get('checks'),'oracle_cpu':e['cpu'],'oracle_wall':e['wall'],'common_success':common,'cpu_ratio':cc/e['cpu'] if common else None,'wall_ratio':cw/e['wall'] if common else None,'oracle_answer_censored':r['status'] in ['unknown','oracle_case_external_timeout','oracle_case_timeout'],'native_prefix_cpu_credit_missing':True})
common=[r for r in records if r['common_success']];instances=set(r['instance'] for r in common);enough=len(common)>=3 and len(instances)>=2;cheap=enough and statistics.median(r['cpu_ratio'] for r in common)<=.2 and statistics.median(r['wall_ratio'] for r in common)<=.2
csvwrite(out/'comparison.csv',records);write(out/'summary.json',{'cases':12,'records':records,'statuses':dict(collections.Counter(r['oracle_status'] for r in records)),'common_successes':len(common),'common_instances':sorted(instances),'significantly_cheaper_claim_supported':cheap,'unknown_not_imputed_as_success':True,'real_online_speedup_claim':False})
print('oracle summary',len(common),'common successes',cheap)
