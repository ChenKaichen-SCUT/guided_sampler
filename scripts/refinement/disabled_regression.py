from common_r import *
from finalize_samples import finalize
import argparse
p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('attempt');a=p.parse_args();out=attempt('correctness','disabled_'+a.variant+'_'+a.attempt);env=os.environ.copy();env.update(REFINEMENT_MODE='off',HIGHDIV_TEST_MAX_QUERIES='20',GUIDED_CCSS_STAGNATION_GUARD='1')
if a.variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
summary={}
for mode in ['S_ref','S_full']:
    d=out/mode;d.mkdir();ee=env.copy();ee.update(HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(d/'rng.txt'))
    host=ROOT/f'worktrees/refinement_{a.variant}/HighDiv/highdiv';cmd=[host,'-i',ROOT/'results/correctness/release/host.smt2','-o',d,'-n','8','-t','60','-s','0','--guidance',mode];write(d/'attempt.json',{'command':list(map(str,cmd)),'binary_sha256':digest(host),'environment':{k:v for k,v in ee.items() if k.startswith(('GUIDED','HIGHDIV','REFINEMENT','ASAN','UBSAN','LSAN'))}})
    with open(d/'stdout.log','w') as f,open(d/'stderr.log','w') as e:r=subprocess.run(list(map(str,cmd)),stdout=f,stderr=e,env=ee,timeout=90)
    assert r.returncode==0;finalize(d,60,8)
    old=ROOT/'results/round5/correctness'/('release_03' if a.variant=='release' else 'sanitize_01')/(mode+'_off')
    def samples(p):return [line.split(': ',1)[1] for line in p.read_text().splitlines()]
    assert samples(d/'samples.formal')==samples(old/'samples.formal'),mode
    for f in ['native_decisions.txt','rng.txt']:assert (d/f).read_bytes()==(old/f).read_bytes(),(mode,f)
    summary[mode]={'passed':True,'saved_round5':str(old.relative_to(ROOT)),'old_binaries_executed':0,'new_binary_sha256':digest(host)}
write(out/'summary.json',summary);print('disabled saved Round5 native behavior PASS',a.variant)
