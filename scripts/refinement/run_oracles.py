from common_r import *
import resource
assert (MAN/'implementation.json').exists();assert (BASE/'offline/frozen_v1/FINISHED.json').exists();out=attempt('oracle','frozen_v1');cfg=read(ROOT/'configs/refinement.json');jobs=[(n,p) for n in cfg['offline_inputs'] for p in cfg['oracle_positions']];exclusive(out/'STARTED.json',{'jobs':jobs,'max_checks':12,'per_case_total_wall':3,'per_check_wall':2,'no_retry':True,'cold_start':True})
for name,pos in jobs:
    d=out/f'{name}_{pos:02}';d.mkdir();data=BASE/'offline/inputs_v1'/f'{name}.json';cmd=[python(),ROOT/'scripts/refinement/oracle_worker.py',data,str(pos),d/'result.json'];started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    with open(d/'stdout.log','w') as f,open(d/'stderr.log','w') as e:
        proc=subprocess.Popen(list(map(str,cmd)),stdout=f,stderr=e)
        timedout=False
        try:code=proc.wait(timeout=3)
        except subprocess.TimeoutExpired:timedout=True;proc.kill();code=proc.wait()
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    if (d/'result.json.checkpoint').exists() and not (d/'result.json').exists():
        checkpoint=read(d/'result.json.checkpoint');checkpoint.update(status='oracle_case_external_timeout',answer_censored=True);write(d/'result.json',checkpoint)
    if not (d/'result.json').exists():write(d/'result.json',{'status':'oracle_case_external_timeout' if timedout else 'failed','checks':None,'reason':'child did not finish a full result; unknown check state, no inference of UNSAT','returncode':code})
    write(d/'execution.json',{'command':list(map(str,cmd)),'wall':time.monotonic()-started,'cpu':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'external_timeout':timedout,'returncode':code,'no_retry':True,'result_sha256':digest(d/'result.json')});print(name,pos,read(d/'result.json')['status'],flush=True)
write(out/'FINISHED.json',{'cases':len(jobs),'max_checks':12,'no_retry':True})
