from common_r import *
import argparse
p=argparse.ArgumentParser();p.add_argument('variant');p.add_argument('attempt');p.add_argument('--names',nargs='+',default=['state','isolation','delivery_cases','cli']);a=p.parse_args();out=attempt('build_logs','tests_'+a.variant+'_'+a.attempt);tree=ROOT/f'worktrees/refinement_{a.variant}';prefix=ROOT/f'deps/round6_{a.variant}'
checks={}
for name in a.names:
    src=ROOT/('src/refinement/cli.cpp' if name=='cli' else f'tests/refinement/{name}.cpp');exe=ROOT/f'build/refinement_{name}'+pathlib.Path('') if False else ROOT/f'build/refinement_{name}_{a.variant}'
    if name=='cli' and a.variant=='release':exe=ROOT/'build/refinement_cli'
    flags=['-O3','-DNDEBUG'] if a.variant=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
    cmd=['g++','-std=c++20',*flags,'-I'+str(tree/'refinement_include'),'-I'+str(ROOT/'include/round4'),'-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(src),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(exe)]
    with open(out/(name+'.log'),'w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    checks[name]={'command':cmd,'returncode':r.returncode,'binary_sha256':digest(exe) if r.returncode==0 else None};write(out/'summary.json',checks);assert r.returncode==0,name
print('test binaries built',a.variant)
