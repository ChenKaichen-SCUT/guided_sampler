# One cold process, at most one solver.check, never a model supplier.
import time,signal,sys,json,pathlib
START=time.monotonic();CPU=time.process_time();deadline=START+3
class CaseTimeout(Exception):pass
class EncodingTimeout(Exception):pass
def alarm(*args):raise CaseTimeout()
signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,3)
result={'checks':0,'status':'unstarted','cold_solver':True}
try:
    from oracle_encoder import *
    from independent import export,observations,covered
    data=json.loads(pathlib.Path(sys.argv[1]).read_text());pos=int(sys.argv[2]);result.update(position=pos,z3_version=z3.get_full_version(),input_sha256=data['ast']['input_sha'],input=data['input'])
    root=z3.And(z3.parse_smt2_file(data['input']));problem,meta=improvement_problem(root,data['models'],pos,deadline);result.update(meta)
    result['encoding_wall']=time.monotonic()-START;result['encoding_cpu']=time.process_time()-CPU
    if problem is not None:
        solver=z3.Solver();solver.add(problem);pathlib.Path(sys.argv[3]+'.smt2').write_text(solver.to_smt2());remaining=deadline-time.monotonic();solver.set(timeout=max(1,int(min(2,remaining)*1000)))
        if remaining<=0:raise CaseTimeout()
        sw=time.monotonic();sc=time.process_time();result['checks']=1;result['status']='check_started';pathlib.Path(sys.argv[3]+'.checkpoint').write_text(json.dumps(result));answer=solver.check();result.update(status=str(answer),check_wall=time.monotonic()-sw,check_cpu=time.process_time()-sc)
        if answer==z3.unknown:result['reason_unknown']=solver.reason_unknown()
        if answer==z3.sat:
            a,ns,vs=export(root);model=solver.model();assignment=[str(model.eval(v,model_completion=True).as_long()) if z3.is_int(v) else str(int(z3.is_true(model.eval(v,model_completion=True)))) for v in vs]
            history=set()
            for m in data['models'][:pos-1]:history|=observations(a,m)[1]
            native=observations(a,data['models'][pos-1])[1];legal,seen=observations(a,assignment);assert legal and native-history<=seen and covered(history|seen)>covered(history|native)
            result.update(assignment=assignment,independent_validation=True,covered_extra=covered(history|seen)-covered(history|native))
except (CaseTimeout,EncodingTimeout):result['status']='oracle_encoding_timeout' if result['checks']==0 else 'oracle_case_timeout'
except NotImplementedError as e:result.update(status='oracle_encoding_unsupported',error=str(e))
except BaseException as e:result.update(status='failed',error=repr(e))
finally:
    signal.setitimer(signal.ITIMER_REAL,0);result.update(total_wall=time.monotonic()-START,total_cpu=time.process_time()-CPU);pathlib.Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
