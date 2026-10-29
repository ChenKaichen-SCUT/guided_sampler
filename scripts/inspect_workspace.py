#!/usr/bin/env python3
import hashlib,json,pathlib,urllib.request,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
UP=ROOT.parent/'HighDiv-master'
SHA='f2c6e1756b13281d96cbf90a8bd940129e56cce4'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    tree=json.load(urllib.request.urlopen(f'https://api.github.com/repos/laigroup/HighDiv/git/trees/{SHA}?recursive=1'))
    assert not tree['truncated']
    files=[];differences=[]
    for x in tree['tree']:
        if x['type']!='blob':continue
        p=UP/x['path']
        if not p.is_file(): differences.append({'path':x['path'],'status':'missing'});continue
        b=p.read_bytes();gitsha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        files.append({'path':x['path'],'sha256':sha(p),'git_blob':gitsha})
        if gitsha!=x['sha']:differences.append({'path':x['path'],'expected':x['sha'],'actual':gitsha})
    extra=sorted(str(p.relative_to(UP)) for p in UP.rglob('*') if p.is_file() and str(p.relative_to(UP)) not in {f['path'] for f in files})
    doc={'repository':'https://github.com/laigroup/HighDiv','commit':SHA,'git_metadata':(UP/'.git').exists(),'files':files,'differences':differences,'extra_files':extra}
    (ROOT/'manifests/upstream.json').write_text(json.dumps(doc,indent=2)+'\n')
    inputs=sorted((ROOT.parent/'benchmarks').rglob('*.smt2'))
    assert len(inputs)==8
    public={f['sha256']:f['path'] for f in files if f['path'].endswith('.smt2')}
    inp=[{'path':str(p.relative_to(ROOT.parent)),'sha256':sha(p),'size':p.stat().st_size,'public_source':public.get(sha(p))} for p in inputs]
    (ROOT/'manifests/inputs.json').write_text(json.dumps(inp,indent=2)+'\n')
    (ROOT/'manifests/cpu.txt').write_text(subprocess.check_output(['lscpu','-e=CPU,CORE,SOCKET,ONLINE'],text=True))
    print(json.dumps({'upstream_files':len(files),'differences':differences,'extras':extra,'inputs':len(inp)}))
    assert not differences and not extra
if __name__=='__main__':main()
