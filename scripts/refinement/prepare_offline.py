from common_r import *
from independent import export,observations,metric_module
import z3
out=attempt('offline','inputs_v1');cfg=read(ROOT/'configs/refinement.json');entries={j['instance']:j for j in cfg['short']}
summary={}
for name,count in cfg['offline_inputs'].items():
    old=ROOT/'results/round5/W'/f'{name}_S_ref';receipts=rows(old/'formal_receipts.jsonl');assert len(receipts)==count
    inp=(ROOT/entries[name]['input']).resolve();assert digest(inp)==entries[name]['input_sha256'];assert all(not q['assumptions'] for q in rows(old/'queries.jsonl'))
    root=z3.And(z3.parse_smt2_file(str(inp)));ast,ns,vs=export(root,digest(inp));original=read(old/'original_nodes.json');assert len(ns)==len(original)
    for i,(e,n) in enumerate(zip(ns,original)):assert n['node']==i and e.decl().kind()==n['operator'] and ast['nodes'][i]['children']==n['children'] and str(e.sort())==n['sort']
    models=[]
    for r in receipts:
        vals={x['name']:x['value'] for x in r['typed']};assert len(vals)==len(vs);models.append([vals[str(v.decl().name())] for v in vs])
    write(out/(name+'.json'),{'ast':ast,'models':models,'input':str(inp),'source_receipts':str(old/'formal_receipts.jsonl'),'source_receipts_sha256':digest(old/'formal_receipts.jsonl'),'native_model_hashes':[r['model_hash'] for r in receipts],'query_ids':[r['query'] for r in receipts]})
    def cpu_paths(x,p=''):
        if isinstance(x,dict):
            for k,v in x.items():
                if 'cpu' in k.lower():yield p+'/'+k
                yield from cpu_paths(v,p+'/'+k)
        elif isinstance(x,list):
            for v in x:yield from cpu_paths(v,p+'/*')
    fields={f:sorted(set(cpu_paths(rows(old/f)))) for f in ['queries.jsonl','models.jsonl','formal_receipts.jsonl','cost_ledger.jsonl','exchange_events.jsonl']}
    summary[name]={'models':count,'nodes':len(ns),'variables':len(vs),'actual_hard_conditions':[],'schema_matches_frozen_original_nodes':True,'cpu_fields_by_file':fields,'per_model_native_cpu_credit_available':False,'reason':'Only whole-session user/system CPU exists in terminal.json; cannot allocate it to a past native-ready prefix or exclude logging/refinement. query check_seconds and model_extract_seconds are wall clocks.','input_sha256':digest(inp),'prepared_sha256':digest(out/(name+'.json'))}
write(out/'summary.json',summary);print('Restored all 43 frozen Ref models; past-prefix CPU credit missing',flush=True)
