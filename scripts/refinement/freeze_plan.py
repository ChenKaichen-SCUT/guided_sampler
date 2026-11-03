"""Read-only source restoration and preregistration; never runs an old sampler."""
from common_r import *
from archive_round4 import Joined
import tarfile
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='9270e83b7e95b9d9e51e0246de939d82ff570dce'
g3=read(ROOT/'results/round6/guard_analysis/G3_decision.json');assert all(g3[k] for k in ['G_PASS_LOCAL','G_PASS_TIME','G_PASS_USEFUL'])
old=read(ROOT/'configs/round5_diagnosis.json');jobs=[]
for batch,(budget,inst) in enumerate((budget,inst) for budget in ['time120','n20_t120'] for inst in ['convert','SMT_random','SMT_real']):
    parent=next(j for j in old['jobs'] if j['instance']==inst)
    for k,mode in enumerate(['Ref','RefObserve','RefImprove','Full']):
        jobs.append({'id':inst+'_'+mode+'_'+budget,'instance':inst,'mode':mode,'budget':budget,'batch':batch,'cpu':[0,2,4,6][(batch+k)%4],'seed':0,'wall_seconds':120,'model_limit':20 if budget=='n20_t120' else None,'input':parent['input'],'input_sha256':parent['input_sha256'],'guard':True,'query_limit':None})
config={'base_commit':'9270e83b7e95b9d9e51e0246de939d82ff570dce','historical_ref_commit':'ae85956068154207a442c0e2c8387c573dc32411','generator':'R5 Ref soft reference, no coverage; shared validated R6 guard','guard':True,'guard_limit':65536,'guard_evidence_sha256':digest(ROOT/'results/round6/guard_analysis/G3_decision.json'),'seed':0,'B':False,'direction_pool':256,'directions_per_event':16,'ranked_directions':8,'targets_per_direction':8,'hits_per_target':4,'full_candidates_per_event':64,'event_seconds':0.020,'preprocess_seconds':0.100,'session_fraction':0.05,'earned_fraction':0.10,'minimum_remaining_seconds':0.010,'component_variables':64,'component_rows':128,'component_nonzeros':4096,'integer_bits':4096,'interval_limit':4096,'domain_ops':200000,'elimination_ops':200000,'short':jobs,'offline_inputs':{'convert':27,'SMT_random':8,'SMT_real':8},'L1_positions':40,'L2_sequences':['main','component_only'],'oracle_positions':[2,3,4,5],'oracle_check_seconds':2,'oracle_total_seconds':3,'oracle_max_checks':12,'oracle_cold_start':True,'tests':{'integer_exhaustion':'signed coefficients/offsets -6..6, moduli 1..16; deterministic enumerations; separate all-residue tests','domain_exhaustion':'t -24..24, fixed enumerated formulas','synthetic_seed':0,'identity_and_actual_replacement_required':True},'gates':{'offline':'all correctness/isolation; main L2 strict covered improvement on >=2 instances; all endpoints contain native; actual improvements within established CPU AND wall credit; no credit invented if historical cost missing','short':'RefImprove-Ref equal-weight time120 mean positive and >=2 positive; strict independent20 common completed set >=2, mean positive and >=2 positive; no decline >0.5pp OR >5% of Ref covered; online strict extra covered replacements >=2 instances; no correctness/isolation/deadline/unexplained budget error','formal':'only after short passed;32 sessions, fixed16 CPU slots; two positive means and >=2 positive cases for each budget; strict100 only completed intersections'},'no_resampling_old_runs':True,'no_additional_seed':True,'no_parameter_search':True}
exclusive(ROOT/'configs/refinement.json',config)
exclusive(MAN/'plan.json',{'config_sha256':digest(ROOT/'configs/refinement.json'),'guide_sha256':digest(ROOT/'docs/refinement/execution_guide.zh.md'),'cpu_topology':subprocess.check_output(['lscpu','-p=CPU,CORE,SOCKET,NODE'],text=True),'allowed_cpus':sorted(os.sched_getaffinity(0)),'implementation_not_started':True,'offline_sequence_models':43,'single_step_positions':40,'oracle_max_cases':12,'conditional_short':24,'conditional_formal':32})
metadata={}
for folder in ['results','archives']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file() and 'refinement' not in p.parts:
            st=p.stat();metadata[str(p.relative_to(ROOT))]={'size':st.st_size,'mtime_ns':st.st_mtime_ns}
protected={str(p.relative_to(ROOT)):digest(p) for pattern in ['manifests/round5*.json','manifests/round6*.json','docs/round4_mapping_and_soft_reference_results.zh.md','docs/round5*.md','include/round5/*','include/round6/*','src/round5/*','src/round6/*'] for p in ROOT.glob(pattern) if p.is_file()}
metric=ROOT/'worktrees/baseline/HighDiv/my_scripts/calc_metric.py';protected[str(metric.relative_to(ROOT))]=digest(metric)
exclusive(MAN/'protected_before.json',{'metadata':metadata,'sha256':protected,'inputs':read(ROOT/'manifests/inputs.json')})
print('Plan and generator frozen; verifying old archive',flush=True)
m=read(ROOT/'archives/round5/manifest.json');parts=[ROOT/'archives/round5'/r['file'] for r in m['parts']]
for p,r in zip(parts,m['parts']):assert digest(p)==r['sha256']
count=0
with tarfile.open(fileobj=Joined(parts),mode='r|gz') as tar:
    for entry in tar:
        if not entry.isfile():continue
        h=hashlib.sha256();f=tar.extractfile(entry)
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
        assert h.hexdigest()==m['members'][entry.name]['sha256']==digest(ROOT/entry.name),entry.name
        count+=1
for name,h in read(ROOT/'manifests/round5_W_evidence.json')['files'].items():assert digest(ROOT/name)==h,name
for r in read(ROOT/'manifests/inputs.json'):assert digest(ROOT.parent/r['path'])==r['sha256']
for variant in ['release','sanitize']:
    for name,r in read(ROOT/'manifests/round5_implementation.json')['sources'].items():assert digest(ROOT/f'worktrees/round5_{variant}'/name)==r['sha256']
    r6=read(ROOT/'manifests/round6_implementation.json')
    for name,r in r6['sources'][variant].items():assert digest(ROOT/f'worktrees/round6_{variant}'/name)==r['sha256']
    for path,h in [(ROOT/f'worktrees/round6_{variant}/HighDiv/highdiv',r6['validation'][variant]['binary_sha256']),(ROOT/f'deps/round6_{variant}/lib/libz3.so',r6['validation'][variant]['library_sha256'])]:assert digest(path)==h
write(BASE/'readonly/evidence.json',{'passed':True,'R5_archive_members':count,'old_sampler_executions':0,'solver_checks':0,'metric_sha256':digest(metric),'guard_shared':True,'guard_reason':'R6 correctness,219-step preservation and actual useful convert end-to-end production established; all modes fixed on before this round'})
print('Frozen evidence verified',count,flush=True)
