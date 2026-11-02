from common6 import *
from batch_runner import run_batch
def main():
    stage=sys.argv[1];assert stage in ['G2','candidate'];cfg=read(ROOT/'configs/round6_guard.json');g1=read(BASE/'guard_analysis/G1_audit.json');assert g1['passed'];mf=ROOT/'manifests'/('round6_implementation.json' if stage=='G2' else 'round6_candidate_implementation.json');freeze=read(mf);tree=ROOT/('worktrees/round6_release' if stage=='G2' else 'worktrees/round6_candidate_release');host=tree/'HighDiv/highdiv';lib=ROOT/('deps/round6_release/lib/libz3.so' if stage=='G2' else 'deps/round6_candidate_release/lib/libz3.so');assert digest(host)==freeze['validation']['release']['binary_sha256'] and digest(lib)==freeze['validation']['release']['library_sha256']
    if stage=='candidate':assert read(BASE/'guard_analysis/G3_decision.json')['chosen'] in ['A','B']
    root=BASE/('guard_short' if stage=='G2' else 'candidate_short');exclusive(BASE/(stage+'_STARTED.json'),{'config_sha256':digest(ROOT/'configs/round6_guard.json'),'freeze_sha256':digest(mf),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'expected_attempts':24 if stage=='G2' else 18});results=[]
    for batch in range(6):
        jobs=[]
        for j in [j for j in cfg[stage] if j['batch']==batch]:
            d=root/j['id'];assert digest(ROOT/j['input'])==j['input_sha256'];mode=j['mode'];ee={k:os.environ[k] for k in ['PATH','LANG','LC_ALL','TMPDIR'] if k in os.environ};ee.update(GUIDED_R6_TRACE_DIR=str(d),GUIDED_CCSS_STAGNATION_GUARD='1' if stage=='candidate' or mode.endswith('G') else '0',GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=j['id'],GUIDED_SEMANTIC_UNMAPPED_LIMIT='0',HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'))
            policy='S_ref' if mode.startswith('Ref') else 'S_full'
            if mode=='Chosen':ee['GUIDED_R6_CANDIDATE']=read(BASE/'guard_analysis/G3_decision.json')['chosen']
            cmd=[str(host),'-i',str((ROOT/j['input']).resolve()),'-o',str(d),'-t','120','-s','0','--guidance',policy]+(['-n','20'] if j['model_limit'] else ['--unlimited-samples'])
            jobs.append({**j,'directory':str(d),'command':cmd,'environment':ee,'binary_sha256':digest(host),'library_sha256':digest(lib)})
        print('Starting',stage,'batch',batch,[(j['id'],j['cpu']) for j in jobs],flush=True);r=run_batch(jobs,BASE/(stage+'_batches')/str(batch),135);results+=r;print('Completed',stage,'batch',batch,'attempts',len(r),flush=True)
        failures=[]
        for j,t in zip(jobs,r):
            p=pathlib.Path(j['directory'])/'summary.json';s=read(p) if p.exists() else {}
            if t['exit_code']!=0 or s.get('status') in ['invalid','error'] or not p.exists():failures.append({'id':j['id'],'process_exit':t['exit_code'],'status':s.get('status','missing_summary')})
        if failures:
            exclusive(BASE/(stage+'_EARLY_STOP.json'),{'executed_attempts':len(results),'failures':failures,'no_retries':True,'remaining_batches_not_started':list(range(batch+1,6))});raise RuntimeError('No further performance batches after failed/corrupt session')
    exclusive(BASE/(stage+'_FINISHED.json'),{'attempts':len(results),'no_retries':True,'results':results});print('Completed',stage,len(results),flush=True)
if __name__=='__main__':main()
