import argparse,pathlib,subprocess,json,time,hashlib
from prepare import ROOT,WORKSPACE,write
ap=argparse.ArgumentParser();ap.add_argument('--tests-only',action='store_true');ap.add_argument('--baseline-only',action='store_true');args=ap.parse_args()
headers=WORKSPACE/'guided_sampler/build/performance_path/header_dependencies/usr/include'
dest=ROOT/'bin';dest.mkdir(exist_ok=True);results=[]
def compile(name,sources,baseline=False):
    prefix=ROOT/'deps/baseline' if baseline else ROOT/'deps/soft'
    command=['g++','-O3','-DNDEBUG','-std=c++20','-I'+str(ROOT/'include'),'-I'+str(headers),'-I'+str(prefix/'include')]
    if baseline:command+=['-DESG_NO_KERNEL']
    command+=list(map(str,sources))+['-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-pthread','-o',str(dest/name)]
    started=time.monotonic()
    with (ROOT/'build'/f'{name}_compile.log').open('w') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    r=dict(name=name,command=command,exit_code=p.returncode,wall=time.monotonic()-started);results.append(r);print(json.dumps(r),flush=True)
    if p.returncode:raise SystemExit(p.returncode)
    r['sha256']=hashlib.sha256((dest/name).read_bytes()).hexdigest()
if args.tests_only:
    compile('pattern_test',[ROOT/'tests/pattern.cpp'],True)
    compile('impossible_test',[ROOT/'tests/impossible.cpp'],True)
else:
    subprocess.run(['python3',str(ROOT/'scripts/prepare_host.py')],check=True)
    sources=[ROOT/'src/main/main.cpp',ROOT/'src/sampler/sampler.cpp',ROOT/'src/sampler/liasampler.cpp']
    compile('highdiv_baseline',sources,True)
    if not args.baseline_only:
        compile('highdiv_soft',sources)
        compile('kernel_test',[ROOT/'tests/kernel.cpp'])
        compile('ccss_test',[ROOT/'tests/ccss.cpp'])
write(ROOT/'build'/('host_tests_build.json' if args.tests_only else 'host_build.json'),json.dumps(results,indent=2)+'\n')
