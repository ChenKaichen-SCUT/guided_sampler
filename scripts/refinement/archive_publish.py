from common_r import *
from archive_results import SplitWriter
from archive_round4 import Joined
import tarfile,gzip

def archive():
    assert read(BASE/'audit_summary.json')['passed'];out=ROOT/'archives/refinement';out.mkdir(exist_ok=False);writer=SplitWriter(out);members={}
    with gzip.GzipFile(fileobj=writer,mode='wb',compresslevel=6,mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w|') as tar:
            for p in sorted(BASE.rglob('*')):
                if not p.is_file():continue
                name=str(p.relative_to(ROOT));members[name]={'sha256':digest(p),'bytes':p.stat().st_size};tar.add(p,arcname=name,recursive=False)
    writer.close();parts=[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts];write(out/'manifest.json',{'members':members,'parts':parts,'format':'concatenate ordered gzip parts, tar lossless','base_commit':'9270e83b7e95b9d9e51e0246de939d82ff570dce','all_failed_attempts_retained':True,'historical_archives_duplicated':False,'third_party_binaries_or_build_trees_uploaded':False})
    verified=0
    with tarfile.open(fileobj=Joined(writer.parts),mode='r|gz') as tar:
        for entry in tar:
            if not entry.isfile():continue
            h=hashlib.sha256();f=tar.extractfile(entry)
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
            assert h.hexdigest()==members[entry.name]['sha256'];verified+=1
    assert verified==len(members);write(out/'verification.json',{'passed':True,'members':verified,'parts':len(parts),'manifest_sha256':digest(out/'manifest.json')})
    (out/'RESTORE.md').write_text('# 观察保留改进：完整证据恢复\n\n在仓库根目录执行：\n\n```bash\ncat archives/refinement/results.tar.gz.part* | tar -xzf -\n```\n\n全部原始成功、失败、未触发、超时、候选、原生/输出流、事务、Python 审计、官方计分和 oracle 记录均在归档。每成员/分片 SHA256 见 manifest.json；已全量流式解压复核。历史 Ref 序列仍由 archives/round5 恢复，历史 HighDiv 和守卫证据沿用此前归档。本轮附上实际使用的宿主补丁展开文本和头依赖作为构建溯源，不上传构建树、虚拟环境、第三方二进制或凭据。重建需先按仓库原有脚本恢复第六轮 Release/SAN 前置构建，然后运行 scripts/refinement/build.py；源码和动态库 SHA 以本轮 implementation manifest 为准。\n')
    print('Lossless archive verified',verified,'members',len(parts),'parts',flush=True)

def publish():
    branch='observation-preserving-refinement';assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
    assert subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()=='https://github.com/ChenKaichen-SCUT/guided_sampler.git'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    assert read(BASE/'audit_summary.json')['passed'] and read(ROOT/'archives/refinement/verification.json')['passed']
    for part in read(ROOT/'archives/refinement/manifest.json')['parts']:
        p=ROOT/'archives/refinement'/part['file'];assert digest(p)==part['sha256'];subprocess.run(['git','ls-files','--error-unmatch',p.relative_to(ROOT)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();r=subprocess.run(['git','push','-u','origin',branch],cwd=ROOT,capture_output=True,text=True)
    receipt={'local_sha':sha,'branch':branch,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'verified':False}
    if r.returncode==0:
        remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],cwd=ROOT,text=True).split()[0];receipt.update(remote_sha=remote,verified=remote==sha)
    write(ROOT/'build/refinement-publish-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));assert receipt['verified']
if __name__=='__main__':(archive if sys.argv[1]=='archive' else publish)()
