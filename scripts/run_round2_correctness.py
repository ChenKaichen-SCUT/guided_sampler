#!/usr/bin/env python3
import argparse,os,subprocess,time
from common import *
from finalize_samples import finalize
from evaluate_official import evaluate
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--attempt',default='01');a=p.parse_args()
variant='round2_'+a.variant;prefix=ROOT/'deps'/variant;out=ROOT/f'results/round2_a/correctness/{a.variant}_{a.attempt}';out.mkdir(parents=True,exist_ok=False)
env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='20'
if a.variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
def run(cmd,name,runenv=None,timeout=180):
 r=subprocess.run(list(map(str,cmd)),cwd=out,capture_output=True,text=True,env=runenv or env,timeout=timeout);(out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
 trace=out/'.z3-trace'
 if trace.exists():trace.rename(out/(name+'.z3-trace'))
 write(out/(name+'.command.json'),{'command':list(map(str,cmd)),'exit_code':r.returncode});assert r.returncode==0,(name,r.stderr[-2500:]);assert 'runtime error:' not in r.stderr and 'ERROR: AddressSanitizer' not in r.stderr
 return r.stdout
def compile(name,source=None):
 binary=ROOT/'build'/f'round2-{name}-{a.variant}'
 cmd=['g++','-std=c++20','-O1' if a.variant=='sanitize' else '-O3','-g','-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(source or ROOT/f'tests/round2/{name}.cpp'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(binary)]
 if a.variant=='sanitize':cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 run(cmd,name+'-compile',timeout=300);return binary
checks={}
for name in ('canonical','kernel','abandon','parallel','index_outcome','exposure'):
 binary=compile(name);run([binary,out/(name+'-data')],name);checks[name]=True
for name in ('deep_observer','session'):
 binary=compile(name,ROOT/f'tests/{name}.cpp');run([binary,out/(name+'-data')],name);checks[name]=True
run([sys.executable,ROOT/'tests/test_finalization.py'],'finalization');checks['finalization']=True
observer=compile('observer');source=ROOT/'results/correctness/release';formula=source/'observer.smt2';models=source/'observer.models.json'
result=run([observer,formula,models],'observer');(out/'observer.json').write_text(result)
run([python(),ROOT/'tests/compare_observer.py',formula,models,out/'observer.json'],'observer-differential');checks['observer_differential']=True
# Replay ONLY new-library finite controls; compare to saved first-round native baseline.
host=ROOT/f'worktrees/{variant}/HighDiv/highdiv';synth=source/'host.smt2'
fixture=source/'baseline-off' if a.variant=='release' else ROOT/'results/correctness/sanitize/sanitize-off'
for mode in ['a_off_test','a_observe_test','a_apply_test']:
 d=out/mode;d.mkdir();ee=env.copy();ee['HIGHDIV_ROUTE_LOG']=str(d/'routes.jsonl');ee['HIGHDIV_NATIVE_DECISION_TRACE']=str(d/'native_decisions.txt')
 run([host,'-i',synth,'-o',d,'-n','8','-t','15','-s','0','--guidance',mode],mode,ee,90);finalize(d,15,8)
 metrics=evaluate(d,synth);assert metrics=={'official_exit':0,'exact_exit':0};assert read(d/'summary.json')['formal_count']>0
 if mode=='a_off_test':
  assert (d/'samples.formal').read_bytes()==(fixture/'samples.formal').read_bytes(),'off model trajectory differs from saved native baseline'
  assert (d/'native_decisions.txt').read_bytes()==(fixture/'native_decisions.txt').read_bytes(),'off native decisions differ'
 if mode=='a_observe_test':
  off=out/'a_off_test';assert (d/'samples.formal').read_bytes()==(off/'samples.formal').read_bytes(),'observe models changed'
  assert (d/'native_decisions.txt').read_bytes()==(off/'native_decisions.txt').read_bytes(),'observe decisions changed'
  def trajectory(path):return [(r['source'],r['assumptions'],r['result'],r.get('highdiv_ls_seed')) for r in map(__import__('json').loads,(path/'queries.jsonl').read_text().splitlines())]
  assert trajectory(d)==trajectory(off),'observe solver calls / original RNG stream changed'
checks['off_vs_saved_native_and_observe']=True
# Real unchanged CCSS regression suite, linked to this round's own dependency.
tree=(ROOT/f'worktrees/{variant}').resolve()
if not (tree/'venv').exists():(tree/'venv').symlink_to(prefix,target_is_directory=True)
ue=env.copy()
if a.variant=='sanitize':ue['CXX']='g++ -fsanitize=address,undefined -fno-omit-frame-pointer'
run([sys.executable,'-m','unittest','discover','-s',tree/'tests','-p','test_partitioned_initialization.py','-v'],'upstream-ccss',ue,300);checks['upstream_ccss']=True
write(out/'summary.json',{'passed':True,'checks':checks,'binary_sha256':digest(host),'library_sha256':digest(prefix/'lib/libz3.so'),'baseline_executions':0,'comparison_to_saved_round1_fixture':True,'known_upstream_leak_exception':'tests/lsan-upstream.supp' if a.variant=='sanitize' else None})
print('Passed round2 correctness:',a.variant)
