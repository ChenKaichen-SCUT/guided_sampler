"""Saved independent100-model development instances; offline set analysis only."""
from common6 import *
from analyze_short import load_bits,compare
assert read(BASE/'formal_analysis/independent_audit.json')['passed'];plan=read(ROOT/'manifests/round6_formal_plan.json');partitions=[];bits=[]
for index in [2,3,4]:
    js=[j for j in plan['jobs'] if j['input_index']==index and j['budget']=='n100_t900'];data={}
    for j in js:
        d=BASE/'formal'/j['id'];assert read(d/'exact.json')['models']==100;data[j['mode']]=load_bits(ROOT/j['input'],d)
    a,b=compare(data['RefG'],data['Chosen'],{'input_index':index,'instance':js[0]['instance'],'budget':'n100_t900','pair':'RefG_vs_Chosen'})
    partitions.extend([{**r,'alignment':'strict100_independent'} for r in a if r['alignment']=='full_session']);bits.extend(b)
    print('Partitioned saved strict100',index,flush=True)
out=BASE/'formal_analysis';csvwrite(out/'development_strict100_partitions.csv',partitions);csvwrite(out/'development_strict100_bit_details.csv',bits);write(out/'development_strict100_partition_audit.json',{'passed':True,'sessions_read':6,'sampler_executions':0,'solver_checks':0,'all_totals_equal_frozen_official':True,'files':{p.name:digest(p) for p in [out/'development_strict100_partitions.csv',out/'development_strict100_bit_details.csv']}})
