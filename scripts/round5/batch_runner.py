from common5 import *
import threading,signal
def run_batch(jobs,out,timeout):
    out.mkdir(parents=True,exist_ok=False);gate=out/'RELEASE.json';processes=[];threads=[];errors=[]
    def wait(p,j):
        try:
            _,status,usage=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status)
            write(pathlib.Path(j['directory'])/'terminal.json',{'exit_code':p.returncode,'user_cpu':usage.ru_utime,'system_cpu':usage.ru_stime,'max_rss_kb':usage.ru_maxrss,'wall_from_batch_release':time.monotonic()-release[0],'completed_monotonic':time.monotonic(),'no_retry':True})
        except Exception as e:errors.append(str(e))
    for job in jobs:
        d=pathlib.Path(job['directory']);d.mkdir(parents=True,exist_ok=False);ready=out/(job['id']+'.ready.json');spec={**job,'ready':str(ready),'gate':str(gate),'cwd':str(d)};exclusive(d/'attempt.json',{k:v for k,v in job.items() if k!='environment'});write(out/(job['id']+'.worker.json'),spec)
        stdout=(d/'stdout.log').open('x');stderr=(d/'stderr.log').open('x');p=subprocess.Popen([sys.executable,ROOT/'scripts/round5/batch_worker.py',out/(job['id']+'.worker.json')],stdout=stdout,stderr=stderr,start_new_session=True);stdout.close();stderr.close();processes.append((p,job))
    t=time.monotonic()
    while not all((out/(j['id']+'.ready.json')).exists() for p,j in processes):
        if time.monotonic()-t>30:raise RuntimeError('worker readiness failed; retain attempts and do not relaunch')
        time.sleep(.05)
    release=[time.monotonic()];exclusive(gate,{'monotonic':release[0],'count':len(jobs),'cpu_slots':[j['cpu'] for j in jobs]})
    for p,j in processes:
        th=threading.Thread(target=wait,args=(p,j));th.start();threads.append(th)
    with (out/'concurrency.jsonl').open('x') as monitor:
        while any(th.is_alive() for th in threads):
            now=time.monotonic();live=[]
            for (p,j),th in zip(processes,threads):
                if not th.is_alive():continue
                try:
                    stat=pathlib.Path(f'/proc/{p.pid}/stat').read_text().split();live.append({'id':j['id'],'pid':p.pid,'processor':int(stat[38]),'user_ticks':int(stat[13]),'system_ticks':int(stat[14]),'state':stat[2]})
                except FileNotFoundError:pass
                if now-release[0]>timeout:
                    try:os.killpg(p.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
            monitor.write(json.dumps({'elapsed':now-release[0],'live':live})+'\n');monitor.flush();time.sleep(.25)
    for th in threads:th.join()
    assert not errors,errors
    # Environment is deliberately whitelisted by callers; no credentials saved.
    return [read(pathlib.Path(j['directory'])/'terminal.json') for j in jobs]
