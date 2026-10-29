#!/usr/bin/env python3
import argparse,collections,importlib.util,json,os,pathlib,subprocess,sys,time
from common import *

def compile_test(name,variant,out):
    prefix=ROOT/'deps'/variant;binary=ROOT/'build'/f'{name}-{variant}'
    cmd=['g++','-std=c++20','-O1' if variant=='sanitize' else '-O3','-g','-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(ROOT/'tests'/f'{name}.cpp'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(binary)]
    if variant=='sanitize':cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    p=subprocess.run(cmd,capture_output=True,text=True);(out/f'{name}-compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
    return binary

def run(cmd,out,env=None,timeout=180):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env,timeout=timeout,cwd=out.parent)
    out.with_suffix('.stdout').write_text(p.stdout);out.with_suffix('.stderr').write_text(p.stderr)
    trace=out.parent/'.z3-trace'
    if trace.exists():trace.rename(out.with_suffix('.z3-trace'))
    assert p.returncode==0,f'{cmd}: {p.stderr[-3000:]}'
    assert 'runtime error:' not in p.stderr and 'ERROR: AddressSanitizer' not in p.stderr,p.stderr[-3000:]
    return p.stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);a=p.parse_args();variant='guided' if a.variant=='release' else 'sanitize'
    out=ROOT/'results/correctness'/a.variant;out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='20'
    if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
    kernel=compile_test('kernel',variant,out);observer=compile_test('observer',variant,out)
    kernel_result=json.loads(run([kernel],out/'kernel',env));assert kernel_result['passed']
    deep=compile_test('deep_observer',variant,out);run([deep],out/'deep',env)
    run([sys.executable,ROOT/'tests/test_finalization.py'],out/'finalization')
    sink=compile_test('session',variant,out);run([sink,out/'sink'],out/'sink-test',env)
    # Run independent oracle in frozen baseline Python, even for sanitized C++.
    formula='''(declare-const x Int) (declare-const y Int) (declare-const b Bool)
(assert (and (or (= x 10) (= x 0) (> y -99999999999999999999999))
 (= (+ x y) (+ y x)) (= (ite b (- x) (* x 2)) (ite b (- x) (* x 2)))
 (= (not b) (= x y))))'''
    f=out/'observer.smt2';f.write_text(formula)
    values=[{'x':str(x),'y':str(y),'b':str(b)} for x,y,b in [(10,0,0),(0,-1,1),(-1,-2,0),(-(2**70),2**80+3,1),(2**63,2**64-1,0),(10,10,1)]]
    write(out/'observer.models.json',values)
    cpp=json.loads(run([observer,f,out/'observer.models.json'],out/'observer',env));write(out/'observer.json',cpp)
    oracle_cmd=[python(),ROOT/'tests/compare_observer.py',f,out/'observer.models.json',out/'observer.json']
    run(oracle_cmd,out/'differential')
    # Controlled finite run: both binaries use count termination, same solver
    # calls, assumptions, LS seeds, and original projected samples.
    synth=out/'host.smt2';synth.write_text('(declare-const x Int)(declare-const y Int)(assert (and (or (= x 0) (= x 10) (= x 20)) (or (= y 0) (= y 10) (= y 20))))')
    host_results={}
    variants=['baseline','guided'] if a.variant=='release' else ['sanitize']
    for v in variants:
        for mode in (['off','a_only','b_only','a_plus_b'] if v!='baseline' else ['off']):
            d=out/(v+'-'+mode);d.mkdir();cmd=[ROOT/f'worktrees/{v}/HighDiv/highdiv','-i',synth,'-o',d,'-n','8','-t','15','-s','0','--guidance',mode]
            runenv=env.copy();runenv['HIGHDIV_ROUTE_LOG']=str(d/'routes.jsonl')
            if mode=='off':runenv['HIGHDIV_NATIVE_DECISION_TRACE']=str(d/'native_decisions.txt')
            run(cmd,out/(v+'-'+mode+'-run'),runenv,90)
            summary=read(d/'summary.json');assert summary['formal_count']>0,summary
            from finalize_samples import finalize
            finalize(d,15,8)
            from evaluate_official import evaluate
            check=evaluate(d,synth);assert check=={'official_exit':0,'exact_exit':0},check
            route_rows=[json.loads(l) for l in (d/'routes.jsonl').read_text().splitlines()]
            queries=[json.loads(l) for l in (d/'queries.jsonl').read_text().splitlines() if json.loads(l)['source']=='CDCL']
            assert len({r['solver'] for r in route_rows})==1
            for epoch,q in enumerate(queries,1):
                route=[r['backend'] for r in route_rows if r['check_epoch']==epoch];assert route
                if q['guidance']:assert q['guidance']['backend']=={'smt':2,'tactic':1}[route[-1]]
            host_results[v+'-'+mode]=summary
    if a.variant=='release':
        base=out/'baseline-off';off=out/'guided-off'
        assert (base/'samples.formal').read_bytes()==(off/'samples.formal').read_bytes(),'Off model trajectory changed'
        def trajectory(d):return [(r['source'],r['assumptions'],r['result'],r.get('highdiv_ls_seed')) for r in map(json.loads,(d/'queries.jsonl').read_text().splitlines())]
        assert trajectory(base)==trajectory(off),'Off solver call/assumption trajectory changed'
        assert (base/'native_decisions.txt').read_bytes()==(off/'native_decisions.txt').read_bytes(),'Off native decisions changed'
    write(out/'summary.json',{'passed':True,'variant':a.variant,'kernel':kernel_result,'differential':True,'host':host_results,'library_sha256':digest(ROOT/f'deps/{variant}/lib/libz3.so'),'known_upstream_leak_exception':'tests/lsan-upstream.supp' if variant=='sanitize' else None})
    print('Correctness passed:',a.variant)
if __name__=='__main__':main()
