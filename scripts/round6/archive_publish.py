from common6 import *
from archive_results import SplitWriter
from archive_round4 import Joined
import tarfile,gzip
def archive():
    assert read(BASE/'audit_summary.json')['passed'];expected=read(BASE/'artifact_hashes.json');out=ROOT/'archives/round6';out.mkdir(exist_ok=False);writer=SplitWriter(out);members={}
    with gzip.GzipFile(fileobj=writer,mode='wb',compresslevel=6,mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w|') as tar:
            for p in sorted(BASE.rglob('*')):
                if not p.is_file():continue
                name=str(p.relative_to(ROOT));members[name]={'sha256':digest(p),'bytes':p.stat().st_size}
                if p.name not in ['audit_summary.json','artifact_hashes.json']:assert members[name]['sha256']==expected[name],name
                tar.add(p,arcname=name,recursive=False)
                if len(members)%500==0:print('Archived members',len(members),flush=True)
    assert set(expected)==set(members)-{str((BASE/p).relative_to(ROOT)) for p in ['audit_summary.json','artifact_hashes.json']}
    writer.close();parts=[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts]
    write(out/'manifest.json',{'members':members,'parts':parts,'compression':'gzip level6, lossless','base_commit':'ae85956068154207a442c0e2c8387c573dc32411','historical_archives_duplicated':False})
    verified=set()
    with tarfile.open(fileobj=Joined(writer.parts),mode='r|gz') as tar:
        for member in tar:
            if not member.isfile():continue
            f=tar.extractfile(member);h=hashlib.sha256()
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
            assert h.hexdigest()==members[member.name]['sha256'];verified.add(member.name)
            if len(verified)%500==0:print('Verified members',len(verified),flush=True)
    assert len(verified)==len(members)
    write(out/'verification.json',{'passed':True,'members':len(verified),'parts':len(parts),'manifest_sha256':digest(out/'manifest.json')})
    (out/'RESTORE.md').write_text('# 第六轮完整证据恢复\n\n在仓库根目录执行：\n\n```bash\ncat archives/round6/results.tar.gz.part* | tar -xzf -\n```\n\n归档包含本轮全部成功及失败的合成测试、正式尝试、原始模型、收据、原生退出、map/RNG身份、诊断、计分及审计。没有丢弃 Unknown、取消、失败和未完成记录。分片及每个成员的 SHA256 见 manifest.json；已完整流式解压核验。历史记录沿用此前归档。构建树、第三方二进制、虚拟环境和凭据不在归档中。\n')
    print('Archived and verified',len(members),'members',len(parts),'parts')
def publish():
    branch='round6-guarded-coverage-validation';assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
    assert subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()=='https://github.com/ChenKaichen-SCUT/guided_sampler.git'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    assert read(BASE/'audit_summary.json')['passed'] and read(ROOT/'archives/round6/verification.json')['passed']
    for r in read(ROOT/'archives/round6/manifest.json')['parts']:
        p=ROOT/'archives/round6'/r['file'];assert digest(p)==r['sha256'];subprocess.run(['git','ls-files','--error-unmatch',p.relative_to(ROOT)],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
    local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();cmd=['git','push','-u','origin',branch];r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);receipt={'command':cmd,'local_sha':local,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'verified':False}
    if r.returncode==0:
        remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],cwd=ROOT,text=True).split()[0];receipt.update(remote_sha=remote,verified=remote==local)
    write(ROOT/'build/round6-publish-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));assert receipt['verified']
if __name__=='__main__':(archive if sys.argv[1]=='archive' else publish)()
