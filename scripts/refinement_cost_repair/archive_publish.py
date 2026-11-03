from common_cr import *
from archive_results import SplitWriter
from archive_round4 import Joined
import tarfile,gzip

def archive():
 assert read(BASE/'audit_summary.json')['passed'];out=ROOT/'archives/refinement_cost_repair';out.mkdir(exist_ok=False);writer=SplitWriter(out);members={}
 with gzip.GzipFile(fileobj=writer,mode='wb',compresslevel=6,mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w|') as tar:
   for p in sorted(BASE.rglob('*')):
    if not p.is_file():continue
    assert p.suffix not in ('.so','.o','.a','.pyc'),p
    name=str(p.relative_to(ROOT));members[name]={'sha256':digest(p),'bytes':p.stat().st_size};tar.add(p,arcname=name,recursive=False)
 writer.close();parts=[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts];write(out/'manifest.json',{'members':members,'parts':parts,'format':'concatenate ordered gzip parts, lossless tar','base_commit':read(ROOT/'configs/refinement_cost_repair.json')['base'],'all_failed_attempts_retained':True,'third_party_binaries_build_trees_venvs_credentials':False})
 count=0
 with tarfile.open(fileobj=Joined(writer.parts),mode='r|gz') as tar:
  for entry in tar:
   if not entry.isfile():continue
   h=hashlib.sha256();f=tar.extractfile(entry)
   for b in iter(lambda:f.read(1<<20),b''):h.update(b)
   assert h.hexdigest()==members[entry.name]['sha256'];count+=1
 assert count==len(members);write(out/'verification.json',{'passed':True,'members':count,'parts':len(parts),'manifest_sha256':digest(out/'manifest.json')})
 (out/'RESTORE.md').write_text('# 成本修复完整证据恢复\n\n在仓库根目录执行：\n\n```bash\ncat archives/refinement_cost_repair/results.tar.gz.part* | tar -xzf -\n```\n\nmanifest.json 列出每个成员与分片的 SHA256；verification.json 是全量解压复核结果。归档包含全部 9 探针、39 序列、24 oracle、成功和失败测试、原始候选、成本、审计和完整源文本溯源；没有构建树、库或虚拟环境。历史 43 模型及原始收据继续从 archives/refinement 和 archives/round5 恢复，未复制或改写旧冻结证据。\n\n重建先恢复原第六轮 Release/SAN 依赖及上一轮宿主生成源码，然后执行 `scripts/refinement_cost_repair/build.py release <新尝试名>` 与 sanitize 构建。构建入口拒绝改写已冻结 implementation manifest，重建时应在新工作副本使用单独 manifest 目录；不可覆盖本轮正式结果。执行/审计入口也拒绝覆盖已有尝试。逐文件、二进制、库与指标 SHA 见 manifests/refinement_cost_repair/implementation.json。\n')
 print('archive verified',count,len(parts),flush=True)

def publish():
 branch='refinement-cost-repair';assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
 assert subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()=='https://github.com/ChenKaichen-SCUT/guided_sampler.git';assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
 assert read(BASE/'audit_summary.json')['passed'] and read(ROOT/'archives/refinement_cost_repair/verification.json')['passed']
 for part in read(ROOT/'archives/refinement_cost_repair/manifest.json')['parts']:
  p=ROOT/'archives/refinement_cost_repair'/part['file'];assert digest(p)==part['sha256'];subprocess.run(['git','ls-files','--error-unmatch',p.relative_to(ROOT)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();r=subprocess.run(['git','push','-u','origin',branch],cwd=ROOT,capture_output=True,text=True);receipt={'local_sha':sha,'branch':branch,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'verified':False}
 if r.returncode==0:
  remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],cwd=ROOT,text=True).split()[0];receipt.update(remote_sha=remote,verified=remote==sha)
 write(ROOT/'build/refinement-cost-repair-publish-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));assert receipt['verified']
if __name__=='__main__':(archive if sys.argv[1]=='archive' else publish)()
