from common_bd import *
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('attempt');p.add_argument('--names',nargs='+',default=['host','state','delivery_cases','isolation','math','mechanisms','worker','blocking']);a=p.parse_args();d=attempt('build_logs','build_'+a.variant+'_'+a.attempt);assert not (MAN/'implementation.json').exists()
old=ROOT/f'worktrees/cost_repair_{a.variant}';tree=ROOT/f'worktrees/budget_delivery_{a.variant}';prefix=ROOT/f'deps/round6_{a.variant}'
if not tree.exists():
    tmp=pathlib.Path('/tmp/guided_sampler_budget_delivery')/a.variant;tmp.mkdir(parents=True,exist_ok=False);tree.symlink_to(tmp,target_is_directory=True)
    shutil.copytree(old/'HighDiv',tree/'HighDiv',ignore=shutil.ignore_patterns('build','highdiv'))
    shutil.copytree(old/'refinement_include',tree/'refinement_include')
    mf=tree/'HighDiv/makefile';mf.write_text(mf.read_text().replace(str(old/'refinement_include'),str(tree/'refinement_include')))
session=tree/'refinement_include/session.hpp'
s=session.read_text().replace('b,split->repair_configuration));','b,split->search_strategies));').replace('"real_hard",b),b));','"real_hard",b),b,split->repair_configuration));')
if s!=session.read_text():session.write_text(s)
flags=['-O3','-DNDEBUG'] if a.variant=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
summary={}
source_paths=[p for pattern in ['include/refinement/*.hpp','include/round6/sha256.hpp','src/refinement/*','tests/refinement_budget_delivery/*','tests/refinement/*.cpp'] for p in ROOT.glob(pattern) if p.is_file()]
for name in a.names:
 snapshot={str(p.relative_to(ROOT)):digest(p) for p in source_paths}

 if name=='host':
    shutil.rmtree(tree/'HighDiv/build',ignore_errors=True)
    exe=tree/'HighDiv/highdiv';exe.unlink(missing_ok=True);cmd=['make','-C',str(tree/'HighDiv'),'-j2',f'Z3_PREFIX={prefix}','CXXFLAGS='+' '.join([*flags,'-std=c++20','-Wall'])]
 else:
    source=ROOT/({'worker':'src/refinement/budget_delivery_worker.cpp','blocking':'src/refinement/line_blocking_worker.cpp','math':'src/refinement/cli.cpp','mechanisms':'tests/refinement_budget_delivery/mechanisms.cpp'}.get(name,f'tests/refinement/{name}.cpp'))
    exe=ROOT/f'build/budget_delivery_{name}_{a.variant}';cmd=['g++','-std=c++20',*flags,'-I'+str(tree/'refinement_include'),'-I'+str(ROOT/'include/round4'),'-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),'-MMD','-MF',str(d/(name+'.d')),str(source),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(exe)]
 with open(d/(name+'.log'),'w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 assert all(digest(ROOT/p)==sha for p,sha in snapshot.items()),'source changed during compilation'
 summary[name]={'source_sha256':snapshot,'command':cmd,'returncode':r.returncode,'binary_sha256':digest(exe) if r.returncode==0 else None,'library_sha256':digest(prefix/'lib/libz3.so')};write(d/'summary.json',summary);assert r.returncode==0,name
print('built',a.variant,a.names,flush=True)
