from common_r import *
import argparse
p=argparse.ArgumentParser();p.add_argument('--correctness-attempt',required=True);p.add_argument('--math-release',required=True);p.add_argument('--math-sanitize',required=True);p.add_argument('--disabled-attempt',required=True);a=p.parse_args();assert not (MAN/'implementation.json').exists();assert not (BASE/'offline/frozen_v1').exists()
checks={}
for v in ['release','sanitize']:
    for kind,attempt_id in [('isolation',a.correctness_attempt),('disabled',a.disabled_attempt)]:
        path=BASE/'correctness'/f'{kind}_{v}_{attempt_id}'/'summary.json';j=read(path);assert j.get('passed',all(x.get('passed',False) for x in j.values() if isinstance(x,dict)));checks[str(path.relative_to(ROOT))]=digest(path)
    path=BASE/'correctness'/('math_'+v+'_'+(a.math_release if v=='release' else a.math_sanitize))/'summary.json';assert read(path)['passed'];checks[str(path.relative_to(ROOT))]=digest(path)
for f in ['oracle_encoder_test_01.log','preservation_test_01.log']:
    path=BASE/'build_logs'/f;assert json.loads(path.read_text())['passed'];checks[str(path.relative_to(ROOT))]=digest(path)
files={}
for pattern in ['include/refinement/*','src/refinement/*','scripts/refinement/*.py','tests/refinement/*','configs/refinement.json','docs/refinement/*.md']:
    for p in ROOT.glob(pattern):
        if p.is_file():files[str(p.relative_to(ROOT))]=digest(p)
artifacts={}
for v in ['release','sanitize']:
    for name,path in [('host',ROOT/f'worktrees/refinement_{v}/HighDiv/highdiv'),('library',ROOT/f'deps/round6_{v}/lib/libz3.so'),('cli',ROOT/('build/refinement_cli' if v=='release' else 'build/refinement_cli_sanitize'))]:artifacts[name+'_'+v]={'path':str(path.relative_to(ROOT)),'sha256':digest(path)}
    tree=ROOT/f'worktrees/refinement_{v}'
    for p in list((tree/'refinement_include').glob('*'))+list((tree/'HighDiv/src').rglob('*'))+[tree/'HighDiv/makefile']:
        if p.is_file():files[str(p.relative_to(ROOT))]=digest(p)
    dep=(tree/'HighDiv/build/sampler/liasampler.d').read_text();assert str(tree/'refinement_include/session.hpp') in dep and '/include/refinement/' in dep
    checks['loaded_library_'+v]=subprocess.check_output(['ldd',tree/'HighDiv/highdiv'],text=True)
exclusive(MAN/'implementation.json',{'files':files,'artifacts':artifacts,'correctness':checks,'base':read(ROOT/'configs/refinement.json')['base_commit'],'metric_sha256':digest(metric_path()),'B_disabled':True,'extra_production_solver_checks':0,'frozen_before_offline':True,'no_candidate_parameter_tuning':True})
print('Implementation frozen',digest(MAN/'implementation.json'),flush=True)
