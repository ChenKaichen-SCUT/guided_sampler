from common_cr import *
import shutil
assert not (MAN/'implementation.json').exists();assert not (BASE/'offline/frozen_v1').exists()
checks={}
for v in ['release','sanitize']:
 for kind in ['mechanisms','isolation','disabled']:
  p=BASE/'correctness'/f'{kind}_{v}_{"frozen" if kind=="mechanisms" else "final"}/summary.json';assert read(p)['passed'];checks[str(p.relative_to(ROOT))]=digest(p)
 p=BASE/'correctness'/f'math_{v}_final/summary.json';assert read(p)['passed'];checks[str(p.relative_to(ROOT))]=digest(p)
for v in ['release','sanitize']:
 p=BASE/f'correctness/mechanisms_{v}_frozen/mechanisms.command.json';assert read(p)['binary_sha256']==digest(ROOT/f'build/cost_repair_mechanisms_{v}')
p=BASE/'correctness/oracle_01.json';assert read(p)['passed'];checks[str(p.relative_to(ROOT))]=digest(p)
files={}
for pattern in ['include/refinement/*.hpp','src/refinement/*','scripts/refinement_cost_repair/*.py','scripts/refinement/independent.py','scripts/refinement/oracle_encoder.py','tests/refinement_cost_repair/*','configs/refinement_cost_repair.json','docs/refinement_cost_repair/implementation.zh.md']:
 for p in ROOT.glob(pattern):
  if p.is_file():files[str(p.relative_to(ROOT))]=digest(p)
artifacts={};libraries={};loaded={};provenance=attempt('build_provenance','frozen_v1')
for v in ['release','sanitize']:
 tree=ROOT/f'worktrees/cost_repair_{v}'
 for p in list((tree/'refinement_include').glob('*'))+list((tree/'HighDiv/src').rglob('*'))+[tree/'HighDiv/makefile']:
  if p.is_file():
   files[str(p.relative_to(ROOT))]=digest(p);dest=provenance/v/p.relative_to(tree);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 dep=tree/'HighDiv/build/sampler/liasampler.d';text=dep.read_text();assert str(tree/'refinement_include/session.hpp') in text and 'refinement/numeric_cache.hpp' in text and 'refinement/dependency_index.hpp' in text
 shutil.copy2(dep,provenance/v/'liasampler.d')
 for p in [tree/'HighDiv/highdiv']+[ROOT/f'build/cost_repair_{n}_{v}' for n in ['math','state','isolation','delivery_cases','mechanisms','worker']]:artifacts[str(p.relative_to(ROOT))]=digest(p)
 lib=ROOT/f'deps/round6_{v}/lib/libz3.so';libraries[str(lib.relative_to(ROOT))]=digest(lib);loaded[v]=subprocess.check_output(['ldd',tree/'HighDiv/highdiv'],text=True)
 assert str(lib) in loaded[v]
protected=read(MAN/'protected.json')
for rel,rec in protected['metadata'].items():
 p=ROOT/rel;assert p.is_file() and p.stat().st_size==rec['bytes'] and p.stat().st_mtime_ns==rec['mtime_ns'],rel
for rel,sha in protected['sha256'].items():assert digest(ROOT/rel)==sha,rel
for rec in protected['prior_artifacts'].values():assert digest(ROOT/rec['path'])==rec['sha256'],rec['path']
for rec in protected['inputs']:assert digest(ROOT/rec['data'])==rec['sha256'],rec['data']
assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'commit implementation before freeze'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();exclusive(MAN/'implementation.json',{'commit':commit,'base':read(ROOT/'configs/refinement_cost_repair.json')['base'],'correctness_passed':True,'correctness':checks,'files':files,'artifacts':artifacts,'libraries':libraries,'loaded_libraries':loaded,'official_metric_sha256':digest(metric_path()),'no_online_sessions':True,'B_disabled':True,'historical_cpu_credit_proven':False,'no_parameter_tuning':True})
print('frozen',commit,digest(MAN/'implementation.json'),flush=True)
