"""Predeclared synthetic checks; unique attempts, never benchmarks or frozen binaries."""
from common6 import *
from finalize_samples import finalize
import argparse,concurrent.futures
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--attempt',required=True);p.add_argument('--reuse-binaries',action='store_true');a=p.parse_args();variant=a.variant
tree=ROOT/f'worktrees/round6_{variant}';prefix=ROOT/f'deps/round6_{variant}';out=BASE/'correctness'/(variant+'_'+a.attempt);out.mkdir(exist_ok=False);env=os.environ.copy()
env.update(GUIDED_R5_DECISION_AUDIT='1',HIGHDIV_TEST_MAX_QUERIES='20')
if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
def run(cmd,name,ee=None,timeout=300):
    t=time.monotonic();r=subprocess.run(list(map(str,cmd)),cwd=out,env=ee or env,capture_output=True,text=True,timeout=timeout)
    (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr);write(out/(name+'.command.json'),{'command':list(map(str,cmd)),'exit_code':r.returncode,'seconds':time.monotonic()-t})
    assert r.returncode==0,(name,r.stderr[-3000:]);assert 'runtime error:' not in r.stderr and 'ERROR: AddressSanitizer' not in r.stderr;return r.stdout
sources={n:ROOT/f'tests/round2/{n}.cpp' for n in ['canonical','kernel','abandon','parallel','index_outcome','exposure','budgets','demands']}
sources.update(semantic_cases=ROOT/'tests/round3/semantic_cases.cpp',semantic_correspondence=ROOT/'tests/round4/test_semantic_correspondence.cpp',soft_reference=ROOT/'tests/round4/test_soft_reference.cpp',soft_lifecycle=ROOT/'tests/round4/test_soft_lifecycle.cpp',coverage_policy=ROOT/'tests/round5/coverage_policy.cpp')
def compile(item):
    name,source=item;binary=ROOT/f'build/round6-{name}-{variant}';cmd=['g++','-std=c++20','-O1' if variant=='sanitize' else '-O3','-g','-I'+str(tree/'round6_include'),'-I'+str(ROOT/'include/round4'),'-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),source,'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',binary]
    if variant=='sanitize':cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    if a.reuse_binaries:assert binary.exists();write(out/(name+'-compile-reused.json'),{'binary_sha256':digest(binary),'reason':'same public headers and test source; refreshed native trace implementation only'})
    else:run(cmd,name+'-compile')
    return name,binary
checks={}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:binaries=list(pool.map(compile,sources.items()))
for name,binary in binaries:
    d=out/(name+'-data');d.mkdir();ee=env.copy();ee.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=name)
    run([binary,d],name,ee);checks[name]=True
run([python(),ROOT/'tests/round3/test_reach.py'],'official_reach');checks['official_high_bit_signed_short_circuit']=True
host=tree/'HighDiv/highdiv';formula=ROOT/'results/correctness/release/host.smt2'
hostdirs={}
for mode in ['a_off_test','S_ref','S_full','S_support']:
    for trace in [False,True]:
        name=mode+('_on' if trace else '_off');d=out/name;d.mkdir();ee=env.copy();ee.update(HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(d/'rng.txt'),HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'))
        if trace:ee.update(GUIDED_R6_TRACE_DIR=str(d),GUIDED_CCSS_STAGNATION_GUARD='0',GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=name,GUIDED_R5_EXCHANGE_DIR=str(d))
        else:ee.pop('GUIDED_R5_DECISION_AUDIT',None)
        run([host,'-i',formula,'-o',d,'-n','8','-t','60','-s','0','--guidance',mode],name,ee,90);finalize(d,60,8);hostdirs[name]=d
    off,on=hostdirs[mode+'_off'],hostdirs[mode+'_on']
    for f in ['samples.formal','native_decisions.txt','rng.txt']:
        assert (off/f).exists()==(on/f).exists()
        if (off/f).exists():assert (off/f).read_bytes()==(on/f).read_bytes(),(mode,f)
    checks[mode+'_instrumentation_behavior']=True
    previous=ROOT/'results/round4/correctness'/f'soft_host_{variant}'/('S_cov' if mode=='S_full' else mode)
    if mode in ['S_ref','S_full']:
        for f in ['samples.formal','native_decisions.txt','rng.txt']:assert (off/f).read_bytes()==(previous/f).read_bytes(),('saved_R4',mode,f)
        checks[mode+'_saved_R4_regression']=True
    for q in rows(on/'queries.jsonl'):
        g=q['guidance']
        if g:
            assert all(g[k]==0 for k in ['b_encoded','b_internalized','b_selected','guidance_added_assertions','guidance_created_bool_vars','guidance_marked_relevant']);assert g['suggestions']<=4
            assert all(ac['decision_id']<=64 and ac['native_var']==ac['actual_var'] for ac in g['actions'])
            if mode=='S_support':assert all(ac['preference_source']!='avoid_direct_blocker' for ac in g['actions'])
checks['hard_soft_provenance_and_zero_new_guidance_constraints']=True
# X1 synthetic recipe diagonal and raw-map round trips, no search loop.
replay=ROOT/f'build/round6-ccss-replay-{variant}'
run([replay,'--self-test'],'exchange_numeric_and_buffer_tests');checks['exchange_numeric_RNG_and_buffer_tests']=True
for mode in ['S_ref','S_full','S_support']:
    d=hostdirs[mode+'_on'];recipe=read(d/'ccss_2_recipe.json');map_path=d/'map.json';write(map_path,recipe['exchange']['map']);rd=out/('rebuild_'+mode);rd.mkdir();ee=env.copy()
    run([replay,d/'ccss_2_recipe.json',map_path,rd,'diagonal','1'],'rebuild_'+mode,ee)
    for boundary in ['R1','R2','R3']:assert read(d/f'ccss_2_{boundary}.json')==read(rd/f'diagonal_{boundary}.json'),(mode,boundary)
    assert read(d/'ccss_2_intervals.json')==read(rd/'diagonal_intervals.json')
    checks[mode+'_native_recipe_RNG_rebuild']=True
    od=out/('probe_off_'+mode);od.mkdir();run([replay,d/'ccss_2_recipe.json',map_path,od,'off','off'],'probe_off_'+mode,ee)
    for boundary in ['R2','R3']:assert read(d/f'ccss_2_{boundary}.json')==read(od/f'off_{boundary}.json'),('probe_disabled',mode,boundary)
    checks[mode+'_probe_off_initialization_RNG']=True
bad=out/'truncated_recipe.json';bad.write_text('{"seed":');badout=out/'truncated_test';badout.mkdir()
r=subprocess.run([replay,bad,hostdirs['S_full_on']/'map.json',badout,'bad','1'],env=env,capture_output=True,text=True)
write(out/'truncated_input_test.json',{'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==2 and read(badout/'bad_input_failure.json')['status']=='malformed_or_truncated_input';checks['truncated_recipe_explicit_error']=True
write(out/'summary.json',{'passed':True,'checks':checks,'binary_sha256':digest(host),'library_sha256':digest(prefix/'lib/libz3.so'),'replay_sha256':digest(replay),'real_benchmark_runs':0,'old_binary_executions':0,'sole_leak_suppression':digest(ROOT/'tests/lsan-upstream.supp') if variant=='sanitize' else None})
print('Round6 inherited synthetic correctness passed',variant,len(checks),flush=True)
