from common5 import *
from archive_results import SplitWriter
from archive_round4 import Joined
import tarfile
def archive():
    assert read(BASE/'audit_summary.json')['passed'];out=ROOT/'archives/round5';out.mkdir(exist_ok=False);writer=SplitWriter(out);members={}
    with tarfile.open(fileobj=writer,mode='w|gz') as tar:
        for p in sorted(BASE.rglob('*')):
            if not p.is_file():continue
            name=str(p.relative_to(ROOT));members[name]={'sha256':digest(p),'bytes':p.stat().st_size};tar.add(p,arcname=name,recursive=False)
    writer.close();parts=[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts];write(out/'manifest.json',{'members':members,'parts':parts,'base_commit':'ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550','historical_archives_duplicated':False})
    verified=set()
    with tarfile.open(fileobj=Joined(writer.parts),mode='r|gz') as tar:
        for member in tar:
            if not member.isfile():continue
            f=tar.extractfile(member);h=hashlib.sha256()
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
            assert h.hexdigest()==members[member.name]['sha256'];verified.add(member.name)
    assert len(verified)==len(members);write(out/'verification.json',{'passed':True,'members':len(verified),'parts':len(parts),'manifest_sha256':digest(out/'manifest.json')})
    (out/'RESTORE.md').write_text('# 第五轮完整证据恢复\n\n在克隆的仓库根目录执行：\n\n```bash\ncat archives/round5/results.tar.gz.part* | tar -xzf -\n```\n\n所有新增正式/合成尝试、原始模型、收据、map、构造配方、RNG、初始化、重放、负结果和审计均包含在归档中。逐成员及分片SHA见manifest.json；已完整流式解压校验。历史证据沿用前四轮归档，不重复复制。原基准输入按前轮权限仅存来源和哈希。\n')
    print('Archived and verified',len(members),'members',len(parts),'parts')
def publish():
    branch='round5-weak-target-ccss-diagnosis';assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
    assert subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()=='https://github.com/ChenKaichen-SCUT/guided_sampler.git'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True);assert read(BASE/'audit_summary.json')['passed'];assert read(ROOT/'archives/round5/verification.json')['passed']
    for r in read(ROOT/'archives/round5/manifest.json')['parts']:
        p=ROOT/'archives/round5'/r['file'];assert digest(p)==r['sha256'];subprocess.run(['git','ls-files','--error-unmatch',p.relative_to(ROOT)],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
    local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();cmd=['git','push','-u','origin',branch];r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);receipt={'command':cmd,'local_sha':local,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'verified':False}
    if r.returncode==0:
        remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],cwd=ROOT,text=True).split()[0];receipt.update(remote_sha=remote,verified=remote==local)
    write(ROOT/'build/round5-publish-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));assert receipt['verified']
if __name__=='__main__':(archive if sys.argv[1]=='archive' else publish)()
