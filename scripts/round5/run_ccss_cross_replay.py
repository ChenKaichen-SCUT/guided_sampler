from common5 import *
from batch_runner import run_batch
def plan():
    fid=read(BASE/'analysis/X_capture_fidelity.json');cfg=read(ROOT/'configs/round5_diagnosis.json');jobs=[]
    for i,(id,h,m) in enumerate([('X_rr','ref','ref'),('X_rc','ref','full'),('X_cr','full','ref'),('X_cc','full','full'),('X_r0','ref','empty'),('X_c0','full','empty'),('X_rr_repeat','ref','ref'),('X_cc_repeat','full','full')]):
        valid=fid['sources'].get(h,{}).get('passed',False);reason=None if valid else 'reconstruction_not_validated'
        if valid and m not in ['empty',h] and not fid['compatibility'][h+'_'+m]['passed']:valid=False;reason='incompatible_recipe_map'
        rp=BASE/'capture'/h/'recipe.json';mp=BASE/'capture'/(h if m=='empty' else m)/('empty_map.json' if m=='empty' else 'map.json')
        r=read(rp) if rp.exists() else {};cutoff=r.get('cutoff_seconds')
        if valid:assert 0<=cutoff<=60,'Do not alter production-recorded cutoff'
        jobs.append({'id':id,'H':h,'M':m,'cpu':cfg['X_cpu_slots'][i],'execute':valid,'skip_reason':reason,'recipe':str(rp.relative_to(ROOT)),'map':str(mp.relative_to(ROOT)),'recipe_sha256':digest(rp) if rp.exists() else None,'map_sha256':digest(mp) if mp.exists() else None,'native_cutoff_seconds':cutoff,'parent_seconds':65})
    exclusive(ROOT/'manifests/round5_X_plan.json',{'rows':jobs,'capture_manifest_sha256':digest(ROOT/'manifests/round5_capture.json'),'seed_from_capture_only':True});print('Frozen X rows',sum(j['execute'] for j in jobs),'of 8')
def execute():
    spec=read(ROOT/'manifests/round5_X_plan.json');freeze=read(ROOT/'manifests/round5_implementation.json');binary=ROOT/'build/round5-ccss-replay-release';assert digest(binary)==freeze['validation']['release']['replay_sha256'];jobs=[]
    exclusive(BASE/'X_STARTED.json',{'plan_sha256':digest(ROOT/'manifests/round5_X_plan.json'),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    for row in spec['rows']:
        if not row['execute']:continue
        rp=ROOT/row['recipe'];mp=ROOT/row['map'];assert digest(rp)==row['recipe_sha256'] and digest(mp)==row['map_sha256'];d=BASE/'replay'/row['id'];env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL','TMPDIR'] if k in os.environ}
        jobs.append({**row,'directory':str(d),'command':[str(binary),str(rp),str(mp),str(d),row['id'],'0'],'environment':env,'binary_sha256':digest(binary)})
    results=run_batch(jobs,BASE/'X_batch',65) if jobs else []
    exclusive(BASE/'X_FINISHED.json',{'executed':len(jobs),'skipped':8-len(jobs),'results':results,'no_retries':True});print('Finished X',len(jobs))
if __name__=='__main__':(plan if sys.argv[1]=='plan' else execute)()
