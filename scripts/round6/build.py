from common6 import *
import shutil,argparse
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--jobs',type=int,default=8);p.add_argument('--attempt',required=True);a=p.parse_args()
assert not (BASE/'G1_STARTED.json').exists(),'Guard implementation already frozen for experiments'
out=BASE/'build_logs'/(a.variant+'_'+a.attempt);out.mkdir(exist_ok=False)
tree=ROOT/f'worktrees/round6_{a.variant}';prefix=ROOT/f'deps/round6_{a.variant}';source=(ROOT/f'worktrees/round5_{a.variant}').resolve()
def run(cmd,**kw):print('+',' '.join(map(str,cmd)),flush=True);subprocess.run(list(map(str,cmd)),check=True,**kw)
try:
    if not tree.exists():
        tmp=pathlib.Path('/tmp/guided_sampler_round6_worktrees')/a.variant;tmp.mkdir(parents=True,exist_ok=False);tree.symlink_to(tmp,target_is_directory=True)
        for part in ['z3','HighDiv']:run(['cp','-a','--reflink=auto',source/part,tmp/part])
    if not prefix.exists():run([sys.executable,'-m','venv',prefix])
    run([sys.executable,ROOT/'scripts/round6/patch_sources.py',tree,a.variant])
    env=os.environ.copy();env['CXXFLAGS']='-O3 -DNDEBUG' if a.variant=='release' else '-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
    if a.variant=='sanitize':env['LDFLAGS']='-fsanitize=address,undefined'
    run([prefix/'bin/python3','scripts/mk_make.py','--python',f'--prefix={prefix}',f'--pypkgdir={prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages']+(['--debug'] if a.variant=='sanitize' else []),cwd=tree/'z3',env=env)
    if a.variant=='sanitize':
        c=tree/'z3/build/config.mk';c.write_text(c.read_text().replace('-O3','-O1').replace('-O0','-O1'))
    run(['make','-C',tree/'z3/build','-j',a.jobs],env=env);run(['make','-C',tree/'z3/build','-j',a.jobs,'install'],env=env)
    flags='-O3 -DNDEBUG -std=c++20 -Wall' if a.variant=='release' else '-O1 -g -std=c++20 -Wall -fsanitize=address,undefined -fno-omit-frame-pointer'
    run(['make','-C',tree/'HighDiv','-j',a.jobs,f'Z3_PREFIX={prefix}',f'CXXFLAGS={flags}'],env=env)
    write(out/'summary.json',{'passed':True,'binary_sha256':digest(tree/'HighDiv/highdiv'),'library_sha256':digest(prefix/'lib/libz3.so'),'config_sha256':digest(tree/'z3/build/config.mk')})
except Exception as e:write(out/'failure.json',{'error':str(e),'retained':True});raise
