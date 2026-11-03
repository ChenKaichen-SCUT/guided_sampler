from common_cr import *
from archive_round4 import Joined
import tarfile
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='ae6da89e16be99142b7402fe6f0bccfb87e19893'
old=read(ROOT/'configs/refinement.json');prior=read(ROOT/'manifests/refinement/implementation.json');old_off=read(ROOT/'manifests/refinement/offline.json')
for p in ['docs/refinement/results.zh.md','docs/refinement/implementation_contract.zh.md','docs/refinement/known_boundaries.zh.md','results/refinement/analysis/final_v1/failure_reasons.json','results/refinement/analysis/final_v1/record_boundaries.json','archives/refinement/RESTORE.md']:(ROOT/p).read_text()
for item in prior['artifacts'].values():assert digest(ROOT/item['path'])==item['sha256']
for item in old_off['inputs']:
    data=read(ROOT/item['data']);assert digest(ROOT/item['data'])==item['sha256'];assert digest(data['source_receipts'])==item['source_receipts_sha256'];assert digest(data['input'])==item['input_sha256'];assert len(data['models'])==item['models']
arc=read(ROOT/'archives/refinement/manifest.json');parts=[ROOT/'archives/refinement'/p['file'] for p in arc['parts']]
for p,r in zip(parts,arc['parts']):assert digest(p)==r['sha256']
count=0
with tarfile.open(fileobj=Joined(parts),mode='r|gz') as tar:
    for member in tar:
        if not member.isfile():continue
        h=hashlib.sha256();f=tar.extractfile(member)
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
        assert h.hexdigest()==arc['members'][member.name]['sha256']==digest(ROOT/member.name),member.name;count+=1
instances=['convert','SMT_random','SMT_real'];modes=['Legacy','ValueCache','Shared'];jobs=[]
for repeat,order in enumerate([modes,modes[1:]+modes[:1],modes[2:]+modes[:2]],1):
    for instance in instances:
        for mode in order:jobs.append({'id':f'{instance}_{mode}_L2_r{repeat}','instance':instance,'mode':mode,'layer':'L2','component_only':False,'repeat':repeat})
for instance in instances:
    for mode in ['Legacy','Shared']:
        for layer,component in [('L1',False),('L2',True)]:jobs.append({'id':f'{instance}_{mode}_{layer}'+('_component' if component else '')+'_once','instance':instance,'mode':mode,'layer':layer,'component_only':component,'repeat':None})
probes=[{'id':f'{n}_{mode}','instance':n,'mode':mode,'positions':[2,3,4,5]} for mode in modes for n in instances]
oracles=[{'id':f'{n}_{pos:02}_{mode}','instance':n,'position':pos,'mode':mode} for n in instances for pos in [2,3,4,5] for mode in ['OracleLegacy','OracleShared']]
config={'base':'ae6da89e16be99142b7402fe6f0bccfb87e19893','source_models':43,'replayed_events':559,'cpu':0,'seed':0,'online_sessions':0,'B':False,'guard':65536,'numeric_cache_initialization':'empty per anchor; no native trace prefill','affine_constant':'old coefficient dot product order, separate anchor cache','dependency':'complete syntactic parent closure; x-x remains affected','budgets':{'preprocess':.1,'event':.02,'sequence':6,'probe_preprocess':2,'probe_event':.5,'probe_worker_wall':5,'oracle_case_wall':3,'oracle_check_wall':2},'limits':{k:old[k] for k in ['direction_pool','directions_per_event','ranked_directions','targets_per_direction','hits_per_target','full_candidates_per_event','component_variables','component_rows','component_nonzeros','integer_bits','interval_limit','domain_ops','elimination_ops']},'offline':jobs,'probes':probes,'oracles':oracles,'historical_cpu_credit_proven':False,'tests':{'reuse_math':'244612 arithmetic,1356 hits,7938 domain points,4 direction systems,32 official traces','deep_DAG_nodes':12000,'support_sets':'all subsets for fixed four-variable DAGs','anchor_sequence':[[0,1],[2,-3],[-1,1<<63]],'oracle_extra_widths':[1,2,8,64],'synthetic_seed':0,'real_fixed_workload_probes_only':True}}
assert len(jobs)==39 and sum(next(i['models'] for i in old_off['inputs'] if i['instance']==j['instance']) for j in jobs)==559
exclusive(ROOT/'configs/refinement_cost_repair.json',config)
metadata={};sha={}
for folder in ['results','archives']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file() and 'refinement_cost_repair' not in p.parts:st=p.stat();metadata[str(p.relative_to(ROOT))]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
for pattern in ['docs/refinement/*','manifests/refinement/*','configs/refinement.json','worktrees/refinement_*/refinement_include/*']:
    for p in ROOT.glob(pattern):
        if p.is_file():sha[str(p.relative_to(ROOT))]=digest(p)
exclusive(MAN/'protected.json',{'metadata':metadata,'sha256':sha,'prior_artifacts':prior['artifacts'],'inputs':old_off['inputs']})
exclusive(MAN/'plan.json',{'config_sha256':digest(ROOT/'configs/refinement_cost_repair.json'),'guide_sha256':digest(ROOT/'docs/refinement_cost_repair/execution_guide.zh.md'),'source_models':43,'replayed_events':559,'cpu_topology':subprocess.check_output(['lscpu','-p=CPU,CORE,SOCKET'],text=True),'allowed_cpus':sorted(os.sched_getaffinity(0)),'old_archive_verified_members':count,'before_cost_implementation':True,'new_real_sampler_sessions':0,'oracle_max_cases':24})
write(BASE/'readonly/verification.json',{'passed':True,'old_archive_members':count,'old_models':43,'old_results_unchanged':True,'old_implementation_sha256':digest(ROOT/'manifests/refinement/implementation.json'),'metric_sha256':digest(metric_path()),'required_json_documents_fully_loaded':True});print('Plan frozen; all old evidence verified',count)
