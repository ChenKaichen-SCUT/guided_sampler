from common_r import *
from independent import evaluate,observations,covered
from finalize_samples import finalize
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('directory');a=p.parse_args();d=pathlib.Path(a.directory);checks={}
for mode in ['off','identity','improve']:
    root=d/mode;finalize(root,120,None)
    for f in ['native_state.jsonl','query_inputs.jsonl','reference_sources.jsonl']:
        assert rows(root/f)==rows(d/'off'/f),(mode,f);checks[mode+'_'+f]=True
    native=rows(root/'native_models.jsonl');base=rows(d/'off/native_models.jsonl')
    for xs,ys in zip(native,base):
        for key in ['query','source','typed','assignment','native_event_id','native_duplicate','actual_observations','model_hash']:assert xs[key]==ys[key],(mode,key)
    assert len(native)==len(base)
    for ordinal in [1,2]:
        for stage in ['R1','R2','R3','intervals','initial_values']:
            assert read(root/f'ccss_{ordinal}_{stage}.json')==read(d/'off'/f'ccss_{ordinal}_{stage}.json'),(mode,ordinal,stage)
        actual=read(root/f'ccss_{ordinal}_recipe.json');expected=read(d/'off'/f'ccss_{ordinal}_recipe.json')
        assert actual['exchange']['map']==expected['exchange']['map'];assert actual['R0']==expected['R0'];assert actual['build_lits']==expected['build_lits'];checks[mode+f'_internal_map_{ordinal}']=True
    for q in rows(root/'queries.jsonl'):
        if q['guidance']:
            assert all(q['guidance'][k]==0 for k in ['b_encoded','b_internalized','b_selected','guidance_added_assertions','guidance_created_bool_vars','guidance_marked_relevant'])
    if mode!='improve':assert (root/'samples.formal').read_bytes()==(d/'off/samples.formal').read_bytes()
    else:
        summary=read(root/'refinement_summary.json');assert summary['replacements']>=1;assert summary['strict_covered_replacements']>=1
        ast=read(root/'refinement_metadata.json')['ast'];history=set();native_history=set();native_byid={r['native_event_id']:r for r in native if not r['native_duplicate']};candidates=rows(root/'refinement_candidates.jsonl');events={r['native_event_id']:r for r in candidates}
        for out in rows(root/'formal_receipts.jsonl'):
            nr=native_byid[out['native_event_id']];m=nr['assignment'];q=[x['value'] for x in out['typed']];legal,mo=observations(ast,m);qlegal,qo=observations(ast,q);assert legal and qlegal and mo-history<=qo
            if out['replaced']:assert (covered(history|qo),len(history|qo))>(covered(history|mo),len(history|mo));assert q!=m
            history|=qo;native_history|=mo;assert native_history<=history
        assert summary['budget']['optional_cpu']<=summary['budget']['earned_cpu'];assert summary['budget']['optional_wall']<=summary['budget']['earned_wall']
        checks['actual_replacement_count']=summary['replacements'];checks['actual_strict_covered_replacement_count']=summary['strict_covered_replacements']
# Reconstruct authoritative commits after truncation; never rerun solver.
source=(d/'improve/sample_receipts.jsonl').read_text().splitlines(keepends=True);raw=(d/'improve/samples.raw').read_bytes()
for n in range(len(source)+1):
    dest=d/'transaction_prefixes'/f'{n:03}';dest.mkdir(parents=True,exist_ok=False);(dest/'samples.raw').write_bytes(raw);(dest/'sample_receipts.jsonl').write_text(''.join(source[:n])+'{"kind":')
    r=finalize(dest,120,None);assert r['formal_count']==sum(json.loads(s)['kind']=='confirm' and json.loads(s)['timely'] for s in source[:n]);assert len(rows(dest/'formal_receipts.jsonl'))==r['formal_count']
checks['every_receipt_prefix_truncation_replay']=len(source)+1
write(d/'audit.json',{'passed':True,'checks':checks});print('isolation and transaction replay PASS',d)
