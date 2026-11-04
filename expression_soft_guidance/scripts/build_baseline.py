"""Rebuild the unmodified HighDiv kernel with the same compiler and flags."""
import pathlib,shutil,subprocess,json,time,hashlib,argparse
from prepare import ROOT,WORKSPACE,write
ap=argparse.ArgumentParser();ap.add_argument('--destination',default='/tmp/expr_soft_baseline_same_compiler');args=ap.parse_args()
manifest=json.loads((ROOT/'build/prepare.json').read_text());original=pathlib.Path(manifest['destination'])/'z3';source=pathlib.Path(args.destination)
assert not source.exists(),'exclusive build directory required'
shutil.copytree(original,source)
for path in manifest['changed_z3_files']:
    if not (WORKSPACE/'HighDiv-master/z3'/path).exists():continue
    shutil.copyfile(WORKSPACE/'HighDiv-master/z3'/path,source/path)
start=time.monotonic()
with (ROOT/'build/baseline_kernel.log').open('w') as log:
    p=subprocess.run(['make','-C','build','-j8','libz3.so'],cwd=source,stdout=log,stderr=subprocess.STDOUT)
assert p.returncode==0,p.returncode
dest=ROOT/'deps/baseline';(dest/'lib').mkdir(parents=True,exist_ok=True);(dest/'include').mkdir(exist_ok=True)
shutil.copyfile(source/'build/libz3.so',dest/'lib/libz3.so')
for p in (source/'src/api').glob('z3*.h'):shutil.copyfile(p,dest/'include'/p.name)
shutil.copyfile(source/'src/api/c++/z3++.h',dest/'include/z3++.h')
report=dict(compiler=subprocess.check_output(['g++','--version'],text=True),wall=time.monotonic()-start,sha256=hashlib.sha256((dest/'lib/libz3.so').read_bytes()).hexdigest(),source=str(source),method='reuse only unchanged objects; restore every modified upstream file from verified HighDiv; rebuild all dependent archives and library')
write(ROOT/'build/baseline_build.json',json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
