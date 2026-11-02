from common6 import *
g3=read(BASE/'guard_analysis/G3_decision.json');assert g3['chosen']=='FullG' and g3['FullG_promotion']['passed']
assert not (BASE/'F_STARTED.json').exists();f=read(ROOT/'manifests/round6_implementation.json');v=f['validation']['release'];host=ROOT/'worktrees/round6_release/HighDiv/highdiv';lib=ROOT/'deps/round6_release/lib/libz3.so'
assert digest(host)==v['binary_sha256'] and digest(lib)==v['library_sha256'];assert read(BASE/'guard_analysis/independent_audit.json')['passed']
jobs=[];historical={};inputs=read(ROOT/'manifests/inputs.json')
for b,budget in enumerate(['time900','n100_t900']):
    for i,entry in enumerate(inputs):
        inp=ROOT.parent/entry['path'];assert digest(inp)==entry['sha256']
        old=ROOT/'results/baseline_seed0_v1/highdiv'/budget/f'{i:02}'
        for name in ['exact.json','summary.json','formal_receipts.jsonl','wire_coverage.command.json']:
            p=old/name;historical[str(p.relative_to(ROOT))]=digest(p)
        for mode in ['RefG','Chosen']:
            index=len(jobs);jobs.append({'id':f'{i:02}_{mode}_{budget}','queue_index':index,'input_index':i,'instance':inp.name,'input':'../'+entry['path'],'input_sha256':entry['sha256'],'mode':mode,'chosen':'FullG','budget':budget,'cpu':(index+b*8)%16,'seed':0,'wall_seconds':900,'model_limit':100 if b else None,'parent_seconds':915,'cdcl_query_cap':None})
assert len(jobs)==32 and all(sum(j['cpu']==i for j in jobs)==2 for i in range(16))
code={p:digest(ROOT/p) for p in ['scripts/round6/run_formal.py','scripts/round5/batch_worker.py']}
exclusive(ROOT/'manifests/round6_formal_plan.json',{'chosen':'FullG','new_algorithm':False,'G3_decision_sha256':digest(BASE/'guard_analysis/G3_decision.json'),'G3_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'implementation_sha256':digest(ROOT/'manifests/round6_implementation.json'),'config_sha256':digest(ROOT/'configs/round6_guard.json'),'release':v,'code_files':code,'metric_sha256':digest(metric_path()),'historical_files':historical,'jobs':jobs,'slots':list(range(16)),'dispatch':'First time900 job in each slot starts at a common barrier; fixed FIFO second job starts only after its assigned slot is free; no work stealing, no additional jobs','controls_same_build':True,'HighDiv_reruns':0,'additional_seeds':0})
print('Frozen32 F sessions, FullG vs RefG, fixed16-slot FIFO')
