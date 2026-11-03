from common_r import *
assert (MAN/'implementation.json').exists();assert not (BASE/'offline/frozen_v1').exists()
cfg=read(ROOT/'configs/refinement.json');source=BASE/'offline/inputs_v1';entries=[]
for name,count in cfg['offline_inputs'].items():
    data=read(source/f'{name}.json');assert len(data['models'])==count
    entries.append({'instance':name,'models':count,'data':str((source/f'{name}.json').relative_to(ROOT)),'sha256':digest(source/f'{name}.json'),'source_receipts_sha256':data['source_receipts_sha256'],'input_sha256':data['ast']['input_sha'],'native_model_hashes':data['native_model_hashes'],'query_ids':data['query_ids'],'hard_conditions':[]})
exclusive(MAN/'offline.json',{'implementation_sha256':digest(MAN/'implementation.json'),'inputs':entries,'order':['L1_main','L2_main','L2_component_only'],'L1_positions':40,'L2_native_models_each_strategy':43,'oracle_positions':[2,3,4,5],'oracle_max_checks':12,'oracle_seconds':2,'oracle_total_seconds':3,'fixed_caps_only':True,'native_past_CPU_credit_available':False,'no_performance_benefit_claim':True,'no_retries':True})
print('offline/oracle input and case order frozen',digest(MAN/'offline.json'))
