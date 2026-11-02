from common6 import *
import argparse,signal
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--attempt',required=True);a=p.parse_args();v=a.variant
out=BASE/'correctness'/f'guard_{v}_{a.attempt}';out.mkdir(exist_ok=False);tree=ROOT/f'worktrees/round6_{v}';exe=ROOT/f'build/round6-ccss-replay-{v}';env=os.environ.copy()
if v=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
flags=['-std=c++20','-O1','-g']+(['-fsanitize=address,undefined','-fno-omit-frame-pointer'] if v=='sanitize' else [])
def run(cmd,d,ee=env,timeout=90):
    d.mkdir(exist_ok=False);exclusive(d/'attempt.json',{'command':list(map(str,cmd)),'synthetic_only':True});t=time.monotonic();r=subprocess.run(list(map(str,cmd)),cwd=d,env=ee,capture_output=True,text=True,timeout=timeout);(d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr);write(d/'terminal.json',{'exit_code':r.returncode,'wall':time.monotonic()-t});assert r.returncode==0,(d,r.stderr[-3000:]);assert 'runtime error:' not in r.stderr and 'ERROR: AddressSanitizer' not in r.stderr
unit=ROOT/f'build/round6-guard-unit-{v}'
run(['g++',*flags,'-I'+str(ROOT/'include/round6'),ROOT/'tests/round6/stagnation_guard.cpp','-o',unit],out/'unit_compile');run([unit],out/'unit')
native=ROOT/f'build/round6-native-initialize-{v}';archives=sorted((tree/'z3/build').rglob('*.a'));extra=[tree/'z3/build/shell'/f for f in ['mem_initializer.o','gparams_register_modules.o','install_tactic.o']]
run(['g++',*flags,'-I'+str(tree/'z3/src'),'-I'+str(tree/'z3/build'),ROOT/'tests/round6/native_initialization.cpp',*extra,'-Wl,--start-group',*archives,'-Wl,--end-group','-pthread','-ldl','-o',native],out/'native_compile',timeout=300);run([native],out/'native_initialization')
host=tree/'HighDiv/highdiv';dirs={}
for name,fixture in [('yield','diophantine_stagnation.smt2'),('fast','guard_stall.smt2')]:
    d=out/name;ee=env.copy();ee.update(GUIDED_R6_TRACE_DIR=str(d),GUIDED_CCSS_STAGNATION_GUARD='1',GUIDED_R5_EXCHANGE_DIR=str(d),GUIDED_SEMANTIC_TRACE_DIR=str(d),HIGHDIV_TEST_MAX_QUERIES='6');cmd=[host,'-i',ROOT/'tests/round6'/fixture,'-o',d,'-n','8','-t','10','-s','0','--guidance','S_ref'];run(cmd,d,ee);dirs[name]=d
