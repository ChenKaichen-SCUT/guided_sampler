import hashlib,json,pathlib,subprocess,time,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'build/prepare.json').read_text())
source=pathlib.Path(manifest['destination'])/'z3'
out=ROOT/'build';out.mkdir(exist_ok=True)
commands=[] if (source/'build/Makefile').exists() else [['python3','scripts/mk_make.py','--prefix='+str(ROOT/'deps/soft')]]
commands+=[['make','-C','build','-j8','libz3.so']]
results=[]
attempt=time.strftime('%Y%m%d_%H%M%S')
for i,command in enumerate(commands):
    start=time.monotonic()
    with (out/f'kernel_{attempt}_{i}.log').open('w') as log:
        p=subprocess.run(command,cwd=source,stdout=log,stderr=subprocess.STDOUT)
    results.append(dict(command=command,exit_code=p.returncode,wall=time.monotonic()-start))
    (out/'kernel_build.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results[-1]),flush=True)
    if p.returncode:raise SystemExit(p.returncode)
dest=ROOT/'deps/soft';(dest/'lib').mkdir(parents=True,exist_ok=True);(dest/'include').mkdir(exist_ok=True)
shutil.copyfile(source/'build/libz3.so',dest/'lib/libz3.so')
for p in (source/'src/api').glob('z3*.h'):shutil.copyfile(p,dest/'include'/p.name)
shutil.copyfile(source/'src/api/c++/z3++.h',dest/'include/z3++.h')
print('library_sha256',hashlib.sha256((dest/'lib/libz3.so').read_bytes()).hexdigest(),flush=True)
