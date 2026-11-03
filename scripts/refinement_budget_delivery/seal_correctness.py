from common_bd import *
variant=sys.argv[1];d=attempt('build_logs','sealed_pipeline_'+variant);commands=[
 [sys.executable,ROOT/'scripts/refinement_budget_delivery/build.py',variant,'verified3'],
 [sys.executable,ROOT/'scripts/refinement_budget_delivery/run_correctness.py',variant,'sealed','--mode','mechanisms'],
 [python(),ROOT/'tests/refinement_budget_delivery/audit_worker.py',variant,BASE/f'correctness/worker_{variant}_sealed'],
 [python(),ROOT/'tests/refinement_budget_delivery/test_math.py',variant,BASE/f'correctness/math_{variant}_sealed'],
 [sys.executable,ROOT/'scripts/refinement_budget_delivery/run_correctness.py',variant,'sealed','--mode','disabled'],
 [sys.executable,ROOT/'scripts/refinement_budget_delivery/run_correctness.py',variant,'sealed','--mode','isolation']]
completed=[]
for k,cmd in enumerate(commands):
 with (d/f'{k:02d}.stdout').open('w') as o,(d/f'{k:02d}.stderr').open('w') as e:r=subprocess.run(list(map(str,cmd)),stdout=o,stderr=e,cwd=ROOT)
 completed.append({'command':list(map(str,cmd)),'returncode':r.returncode});write(d/'progress.json',completed);print('sealed',variant,k,r.returncode,flush=True);assert r.returncode==0,(variant,k)
write(d/'summary.json',{'passed':True,'completed':completed})
