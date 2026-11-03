from common_cr import *
from finalize_samples import finalize
import argparse
p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('attempt');p.add_argument('--mode',choices=['mechanisms','isolation','disabled'],required=True);a=p.parse_args();d=attempt('correctness',a.mode+'_'+a.variant+'_'+a.attempt);env=os.environ.copy()
if a.variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
def run(cmd,name,ee=None):
 ee=env.copy() if ee is None else ee;write(d/(name+'.command.json'),{'command':list(map(str,cmd)),'binary_sha256':digest(cmd[0]),'environment':{k:v for k,v in ee.items() if k.startswith(('REFINEMENT','ASAN','LSAN','UBSAN'))}})
 with open(d/(name+'.stdout'),'w') as f,open(d/(name+'.stderr'),'w') as e:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=e,env=ee,timeout=300)
 assert r.returncode==0,(name,r.returncode);assert 'runtime error:' not in (d/(name+'.stderr')).read_text();assert 'ERROR: AddressSanitizer' not in (d/(name+'.stderr')).read_text()
if a.mode=='mechanisms':
 run([ROOT/f'build/cost_repair_mechanisms_{a.variant}',ROOT/'tests/refinement_cost_repair/fixtures.json',d/'evidence.json'],'mechanisms')
 subprocess.run([python(),ROOT/'tests/refinement_cost_repair/audit_mechanisms.py',d/'evidence.json',d/'independent.json'],check=True)
elif a.mode=='isolation':
 run([ROOT/f'build/cost_repair_state_{a.variant}'],'state');run([ROOT/f'build/cost_repair_delivery_cases_{a.variant}',d/'delivery_cases'],'delivery_cases')
 for repair in ['Legacy','ValueCache','Shared']:
  rd=d/repair;rd.mkdir();ee=env.copy();ee['REFINEMENT_REPAIR_MODE']=repair
  for mode in ['off','identity','improve']:run([ROOT/f'build/cost_repair_isolation_{a.variant}',rd/mode,mode],repair+'_'+mode,ee)
  subprocess.run([python(),ROOT/'scripts/refinement/audit_isolation.py',rd],check=True)
 # Compare native feedback across repair configurations as well as modes.
 for repair in ['ValueCache','Shared']:
  for mode in ['off','identity','improve']:
   for f in ['native_state.jsonl','query_inputs.jsonl','reference_sources.jsonl']:
    assert rows(d/repair/mode/f)==rows(d/'Legacy'/mode/f),(repair,mode,f)
else:
 for repair in ['Legacy','ValueCache','Shared']:
  rd=d/repair;rd.mkdir();ee=env.copy();ee.update(REFINEMENT_MODE='off',REFINEMENT_REPAIR_MODE=repair,HIGHDIV_TEST_MAX_QUERIES='20',GUIDED_CCSS_STAGNATION_GUARD='1',HIGHDIV_NATIVE_DECISION_TRACE=str(rd/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(rd/'rng.txt'))
  cmd=[ROOT/f'worktrees/cost_repair_{a.variant}/HighDiv/highdiv','-i',ROOT/'results/correctness/release/host.smt2','-o',rd,'-n','8','-t','60','-s','0','--guidance','S_ref'];run(cmd,repair,ee);finalize(rd,60,8)
  old=ROOT/'results/round5/correctness'/('release_03' if a.variant=='release' else 'sanitize_01')/'S_ref_off'
  def samples(p):return [line.split(': ',1)[1] for line in p.read_text().splitlines()]
  assert samples(rd/'samples.formal')==samples(old/'samples.formal')
  for f in ['native_decisions.txt','rng.txt']:assert (rd/f).read_bytes()==(old/f).read_bytes()
write(d/'summary.json',{'passed':True,'variant':a.variant,'mode':a.mode,'real_benchmark_sessions':0,'configurations':['Legacy','ValueCache','Shared'],'leak_suppressions':digest(ROOT/'tests/lsan-upstream.supp') if a.variant=='sanitize' else None});print('PASS',a.mode,a.variant)
