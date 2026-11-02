from common5 import *
import shutil
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550'
jobs=[];slots=[0,2,4,6,8,10,12,14,1]
old=read(ROOT/'manifests/round4_short_plan.json')['jobs']
for instance in ['convert','SMT_random','SMT_real']:
    parent=next(j for j in old if j['instance']==instance)
    for mode in ['S_ref','S_full','S_support']:
        jobs.append({'id':instance+'_'+mode,'instance':instance,'mode':mode,'input':parent['input'],'input_sha256':parent['input_sha256'],'cpu':slots[len(jobs)],'wall_seconds':60,'cdcl_cap':32 if instance=='convert' else 8,'seed':0})
config={'base_commit':'ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550','upstream_commit':'f2c6e1756b13281d96cbf90a8bd940129e56cce4','jobs':jobs,'window':64,'quota':4,'explicit_seconds':45,'exposure_seconds':45,'reference_selection_rate':0.5,'X_ids':['X_rr','X_rc','X_cr','X_cc','X_r0','X_c0','X_rr_repeat','X_cc_repeat'],'X_cpu_slots':[0,2,4,6,8,10,12,14],'X_max_seconds':60,'X_parent_seconds':65,'capture_ordinal':2,'capture_roles':['convert_S_ref','convert_S_full','convert_S_support'],'same_batch_release':True,'new_seed':False,'HighDiv_runs':0,'B':False,'nine_jobs_only':True,'test_cases':{str(i+1):s for i,s in enumerate(['full native/action/RNG regression; support-only first divergence at block tie-break','official original AST signed/high-bit/short-circuit identity','shared quota4/window64, dedup and same phase, reference false/unknown','no new constraint/variable/relevance/B; hard/reference provenance','instrumentation on/off native/RNG/map/initialization/model equality','exchange raw roundtrip missing/negative/overflow/difference/empty map','recipe fresh-object structure and RNG equality','snapshot no RNG calls/get_model/map/order mutation','bounded trace overflow, EOF/truncation and cancellation','legal projection/dedup/receipt/official coverage'])}}
exclusive(ROOT/'configs/round5_diagnosis.json',config)
exclusive(ROOT/'manifests/round5_plan.json',{'config_sha256':digest(ROOT/'configs/round5_diagnosis.json'),'guide_sha256':digest(ROOT/'docs/round5/execution_guide.zh.md'),'cpu_topology':subprocess.check_output(['lscpu','-p=CPU,CORE,SOCKET,NODE'],text=True),'allowed_cpus':sorted(os.sched_getaffinity(0)),'tests_frozen_before_implementation':True,'formal_started':False})
metadata={}
for directory in ['results','archives']:
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and 'round5' not in p.parts:
            st=p.stat();metadata[str(p.relative_to(ROOT))]={'size':st.st_size,'mtime_ns':st.st_mtime_ns}
protected={}
for pattern in ['worktrees/*/HighDiv/highdiv','deps/*/lib/libz3.so','include/round4/**/*.hpp','src/round4/*']:
    for p in ROOT.glob(pattern):
        if p.is_file():protected[str(p.relative_to(ROOT))]=digest(p)
exclusive(ROOT/'manifests/round5_protected_before.json',{'metadata':metadata,'protected_sha256':protected,'upstream':{str(p.relative_to(UP)):digest(p) for p in (UP/'z3/src').rglob('*') if p.is_file()},'inputs':{j['input']:j['input_sha256'] for j in old}})
print('Frozen 9 W jobs, 8 conditional X rows, 10 synthetic test groups and protection snapshot.')
