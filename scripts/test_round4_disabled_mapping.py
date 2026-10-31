#!/usr/bin/env python3
from common import *
from finalize_samples import finalize
stage,variant,attempt=sys.argv[1:];prefix=ROOT/f'deps/round4_{stage}_{variant}';host=ROOT/f'worktrees/round4_{stage}_{variant}/HighDiv/highdiv';out=ROOT/f'results/round4/correctness/{stage}_{variant}_{attempt}';prior=ROOT/'results/round3_semantics/correctness'/('release_03' if variant=='release' else 'sanitize_01');env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='20'
if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
for mode in ['a_off_test','observe_trace','apply_trace']:
 d=out/('mapping_off_'+mode);d.mkdir(exist_ok=False);ee=env.copy();ee.update(GUIDED_R4_MAPPING_OFF='1',HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(d/'rng.txt'));cmd=[host,'-i',ROOT/'results/correctness/release/host.smt2','-o',d,'-n','8','-t','60','-s','0','--guidance',mode];r=subprocess.run(list(map(str,cmd)),cwd=d,env=ee,capture_output=True,text=True,timeout=90);(d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr;finalize(d,60,8)
 for fn in ['samples.formal','native_decisions.txt','rng.txt']:
  old=prior/(mode+'_trace_off')/fn;new=d/fn;assert old.exists()==new.exists(),fn
  if old.exists():assert old.read_bytes()==new.read_bytes(),(mode,fn)
s=read(out/'summary.json');assert s['library_sha256']==digest(prefix/'lib/libz3.so');s['checks']['mapping_disabled_matches_saved_R3_native_RNG_and_models']=True;write(out/'summary.json',s);print('Disabled M mapping matches saved R3 native choices, RNG and models; no historical execution')
