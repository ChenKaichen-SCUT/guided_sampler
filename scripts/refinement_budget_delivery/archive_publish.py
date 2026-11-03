from common_bd import *
from archive_results import SplitWriter
from archive_round4 import Joined
import tarfile,gzip

def archive():
 assert read(BASE/'audit_summary.json')['passed'];out=ROOT/'archives/refinement_budget_delivery';out.mkdir(exist_ok=False);writer=SplitWriter(out);members={}
 with gzip.GzipFile(fileobj=writer,mode='wb',compresslevel=6,mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w|') as tar:
   for p in sorted(BASE.rglob('*')):
    if not p.is_file():continue
    assert p.suffix not in ('.so','.o','.a','.pyc'),p
    name=str(p.relative_to(ROOT));members[name]={'sha256':digest(p),'bytes':p.stat().st_size};tar.add(p,arcname=name,recursive=False)
 writer.close();parts=[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts];write(out/'manifest.json',{'members':members,'parts':parts,'format':'ordered gzip parts concatenate to lossless tar','base_commit':read(ROOT/'configs/refinement_budget_delivery.json')['base'],'all_failed_attempts_retained':True,'third_party_binaries_build_trees_venvs_credentials':False})
 count=0
 with tarfile.open(fileobj=Joined(writer.parts),mode='r|gz') as tar:
  for entry in tar:
   assert entry.isfile();h=hashlib.sha256();f=tar.extractfile(entry)
   for b in iter(lambda:f.read(1<<20),b''):h.update(b)
   assert h.hexdigest()==members[entry.name]['sha256'];count+=1
 assert count==len(members);write(out/'verification.json',{'passed':True,'members':count,'parts':len(parts),'manifest_sha256':digest(out/'manifest.json')})
 (out/'RESTORE.md').write_text('# 原预算交付与 real 阻塞诊断：完整证据恢复\n\n请在新的恢复目录执行，不覆盖已有冻结数据：\n\n```bash\ncat /path/to/repo/archives/refinement_budget_delivery/results.tar.gz.part* | tar -xzf -\n```\n\nmanifest.json 含全部成员及分片 SHA256；verification.json 是逐成员完整解压核对结果。包含所有构建/测试失败、4 探针、22 离线序列、4 real 诊断、全部候选、观察、区间证书、成本与独立审计。43 个源模型和原生收据从 archives/refinement 与 archives/round5 恢复；上一轮证据见 archives/refinement_cost_repair。没有第三方二进制、虚拟环境、构建树或凭据。\n\n源码、实际生成宿主文件、二进制和动态库 SHA 见 manifests/refinement_budget_delivery/implementation.json；生成源码副本在本归档的 build_provenance 下。重建应使用新的工作副本和结果/构建目录，build.py 在存在实现冻结清单时拒绝重建，所有执行器拒绝覆盖尝试。不得通过删除冻结清单在原工作目录改写实验。\n')
 print('archive fully verified',count,len(parts),flush=True)

def publish():
 branch='refinement-budget-delivery';assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()==branch
 assert subprocess.check_output(['git','remote','get-url','origin'],text=True).strip()=='https://github.com/ChenKaichen-SCUT/guided_sampler.git';assert not subprocess.check_output(['git','status','--porcelain'],text=True)
 assert read(BASE/'audit_summary.json')['passed'] and read(ROOT/'archives/refinement_budget_delivery/verification.json')['passed']
 for part in read(ROOT/'archives/refinement_budget_delivery/manifest.json')['parts']:
  p=ROOT/'archives/refinement_budget_delivery'/part['file'];assert digest(p)==part['sha256'];subprocess.run(['git','ls-files','--error-unmatch',p.relative_to(ROOT)],check=True,stdout=subprocess.DEVNULL)
 sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();r=subprocess.run(['git','push','-u','origin',branch],capture_output=True,text=True);receipt={'local_sha':sha,'branch':branch,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'verified':False}
 if r.returncode==0:
  remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],text=True).split()[0];receipt.update(remote_sha=remote,verified=remote==sha)
 write(ROOT/'build/refinement-budget-delivery-publish-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));assert receipt['verified']
if __name__=='__main__':(archive if sys.argv[1]=='archive' else publish)()
