# Establish the stage log BEFORE importing z3 or the independent evaluator.
import time,sys,json,pathlib,contextlib,signal
START=time.monotonic();CPU=time.process_time();deadline=START+3
out=pathlib.Path(sys.argv[3]);log=open(out/'stages.jsonl','w',buffering=1);last='worker_start'
def emit(stage,state,stats=None):
    global last
    last=stage;log.write(json.dumps({'stage':stage,'state':state,'wall':time.monotonic()-START,'cpu':time.process_time()-CPU,'counts':dict(stats or {})})+'\n');log.flush()
emit('worker_start','completed')
@contextlib.contextmanager
def stage(name,stats=None):
    emit(name,'entered',stats)
    try:yield
    except BaseException:emit(name,'incomplete',stats);raise
    else:emit(name,'completed',stats)
class CaseTimeout(Exception):pass
def alarm(*args):raise CaseTimeout()
signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,max(.000001,deadline-time.monotonic()))
result={'checks':0,'status':'unstarted','cold_solver':True,'mode':sys.argv[4]}
try:
    with stage('imports'):
        sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'refinement'))
        from cost_oracle_encoder import problem,EncodingTimeout
        from independent import observations,covered
        import z3
    with stage('input_read'):
        data=json.loads(pathlib.Path(sys.argv[1]).read_text());pos=int(sys.argv[2]);result.update(position=pos,z3_version=z3.get_full_version(),input_sha256=data['ast']['input_sha'],input=data['input'])
    with stage('parse_formula'):root=z3.And(z3.parse_smt2_file(data['input']))
    formula,meta,context=problem(root,data['models'],pos,deadline,sys.argv[4],stage);result.update(meta)
    if formula is not None:
        with stage('solver_add'):solver=z3.Solver();solver.add(formula)
        with stage('smt2_export'):(out/'problem.smt2').write_text(solver.to_smt2())
        remaining=deadline-time.monotonic()
        if remaining<0.001:raise CaseTimeout()
        solver.set(timeout=max(1,int(min(2,remaining)*1000)))
        emit('check_attempt','entered',{'checks':1});result['checks']=1;result['status']='check_attempt';sw=time.monotonic();sc=time.process_time();answer=solver.check()
        result.update(answer=str(answer),status=str(answer),check_wall=time.monotonic()-sw,check_cpu=time.process_time()-sc);emit('check_return','completed',{'answer':str(answer)})
        if answer==z3.unknown:result['reason_unknown']=solver.reason_unknown()
        if answer==z3.sat:
            with stage('witness_validation'):
                ast,nodes,vs,reach,history,native=context;model=solver.model();assignment=[str(model.eval(v,model_completion=True).as_long()) if z3.is_int(v) else str(int(z3.is_true(model.eval(v,model_completion=True)))) for v in vs]
                legal,seen=observations(ast,assignment);assert legal and native-history<=seen and covered(history|seen)>covered(history|native)
                from independent import evaluate
                _,visited=evaluate(ast,assignment)
                for i,r in enumerate(reach):assert z3.is_true(model.eval(r,model_completion=True))==(i in visited)
                if time.monotonic()>=deadline:raise CaseTimeout()
                result.update(assignment=assignment,independent_validation=True,covered_extra=covered(history|seen)-covered(history|native))
except BaseException as e:
    result.update(last_failed_stage=last,error=repr(e))
    if type(e).__name__ in ('CaseTimeout','EncodingTimeout'):result['status']='case_timeout'
    elif isinstance(e,NotImplementedError):result['status']='unsupported'
    else:result['status']='failed'
finally:
    signal.setitimer(signal.ITIMER_REAL,0);result.update(total_wall_before_result=time.monotonic()-START,total_cpu_before_result=time.process_time()-CPU,last_stage_before_result=last)
    result['validated_within_case']=bool(result.get('independent_validation') and time.monotonic()<=deadline)
    with stage('result_write'):(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    emit('worker_finished','completed',{'within_case':time.monotonic()<=deadline});log.close()
