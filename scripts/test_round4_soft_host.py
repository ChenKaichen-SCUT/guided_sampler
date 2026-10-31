#!/usr/bin/env python3
"""Controlled end-to-end S CLI, provenance and shared route checks, not benchmarks."""
from common import *
from finalize_samples import finalize
variant=sys.argv[1];assert variant in ['release','sanitize'];out=ROOT/f'results/round4/correctness/soft_host_{variant}';out.mkdir(exist_ok=True);assert not (out/"summary.json").exists();host=ROOT/f'worktrees/round4_S_{variant}/HighDiv/highdiv';lib=ROOT/f'deps/round4_S_{variant}/lib/libz3.so';env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='20'
if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
audit=ROOT/f'build/round4-host-RNG-{variant}';subprocess.run(['g++','-std=c++20','-O2',ROOT/'tests/round4/audit_reference_rng.cpp','-o',audit],check=True);results={}
for mode in ['S_ref','S_cov']:
 d=out/mode;d.mkdir(exist_ok=True);ee=env.copy();ee.update(GUIDED_SEMANTIC_TRACE_DIR=str(d),GUIDED_SEMANTIC_RUN_ID=mode,HIGHDIV_ROUTE_LOG=str(d/'routes.jsonl'),HIGHDIV_NATIVE_DECISION_TRACE=str(d/'native_decisions.txt'),GUIDED_TEST_RNG_TRACE=str(d/'rng.txt'))
 cmd=[host,'-i',ROOT/'results/correctness/release/host.smt2','-o',d,'-n','8','-t','60','-s','0','--guidance',mode];
 if not (d/'command.json').exists():
  r=subprocess.run(list(map(str,cmd)),env=ee,capture_output=True,text=True,timeout=90);(d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr);write(d/'command.json',{'command':list(map(str,cmd)),'exit_code':r.returncode});assert r.returncode==0,r.stderr
 else:assert read(d/'command.json')=={'command':list(map(str,cmd)),'exit_code':0},'do not repeat failed host execution'
 if not (d/'finalization.json').exists():finalize(d,60,8)

 qs=[json.loads(l) for l in (d/'queries.jsonl').open()];inputs=[json.loads(l) for l in (d/'query_inputs.jsonl').open()];assert len(inputs)==sum(q['source']=='CDCL' for q in qs);assert all(q['assumptions']==[] for q in qs if q['source']=='CDCL');assert all(r['hard_assumptions_count']==0 and r['policy']==mode for r in inputs);assert any(r['reference_count'] for r in inputs),'source reference never exercised'
 for q in qs:
  g=q['guidance']
  if not g:continue
  assert all(g[k]==0 for k in ['b_encoded','b_internalized','b_selected','guidance_added_assertions','guidance_created_bool_vars','guidance_marked_relevant']);assert g['suggestions']<=4
  for a in g['actions']:assert a['native_var']==a['actual_var'] and a['decision_id']<=64
 
 for name in ['rng_audit.stdout','rng_audit.stderr']:
  if (d/name).exists():(d/name).rename(d/(name+'.prior_failed'))
 rr=subprocess.run([audit,d],capture_output=True,text=True);(d/'rng_audit.stdout').write_text(rr.stdout);(d/'rng_audit.stderr').write_text(rr.stderr);assert rr.returncode==0,rr.stderr
 results[mode]={'query_count':len(qs),'reference_checks':sum(bool(r['reference_count']) for r in inputs),'rng_replay':json.loads(rr.stdout),'first_model':(d/'samples.formal').read_text().splitlines()[0],'first_route':qs[0]['guidance']['backend_calls'][0]['outer_route']}
assert results['S_ref']['first_model']==results['S_cov']['first_model'];assert results['S_ref']['first_route']==results['S_cov']['first_route']
write(out/'summary.json',{'passed':True,'variant':variant,'results':results,'binary_sha256':digest(host),'library_sha256':digest(lib),'benchmark_runs':0});print('soft host passed',variant)
