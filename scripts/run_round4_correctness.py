#!/usr/bin/env python3
from common import *
import argparse,time,concurrent.futures
from finalize_samples import finalize
p=argparse.ArgumentParser();p.add_argument('stage',choices=['M','S']);p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--attempt',default='01');a=p.parse_args();variant='round4_'+a.stage+'_'+a.variant;prefix=ROOT/'deps'/variant;out=ROOT/f'results/round4/correctness/{a.stage}_{a.variant}_{a.attempt}';out.mkdir(parents=True,exist_ok=False)
env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='20'
if a.variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
def run(cmd,name,ee=None,timeout=300):
 start=time.monotonic();r=subprocess.run(list(map(str,cmd)),cwd=out,capture_output=True,text=True,env=ee or env,timeout=timeout);(out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr);trace=out/'.z3-trace';
 if trace.exists():trace.rename(out/(name+'.z3-trace'))
 write(out/(name+'.command.json'),{'command':list(map(str,cmd)),'exit_code':r.returncode,'seconds':time.monotonic()-start});assert r.returncode==0,(name,r.stderr[-3000:]);assert 'runtime error:' not in r.stderr and 'ERROR: AddressSanitizer' not in r.stderr;return r.stdout
checks={}
names=['canonical','kernel','abandon','parallel','index_outcome','exposure','budgets','demands','semantic_cases','semantic_correspondence']
if a.stage=='S':names+=['soft_reference','soft_lifecycle']
def compile_one(name):
 binary=ROOT/'build'/f'round4-{a.stage}-{name}-{a.variant}';source=ROOT/('tests/round4/test_soft_lifecycle.cpp' if name=='soft_lifecycle' else 'tests/round4/test_soft_reference.cpp' if name=='soft_reference' else 'tests/round4/test_semantic_correspondence.cpp' if name=='semantic_correspondence' else 'tests/round3/semantic_cases.cpp' if name=='semantic_cases' else f'tests/round2/{name}.cpp')
 cmd=['g++','-std=c++20','-O1' if a.variant=='sanitize' else '-O3','-g','-I'+str(ROOT/('include/round4/soft_reference' if a.stage=='S' else 'include/round4')),'-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(source),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(binary)]
 if a.variant=='sanitize':cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 run(cmd,name+'-compile');return binary
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:binaries=dict(zip(names,pool.map(compile_one,names)))
for name in names:
 binary=binaries[name];d=out/(name+'-data');d.mkdir();ee=env.copy();ee.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=name)
 run([binary,d],name,ee);checks[name]=True
run([python(),ROOT/'tests/round3/test_reach.py'],'offline-exact-reach',timeout=300);checks['exact_official_reach_and_high_bits']=True
# Identical untimed-small controls, both execute only the new implementation.
host=ROOT/f'worktrees/{variant}/HighDiv/highdiv';formula=ROOT/'results/correctness/release/host.smt2'
for mode in ['a_off_test','observe_trace','apply_trace']:
 for trace in [False,True]:
  name=mode+('_trace_on' if trace else '_trace_off');d=out/name;d.mkdir();ee=env.copy();ee.update(HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'),HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(d/'rng.txt'))
  if trace:ee.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=name)
  run([host,'-i',formula,'-o',d,'-n','8','-t','60','-s','0','--guidance',mode],name,ee,90);finalize(d,60,8)
 off=out/(mode+'_trace_off');on=out/(mode+'_trace_on')
 for fn in ['samples.formal','native_decisions.txt','rng.txt']:
  assert (off/fn).exists()==(on/fn).exists(),fn
  if (off/fn).exists():assert (off/fn).read_bytes()==(on/fn).read_bytes(),(mode,fn)
 def trajectory(d):return [(r['source'],r['assumptions'],r['result'],r['highdiv_ls_seed']) for r in map(json.loads,(d/'queries.jsonl').read_text().splitlines())]
 assert trajectory(off)==trajectory(on);checks[mode+'_trace_off_on']=True
fixture=ROOT/('results/correctness/release/baseline-off' if a.variant=='release' else 'results/correctness/sanitize/sanitize-off')
assert (out/'a_off_test_trace_off/samples.formal').read_bytes()==(fixture/'samples.formal').read_bytes();checks['off_matches_saved_frozen_baseline']=True
# Inspect actual event invariants; not just expected field names.
semantic=[json.loads(l) for d in out.glob('*-data') if (d/'semantic.jsonl').exists() for l in (d/'semantic.jsonl').read_text().splitlines()]
snapshots=[s for s in semantic if s['kind']=='semantic_snapshot'];tokens=0;withdrawn=0;changed=0
for s in snapshots:
 active={};seen=set()
 for e in s['events']:
  if e['kind'].startswith('assignment_') and e['kind']!='assignment_withdrawn':
   key=(e['watch'],e['assignment_token']);assert key not in seen;seen.add(key);active[e['watch']]=e['assignment_token'];tokens+=1
  if e['kind']=='assignment_withdrawn':assert active.get(e['watch'])==e['assignment_token'];active.pop(e['watch']);withdrawn+=1
  changed+=e['kind']=='relevance_changed'
assert tokens and withdrawn and changed
entry_kinds={e['kind'] for s in snapshots for e in s['events']}
assert {'equality_merged','theory_atom_assign_eh','theory_equality_delivered','disequality_added'}.issubset(entry_kinds),entry_kinds
layers=[s for s in semantic if s['kind']=='model_layer'];assert any(s['layer']=='M_leaf' for s in layers) and any(s['layer']=='M_outer' for s in layers)
for s in layers:
 if s['layer']=='M_outer':assert s['backend_call_id']==s['model_provider_backend_id']
checks['assignment_tokens_relevance_and_provider']=True
# The new map can be disabled; compare native traces with frozen R3 evidence,
# never by executing the frozen historical binary.
prior=ROOT/'results/round3_semantics/correctness'/('release_03' if a.variant=='release' else 'sanitize_01')
for mode in ['a_off_test','observe_trace','apply_trace']:
 name='mapping_off_'+mode;d=out/name;d.mkdir();ee=env.copy();ee.update(GUIDED_R4_MAPPING_OFF='1',HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(d/'rng.txt'))
 run([host,'-i',formula,'-o',d,'-n','8','-t','60','-s','0','--guidance',mode],name,ee,90);finalize(d,60,8)
 for fn in ['samples.formal','native_decisions.txt','rng.txt']:
  old=prior/(mode+'_trace_off')/fn;new=d/fn;assert old.exists()==new.exists(),fn
  if old.exists():assert old.read_bytes()==new.read_bytes(),(mode,fn)
checks['mapping_disabled_matches_saved_R3_native_RNG_and_models']=True
write(out/'summary.json',{'passed':True,'checks':checks,'token_events':tokens,'withdrawals':withdrawn,'relevance_changes':changed,'baseline_executions':0,'binary_sha256':digest(host),'library_sha256':digest(prefix/'lib/libz3.so'),'sole_leak_suppression':digest(ROOT/'tests/lsan-upstream.supp') if a.variant=='sanitize' else None});print('Round4 correctness passed:',a.stage,a.variant,flush=True)
