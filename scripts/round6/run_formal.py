"""Exactly the frozen 32 jobs, one process per fixed CPU slot, no retry."""
from common6 import *
import signal
def main():
    mf=ROOT/'manifests/round6_formal_plan.json';plan=read(mf);g3=read(BASE/'guard_analysis/G3_decision.json');assert g3['chosen']=='FullG' and g3['FullG_promotion']['passed'];assert digest(BASE/'guard_analysis/G3_decision.json')==plan['G3_decision_sha256']
    for p,h in plan['code_files'].items():assert digest(ROOT/p)==h,p
    host=ROOT/'worktrees/round6_release/HighDiv/highdiv';lib=ROOT/'deps/round6_release/lib/libz3.so';assert digest(host)==plan['release']['binary_sha256'] and digest(lib)==plan['release']['library_sha256']
    for j in plan['jobs']:assert digest(ROOT/j['input'])==j['input_sha256']
    qdir=BASE/'F_queue';qdir.mkdir(exist_ok=False);root=BASE/'formal';root.mkdir(exist_ok=False);queues={cpu:collections.deque(j for j in plan['jobs'] if j['cpu']==cpu) for cpu in plan['slots']};running={};finished=[];failures=[]
    exclusive(BASE/'F_STARTED.json',{'plan_sha256':digest(mf),'expected_attempts':32,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    def spawn(j,gate):
        d=root/j['id'];d.mkdir();ready=qdir/(j['id']+'.ready.json');env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL','TMPDIR'] if k in os.environ};env.update(GUIDED_R6_TRACE_DIR=str(d),GUIDED_CCSS_STAGNATION_GUARD='1',GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=j['id'],GUIDED_SEMANTIC_UNMAPPED_LIMIT='0',HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'))
        cmd=[str(host),'-i',str((ROOT/j['input']).resolve()),'-o',str(d),'-t','900','-s','0','--guidance','S_ref' if j['mode']=='RefG' else 'S_full']+(['-n','100'] if j['model_limit'] else ['--unlimited-samples'])
        spec={**j,'directory':str(d),'ready':str(ready),'gate':str(gate),'cwd':str(d),'command':cmd,'environment':env,'binary_sha256':plan['release']['binary_sha256'],'library_sha256':plan['release']['library_sha256']}
        exclusive(d/'attempt.json',{k:v for k,v in spec.items() if k!='environment'});write(qdir/(j['id']+'.worker.json'),spec)
        with (d/'stdout.log').open('x') as stdout,(d/'stderr.log').open('x') as stderr:p=subprocess.Popen([sys.executable,ROOT/'scripts/round5/batch_worker.py',qdir/(j['id']+'.worker.json')],stdout=stdout,stderr=stderr,start_new_session=True)
        return {'process':p,'job':j,'ready':ready,'gate':gate,'start':None}
    def await_ready(records):
        deadline=time.monotonic()+30
        while not all(r['ready'].exists() for r in records):
            if time.monotonic()>deadline:raise RuntimeError('Ready barrier failed; retain attempts, no relaunch')
            time.sleep(.01)
    gate=qdir/'INITIAL_RELEASE.json'
    for cpu in plan['slots']:
        r=spawn(queues[cpu].popleft(),gate);running[r['process'].pid]=r
    await_ready(list(running.values()));now=time.monotonic();exclusive(gate,{'monotonic':now,'count':16,'cpu_slots':plan['slots']})
    for r in running.values():r['start']=now
    print('F started16 time900 sessions',flush=True)
    with (qdir/'dispatch.jsonl').open('x') as dispatch,(qdir/'concurrency.jsonl').open('x') as monitor:
        for r in running.values():dispatch.write(json.dumps({'id':r['job']['id'],'cpu':r['job']['cpu'],'released':now})+'\n')
        dispatch.flush()
        while running:
            now=time.monotonic();live=[]
            for pid,r in list(running.items()):
                got,status,usage=os.wait4(pid,os.WNOHANG)
                if got:
                    rc=os.waitstatus_to_exitcode(status);r['process'].returncode=rc;j=r['job'];d=root/j['id'];terminal={'exit_code':rc,'user_cpu':usage.ru_utime,'system_cpu':usage.ru_stime,'max_rss_kb':usage.ru_maxrss,'wall_from_slot_release':time.monotonic()-r['start'],'released_monotonic':r['start'],'completed_monotonic':time.monotonic(),'cpu':j['cpu'],'no_retry':True};write(d/'terminal.json',terminal);finished.append({'id':j['id'],**terminal});del running[pid]
                    s=read(d/'summary.json') if (d/'summary.json').exists() else {}
                    if rc!=0 or not s or s.get('status') in ['error','invalid']:failures.append({'id':j['id'],'exit_code':rc,'status':s.get('status','missing_summary')})
                    print('F completed',j['id'],'exit',rc,'formal',s.get('formal_count'),'done',len(finished),flush=True)
                    if queues[j['cpu']] and not failures:
                        nextjob=queues[j['cpu']].popleft();nextgate=qdir/(nextjob['id']+'.release.json');nr=spawn(nextjob,nextgate);await_ready([nr]);start=time.monotonic();exclusive(nextgate,{'monotonic':start,'cpu':j['cpu'],'previous':j['id']});nr['start']=start;running[nr['process'].pid]=nr;dispatch.write(json.dumps({'id':nextjob['id'],'cpu':j['cpu'],'released':start,'previous':j['id']})+'\n');dispatch.flush()
                    continue
                if now-r['start']>915:
                    try:os.killpg(pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                try:
                    stat=pathlib.Path(f'/proc/{pid}/stat').read_text().split();live.append({'id':r['job']['id'],'pid':pid,'cpu_slot':r['job']['cpu'],'processor':int(stat[38]),'user_ticks':int(stat[13]),'system_ticks':int(stat[14])})
                except FileNotFoundError:pass
            monitor.write(json.dumps({'monotonic':now,'live':live})+'\n');monitor.flush();time.sleep(.5)
    if failures:
        exclusive(BASE/'F_EARLY_STOP.json',{'executed_attempts':len(finished),'failures':failures,'unstarted':[j['id'] for q in queues.values() for j in q],'no_retry':True});raise RuntimeError('Formal failure; no further attempts')
    assert len(finished)==32 and not any(queues.values());exclusive(BASE/'F_FINISHED.json',{'attempts':32,'results':finished,'no_retries':True});print('F completed32 once only',flush=True)
if __name__=='__main__':main()
