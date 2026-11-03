from common_r import *
from finalize_samples import finalize
import argparse
p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('attempt');a=p.parse_args();d=attempt('correctness','isolation_'+a.variant+'_'+a.attempt);env=os.environ.copy()
if a.variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
def run(cmd,name):
    write(d/(name+'.command.json'),{'command':list(map(str,cmd)),'binaries':{str(x):digest(x) for x in cmd[:1]},'environment':{k:v for k,v in env.items() if k.endswith('_OPTIONS')}})
    with open(d/(name+'.stdout'),'w') as f,open(d/(name+'.stderr'),'w') as e:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=e,env=env,timeout=240)
    assert r.returncode==0,(name,r.returncode);assert 'runtime error:' not in (d/(name+'.stderr')).read_text();assert 'ERROR: AddressSanitizer' not in (d/(name+'.stderr')).read_text()
run([ROOT/f'build/refinement_state_{a.variant}'],'state')
run([ROOT/f'build/refinement_delivery_cases_{a.variant}',d/'delivery_cases'],'delivery_cases')
for mode in ['off','identity','improve']:run([ROOT/f'build/refinement_isolation_{a.variant}',d/mode,mode],mode)
subprocess.run([python(),ROOT/'scripts/refinement/audit_isolation.py',d],check=True)
write(d/'summary.json',{'passed':True,'variant':a.variant,'audit_sha256':digest(d/'audit.json'),'real_benchmark_sessions':0,'solver_credit_scope':'fixed 2000 synthetic checks, excludes optional work and logs; all modes identical','leak_suppressions':digest(ROOT/'tests/lsan-upstream.supp') if a.variant=='sanitize' else None})
