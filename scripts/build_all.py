#!/usr/bin/env python3
import argparse,json,os,pathlib,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def run(cmd,**kw):print('+',' '.join(map(str,cmd)),flush=True);subprocess.run(list(map(str,cmd)),check=True,**kw)
def main():
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['baseline','guided','sanitize']);p.add_argument('--jobs',default=12,type=int);p.add_argument('--z3-only',action='store_true');a=p.parse_args()
    if (ROOT/'results/QUEUE_STARTED.json').exists() and not (ROOT/'results/QUEUE_FINISHED.json').exists():raise RuntimeError('No compilation during formal sampling')
    if a.variant=='baseline' and (ROOT/'results/baseline_seed0_v1/BASELINE_FROZEN.json').exists():raise RuntimeError('Frozen baseline is read only')
    tree=ROOT/'worktrees'/a.variant;prefix=ROOT/'deps'/a.variant
    if not tree.exists():
        temp=pathlib.Path('/tmp/guided_sampler_round1_worktrees')/a.variant
        temp.mkdir(parents=True,exist_ok=False)
        tree.symlink_to(temp,target_is_directory=True)
        for part in ('z3','HighDiv','tests'):
            shutil.copytree(ROOT.parent/'HighDiv-master'/part,tree/part)
        if a.variant!='baseline':run([sys.executable,ROOT/'scripts/patch_z3.py',tree])
    run([sys.executable,ROOT/'scripts/patch_common_z3.py',tree])
    prefix.mkdir(exist_ok=True)
    if not (prefix/'bin/python3').exists():run([sys.executable,'-m','venv',prefix])
    env=os.environ.copy()
    if a.variant=='sanitize':
        env['CXXFLAGS']='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
        env['LDFLAGS']='-fsanitize=address,undefined'
    else:env['CXXFLAGS']='-O3 -DNDEBUG'
    if not (tree/'z3/build/Makefile').exists():
        run([prefix/'bin/python3','scripts/mk_make.py','--python',f'--prefix={prefix}',f'--pypkgdir={prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages']+(['--debug'] if a.variant=='sanitize' else []),cwd=tree/'z3',env=env)
    if a.variant=='sanitize':
        config=tree/'z3/build/config.mk';config.write_text(config.read_text().replace('-O3','-O1').replace('-O0','-O1'))
    run(['make','-C',tree/'z3/build','-j',a.jobs],env=env)
    run(['make','-C',tree/'z3/build','-j',a.jobs,'install'],env=env)
    if not a.z3_only:
        run([sys.executable,ROOT/'scripts/patch_host.py',tree,a.variant])
        flags='-O3 -DNDEBUG -std=c++20 -Wall' if a.variant!='sanitize' else '-O1 -g -std=c++20 -Wall -fsanitize=address,undefined -fno-omit-frame-pointer'
        run(['make','-C',tree/'HighDiv','-j',a.jobs,f'Z3_PREFIX={prefix}',f'CXXFLAGS={flags}'],env=env)
if __name__=='__main__':main()
