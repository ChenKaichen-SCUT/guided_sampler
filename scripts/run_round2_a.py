#!/usr/bin/env python3
"""Exactly-once second-round A-only matrix. Never launches a baseline binary."""
import csv,datetime,signal,time,subprocess
from common import *

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def process_info(pid):
    try:
        fields=pathlib.Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
        status=pathlib.Path(f'/proc/{pid}/status').read_text().splitlines();data={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in status if ':' in x}
        ticks=os.sysconf('SC_CLK_TCK')
        return {'cpu_seconds':(int(fields[11])+int(fields[12]))/ticks,'processor':int(fields[36]),'rss_kib':int(data.get('VmRSS','0 kB').split()[0]),'peak_rss_kib':int(data.get('VmHWM','0 kB').split()[0]),'allowed_cpus':data.get('Cpus_allowed_list')}
    except (OSError,ValueError,IndexError):return {}

def main():
    for key in ['HIGHDIV_TEST_MAX_QUERIES','HIGHDIV_NATIVE_DECISION_TRACE','GUIDED_A_DIAGNOSTIC']:os.environ.pop(key,None)
    plan=read(ROOT/'manifests/round2_a_plan.json');assert len(plan['runs'])==16 and len(plan['workers'])==16
    for variant in ['release','sanitize']:
        for k in ['binary','library']:
            x=plan['artifacts'][variant][k];assert digest(ROOT/x['path'])==x['sha256']
    for run in plan['runs']:assert run['config']=='a_only_v2' and run['command'][0]==plan['artifacts']['release']['binary']['path']
    for path,h in plan['source_hashes'].items():assert digest(ROOT/path)==h
    for run in plan['runs']:assert digest(ROOT/run['input'])==run['input_sha256']
    root=ROOT/'results/round2_a';exclusive(root/'QUEUE_STARTED.json',{'time':utc(),'plan_sha256':digest(ROOT/'manifests/round2_a_plan.json')})
    for run in plan['runs']:assert not (ROOT/run['output']).exists(),f"Existing run: {run['id']}"
    runlog=open(root/'dispatch.jsonl','x');concurrent=open(root/'concurrency.jsonl','x');active={};next_index=0;finished=[];blocking_failure=None
    rfd,wfd=os.pipe()
    def launch(run,cpu,barrier):
        nonlocal next_index
        path=ROOT/run['output'];path.mkdir(parents=True)
        exclusive(path/'attempt.json',{'id':run['id'],'time':utc(),'cpu':cpu,'plan_order':run['order']})
        write(path/'config.json',run)
        cmd=[str(ROOT/run['command'][0])]+[str(ROOT/x) if x==run['input'] or x==run['output'] else x for x in run['command'][1:]]
        (path/'command.txt').write_text(shlex_join(cmd)+'\n')
        out=open(path/'stdout.log','xb');err=open(path/'stderr.log','xb')
        wrapper=[sys.executable,str(ROOT/'scripts/launch_worker.py'),str(cpu),str(rfd if barrier else -1)]+cmd
        runenv=os.environ.copy();runenv['HIGHDIV_ROUTE_LOG']=str(path/'routes.jsonl')
        proc=subprocess.Popen(wrapper,cwd=ROOT,env=runenv,stdout=out,stderr=err,pass_fds=(rfd,) if barrier else (),start_new_session=True)
        resource=open(path/'resource.csv','x');writer=csv.DictWriter(resource,fieldnames=['elapsed','pid','cpu','cpu_seconds','processor','rss_kib','peak_rss_kib','allowed_cpus']);writer.writeheader()
        active[cpu]={'run':run,'path':path,'proc':proc,'out':out,'err':err,'resource':resource,'writer':writer,'start':time.monotonic(),'last':{},'terminate':False,'kill':False,'maps':False}
        next_index+=1;event={'event':'launch','id':run['id'],'pid':proc.pid,'cpu':cpu,'utc':utc(),'barrier':barrier};runlog.write(json.dumps(event)+'\n');runlog.flush()
    for run in plan['runs'][:16]:launch(run,run['preferred_cpu'],True)
    start=time.monotonic();os.write(wfd,b'1'*16);os.close(wfd);os.close(rfd)
    for state in active.values():state['start']=start
    last_resource=0
    while active:
        now=time.monotonic();freed=[]
        for cpu,state in sorted(active.items()):
            p=state['proc'];elapsed=now-state['start']
            waited,status,usage=os.wait4(p.pid,os.WNOHANG)
            rc=os.waitstatus_to_exitcode(status) if waited else None
            if waited:p.returncode=rc
            if rc is None:
                if elapsed>901 and not state['terminate']:os.killpg(p.pid,signal.SIGTERM);state['terminate']=True
                if elapsed>965 and not state['kill']:os.killpg(p.pid,signal.SIGKILL);state['kill']=True
                if not state['maps']:
                    try:
                        maps=pathlib.Path(f'/proc/{p.pid}/maps').read_text();liblines=[l for l in maps.splitlines() if 'libz3.so' in l]
                        if liblines:(state['path']/'loaded_library.txt').write_text('\n'.join(liblines)+'\n');state['maps']=True
                    except OSError:pass
                if now-last_resource>=1:
                    info=process_info(p.pid);state['last']=info
                    state['writer'].writerow({'elapsed':elapsed,'pid':p.pid,'cpu':cpu,**info});state['resource'].flush()
                continue
            terminal={'exit_code':rc,'process_wall_seconds':elapsed,'cpu':cpu,'pid':p.pid,'terminated':state['terminate'],'hard_killed':state['kill'],'resource_last':state['last'],'finished_utc':utc(),'cpu_seconds_exact':usage.ru_utime+usage.ru_stime,'peak_rss_kib_exact':usage.ru_maxrss}
            exclusive(state['path']/'terminal.json',terminal)
            if rc not in (0,-15,-9) and blocking_failure is None:
                blocking_failure={'id':state['run']['id'],'exit_code':rc,'reason':'unexpected_error_requires_correctness_review'}
                exclusive(root/'CORRECTNESS_BLOCKED.json',blocking_failure)
                for other in active.values():
                    if other is not state and not other['terminate']:
                        try:os.killpg(other['proc'].pid,signal.SIGTERM);other['terminate']=True
                        except ProcessLookupError:pass
            for key in ['out','err','resource']:state[key].close()
            runlog.write(json.dumps({'event':'finish','id':state['run']['id'],**terminal})+'\n');runlog.flush()
            finished.append(state['run']['id']);freed.append(cpu)
            print(f"{len(finished):02}/16 finished {state['run']['id']} rc={rc} elapsed={elapsed:.1f}s",flush=True)
        for cpu in freed:del active[cpu]
        for cpu in sorted(freed):
            if not blocking_failure and next_index<len(plan['runs']):launch(plan['runs'][next_index],cpu,False)
        if now-last_resource>=1:
            concurrent.write(json.dumps({'elapsed':now-start,'utc':utc(),'active':[{'id':s['run']['id'],'cpu':cpu,'pid':s['proc'].pid} for cpu,s in sorted(active.items())]})+'\n');concurrent.flush();last_resource=now
        time.sleep(0.2)
    if blocking_failure:
        for run in plan['runs'][next_index:]:
            path=ROOT/run['output'];path.mkdir(parents=True);write(path/'config.json',run)
            exclusive(path/'not_started.json',blocking_failure)
            exclusive(path/'terminal.json',{'exit_code':None,'status':'not_started_correctness_blocker','reason':blocking_failure})
    from freeze_round2_a_plan import historical_fingerprint
    after=historical_fingerprint();assert after==plan['baseline_before'];exclusive(root/'BASELINE_UNCHANGED.json',{'baseline_executions':0,'unchanged':True,'before':plan['baseline_before'],'after':after})
    runlog.close();concurrent.close();exclusive(root/'QUEUE_FINISHED.json',{'runs':len(finished),'ids':finished,'utc':utc(),'wall':time.monotonic()-start})
def shlex_join(cmd):
    import shlex;return shlex.join(cmd)
if __name__=='__main__':main()
