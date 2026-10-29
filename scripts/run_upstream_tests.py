#!/usr/bin/env python3
import argparse,os,shutil
from common import *
def main():
    parser=argparse.ArgumentParser();parser.add_argument('variant');a=parser.parse_args();tree=(ROOT/'worktrees'/a.variant).resolve();prefix=ROOT/'deps'/a.variant
    if not (tree/'venv').exists():(tree/'venv').symlink_to(prefix,target_is_directory=True)
    # Initialization/movement regression runs the real unchanged CCSS sources.
    # Legacy output-format tests are superseded by Session/typed-output tests.
    env=os.environ.copy()
    if a.variant=='sanitize':
        env['CXX']='g++ -fsanitize=address,undefined -fno-omit-frame-pointer'
        env['ASAN_OPTIONS']='detect_leaks=1:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    cmd=[sys.executable,'-m','unittest','discover','-s',str(tree/'tests'),'-p','test_partitioned_initialization.py','-v']
    p=subprocess.run(cmd,capture_output=True,text=True,env=env)
    out=ROOT/'results/correctness'/('sanitize' if a.variant=='sanitize' else 'release');out.mkdir(parents=True,exist_ok=True)
    (out/'upstream-initialization.stdout').write_text(p.stdout);(out/'upstream-initialization.stderr').write_text(p.stderr)
    assert p.returncode==0,p.stderr
    write(out/'upstream.json',{'passed':True,'command':cmd,'exit':p.returncode,'source_sha256':digest(tree/'z3/src/sampler/sampler.cpp')})
    print(p.stderr)
if __name__=='__main__':main()
