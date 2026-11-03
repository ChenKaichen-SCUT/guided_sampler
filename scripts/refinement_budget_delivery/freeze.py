from common_bd import *
import shutil
assert not (MAN/'implementation.json').exists()
checks={}
for variant in ['release','sanitize']:
 for kind in ['mechanisms','isolation','disabled','math','worker']:
  p=BASE/'correctness'/f'{kind}_{variant}_sealed/summary.json';assert read(p)['passed'];checks[str(p.relative_to(ROOT))]=digest(p)
 for kind in ['mechanisms','isolation']:
  directory=BASE/'correctness'/f'{kind}_{variant}_sealed'
  for p in directory.glob('*.command.json'):
   command=read(p);assert digest(pathlib.Path(command['command'][0]))==command['binary_sha256'],p
protected=read(MAN/'protected.json')
for rel,rec in protected['metadata'].items():
 p=ROOT/rel;assert p.is_file() and p.stat().st_size==rec['bytes'] and p.stat().st_mtime_ns==rec['mtime_ns'],rel
for rel,sha in protected['hashes'].items():assert digest(ROOT/rel)==sha,rel
plan=read(MAN/'plan.json');assert digest(ROOT/'configs/refinement_budget_delivery.json')==plan['configuration_sha256']
for entry in plan['inputs'].values():assert digest(ROOT/entry['path'])==entry['sha256'];assert digest(pathlib.Path(entry['input']))==entry['input_sha256']
assert digest(metric_path())==plan['official_metric_sha256']
files={}
for pattern in ['include/refinement/*.hpp','include/round6/sha256.hpp','src/refinement/*','scripts/refinement_budget_delivery/*.py','tests/refinement_budget_delivery/*','configs/refinement_budget_delivery.json','docs/refinement_budget_delivery/implementation.zh.md','docs/refinement_budget_delivery/execution_guide.zh.md','scripts/refinement/independent.py','tests/refinement/isolation.cpp','tests/refinement/state.cpp','tests/refinement/delivery_cases.cpp','tests/lsan-upstream.supp']:
 for p in ROOT.glob(pattern):
  if p.is_file():files[str(p.relative_to(ROOT))]=digest(p)
artifacts={};libraries={};loaded={};provenance=attempt('build_provenance','frozen_v1')
for variant in ['release','sanitize']:
 tree=ROOT/f'worktrees/budget_delivery_{variant}'
 build=read(BASE/f'build_logs/build_{variant}_verified3/summary.json')
 for record in build.values():
  assert all(digest(ROOT/p)==sha for p,sha in record['source_sha256'].items())
 assert read(BASE/f'correctness/worker_{variant}_sealed/summary.json')['binary_sha256']==digest(ROOT/f'build/budget_delivery_worker_{variant}')
 for p in list((tree/'refinement_include').glob('*'))+list((tree/'HighDiv/src').rglob('*'))+[tree/'HighDiv/makefile']:
  if p.is_file():
   files[str(p.relative_to(ROOT))]=digest(p);dest=provenance/variant/p.relative_to(tree);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 dep=tree/'HighDiv/build/sampler/liasampler.d';text=dep.read_text()
 for needle in ['refinement/search_strategy.hpp','refinement/direction_score.hpp','refinement/sparse_equality.hpp',str(tree/'refinement_include/session.hpp')]:assert needle in text,(needle,variant)
 shutil.copy2(dep,provenance/variant/'liasampler.d')
 for p in [tree/'HighDiv/highdiv']+[ROOT/f'build/budget_delivery_{n}_{variant}' for n in ['math','state','isolation','delivery_cases','mechanisms','worker','blocking']]:artifacts[str(p.relative_to(ROOT))]=digest(p)
 lib=ROOT/f'deps/round6_{variant}/lib/libz3.so';libraries[str(lib.relative_to(ROOT))]=digest(lib);loaded[variant]=subprocess.check_output(['ldd',tree/'HighDiv/highdiv'],text=True);assert str(lib) in loaded[variant]
assert not subprocess.check_output(['git','diff','--name-only'],text=True).strip(),'commit source before freeze'
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();exclusive(MAN/'implementation.json',{'commit':commit,'base':read(ROOT/'configs/refinement_budget_delivery.json')['base'],'correctness_passed':True,'correctness':checks,'files':files,'artifacts':artifacts,'libraries':libraries,'loaded_libraries':loaded,'official_metric_sha256':digest(metric_path()),'historical_cpu_credit_proven':False,'new_native_sampling':0,'real_solver_checks':0,'B':False,'no_parameter_tuning_after_real_probes':True})
print('implementation frozen',commit,digest(MAN/'implementation.json'),flush=True)