q=rows(dirs['yield']/'queries.jsonl');calls=rows(dirs['yield']/'ccss_guard.jsonl');assert len(calls)==3
for r in calls:assert r['exit_reason']=='ccss_stagnation_yield' and not r['model_produced'] and r['exit_step_exact']-r['last_improvement_step']==65536 and r['last_global_best']>0
assert q[2]['source']=='CDCL' and q[2]['result']=='sat';assert not rows(dirs['yield']/'reference_sources.jsonl');assert all(r['reference_count']==0 for r in rows(dirs['yield']/'query_inputs.jsonl'))
assert all(r['source']=='CDCL' for r in rows(dirs['yield']/'sample_receipts.jsonl') if r.get('kind')=='prepare')
assert all(r['exit_reason']=='sat' and r['last_global_best']==0 for r in rows(dirs['fast']/'ccss_guard.jsonl'))
recipe=read(dirs['yield']/'ccss_1_recipe.json');map_=recipe['exchange']['map'];recipe['cutoff_seconds']=0;write(out/'cutoff_recipe.json',recipe);write(out/'map.json',map_);ee=env.copy();ee['GUIDED_CCSS_STAGNATION_GUARD']='1'
run([exe,out/'cutoff_recipe.json',out/'map.json',out/'cutoff','cutoff','0'],out/'cutoff',ee);rcall=rows(out/'cutoff/ccss_guard.jsonl')[-1];assert rcall['exit_reason']=='native_cutoff' and rcall['exit_step_exact']==1000 and not rcall['model_produced']
# Explicit arithmetic-domain exception, in a synthetic construction only.
bad={**recipe,'make_lits_space':3,'build_lits':['0 true','1 ( >= x 170141183460469231731687303715884105728 )','2 ( <= x 170141183460469231731687303715884105730 )'],'clause_vec':[[1],[2]],'literal_identity':[],'cutoff_seconds':2};write(out/'domain_recipe.json',bad)
d=out/'arith';d.mkdir();cmd=[str(exe),str(out/'domain_recipe.json'),str(out/'map.json'),str(d),'arith','0'];exclusive(d/'attempt.json',{'command':cmd,'synthetic_only':True});r=subprocess.run(cmd,cwd=d,env=ee,capture_output=True,text=True,timeout=30);(d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr);write(d/'terminal.json',{'exit_code':r.returncode});ar=rows(d/'ccss_guard.jsonl')[-1];assert ar['exit_reason']=='arith_unknown' and not ar['model_produced']
# Cancellation is delivered only after the native initialization snapshot exists.
d=out/'cancel';d.mkdir();ee=env.copy();ee.update(GUIDED_R6_TRACE_DIR=str(d),GUIDED_CCSS_STAGNATION_GUARD='0',GUIDED_R5_EXCHANGE_DIR=str(d),GUIDED_SEMANTIC_TRACE_DIR=str(d),HIGHDIV_TEST_MAX_QUERIES='6');cmd=[str(host),'-i',str(ROOT/'tests/round6/diophantine_stagnation.smt2'),'-o',str(d),'-n','8','-t','3','-s','0','--guidance','S_ref'];exclusive(d/'attempt.json',{'command':cmd,'signal_after':'ccss_1_R3.json','synthetic_only':True})
with (d/'stdout.log').open('x') as stdout,(d/'stderr.log').open('x') as stderr:
    proc=subprocess.Popen(cmd,cwd=d,env=ee,stdout=stdout,stderr=stderr);t=time.monotonic()
    while not (d/'ccss_1_R3.json').exists() and proc.poll() is None:
        assert time.monotonic()-t<10,'synthetic initialization not reached';time.sleep(.005)
    proc.send_signal(signal.SIGTERM);rc=proc.wait(timeout=10)
write(d/'terminal.json',{'exit_code':rc,'signal_sent':int(signal.SIGTERM)});assert rc==0;hc=rows(d/'ccss_guard_host.jsonl');assert any(x['host_cancelled'] and x['exit_reason']=='host_cancelled' for x in hc)
for mode in ['yield','fast']:
    for i,r in enumerate(rows(dirs[mode]/'ccss_guard.jsonl'),1):
        if i<=2:
            rec=read(dirs[mode]/f'ccss_{i}_recipe.json');assert r['map_sha256']==sha_text(json.dumps(rec['exchange']['map'],sort_keys=True,separators=(',',':'),ensure_ascii=False))
        assert r['consumed_map_sha256']==sha_text(json.dumps(r['consumed_map'],sort_keys=True,separators=(',',':'),ensure_ascii=False))
checks=['strict_global_best_fixed_limit','same/worse_restart_preserves_history','native_initialize_strict_improvement_hook','zero_unsat_wins','disabled_guard','call_reset','SHA256_vectors_and_real_map_encoding','native_stagnation_unknown_exact_step','host_continues_CDCL_after_yield','no_ccss_model_or_m_ls_update_on_yield','native_cutoff_precedes_guard','arithmetic_exception_distinguished','host_cancellation_distinguished','fast_native_success_preserved']
write(out/'summary.json',{'passed':True,'checks':checks,'host_sha256':digest(host),'replay_sha256':digest(exe),'library_sha256':digest(ROOT/f'deps/round6_{v}/lib/libz3.so'),'real_benchmark_executions':0,'old_binary_executions':0});print('Round6 guard checks passed',v,len(checks))
