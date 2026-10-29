import hashlib,json,pathlib,subprocess,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
UP=ROOT.parent/'HighDiv-master'
INPUTS=ROOT.parent/'benchmarks'
def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())
def write(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def exclusive(p,x):
    with open(p,'x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def metric_path():return ROOT/'worktrees/baseline/HighDiv/my_scripts/calc_metric.py'
def python():return ROOT/'deps/baseline/bin/python3'
def artifact_manifest():
    out={}
    for v in ('baseline','guided'):
        paths={'binary':ROOT/f'worktrees/{v}/HighDiv/highdiv','library':ROOT/f'deps/{v}/lib/libz3.so'}
        out[v]={k:{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for k,p in paths.items()}
    out['metric']={'path':str(metric_path().relative_to(ROOT)),'sha256':digest(metric_path())}
    out['compiler']=subprocess.check_output(['g++','--version'],text=True)
    out['python']=subprocess.check_output([python(),'--version'],text=True)
    out['python_executable_sha256']=digest(python())
    paths=subprocess.check_output([python(),'-c',"import z3,pathlib;print('\\n'.join(sorted({line.split()[-1] for line in pathlib.Path('/proc/self/maps').read_text().splitlines() if 'libz3.so' in line})))"],text=True).strip().splitlines()
    out['metric_loaded_libraries']=[{'path':p,'sha256':digest(p)} for p in paths]
    assert paths and all(x['sha256']==out['baseline']['library']['sha256'] for x in out['metric_loaded_libraries'])
    out['python_packages']=subprocess.check_output([python(),'-m','pip','freeze'],text=True)
    out['headers']={p:digest('/usr/include/'+p) for p in ['nlohmann/json.hpp','boost/multiprecision/cpp_int.hpp']}
    out['host_flags']='-O3 -DNDEBUG -std=c++20 -Wall'
    for v in ('baseline','guided'):out[v]['ldd']=subprocess.check_output(['ldd',ROOT/f'worktrees/{v}/HighDiv/highdiv'],text=True)
    return out
