#!/usr/bin/env python3
import argparse,os,pathlib,shutil,subprocess,sys
from common import ROOT,UP
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--jobs',type=int,default=8);p.add_argument('--host-only',action='store_true');p.add_argument('--z3-only',action='store_true');a=p.parse_args()
name='round2_'+a.variant;tree=ROOT/'worktrees'/name;prefix=ROOT/'deps'/name
q=ROOT/'results/round2_a/QUEUE_STARTED.json'
if q.exists():raise RuntimeError('Frozen round2 implementation cannot be rebuilt after formal start')
def run(c,**kw):print('+',' '.join(map(str,c)),flush=True);subprocess.run(list(map(str,c)),check=True,**kw)
if not tree.exists():
 temp=pathlib.Path('/tmp/guided_sampler_round2_worktrees')/a.variant;temp.mkdir(parents=True,exist_ok=False);tree.symlink_to(temp,target_is_directory=True)
 for part in ('z3','HighDiv','tests'):shutil.copytree(UP/part,temp/part)
 # Independent copies of previously compiled unchanged objects; no hardlinks.
 old=ROOT/'worktrees'/('sanitize' if a.variant=='sanitize' else 'baseline')/'z3/build'
 if old.exists():run(['cp','-a','--reflink=auto',str(old),str(temp/'z3/build')])
prefix.mkdir(exist_ok=True)
if not (prefix/'bin/python3').exists():run([sys.executable,'-m','venv',prefix])
env=os.environ.copy();env['CXXFLAGS']='-O3 -DNDEBUG' if a.variant=='release' else '-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
if a.variant=='sanitize':env['LDFLAGS']='-fsanitize=address,undefined'
if not a.host_only:
 run([sys.executable,ROOT/'scripts/patch_round2_z3.py',tree])
 if not (tree/'z3/build/.round2_configured').exists():
  run([prefix/'bin/python3','scripts/mk_make.py','--python',f'--prefix={prefix}',f'--pypkgdir={prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages']+(['--debug'] if a.variant=='sanitize' else []),cwd=tree/'z3',env=env)
  (tree/'z3/build/.round2_configured').touch()
 if a.variant=='sanitize':
  config=tree/'z3/build/config.mk';config.write_text(config.read_text().replace('-O3','-O1').replace('-O0','-O1'))
 run(['make','-C',tree/'z3/build','-j',a.jobs],env=env)
 run(['make','-C',tree/'z3/build','-j',a.jobs,'install'],env=env)
if not a.z3_only:
 run([sys.executable,ROOT/'scripts/patch_round2_host.py',tree])
 flags='-O3 -DNDEBUG -std=c++20 -Wall' if a.variant=='release' else '-O1 -g -std=c++20 -Wall -fsanitize=address,undefined -fno-omit-frame-pointer'
 run(['make','-C',tree/'HighDiv','-j',a.jobs,f'Z3_PREFIX={prefix}',f'CXXFLAGS={flags}'],env=env)
