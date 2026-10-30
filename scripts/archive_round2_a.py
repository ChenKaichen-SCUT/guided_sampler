#!/usr/bin/env python3
from common import *
from archive_results import SplitWriter
import tarfile,hashlib,io
class Joined(io.RawIOBase):
 def __init__(self,parts):self.parts=iter(parts);self.f=None
 def readable(self):return True
 def read(self,n=-1):
  out=b''
  while n<0 or len(out)<n:
   if self.f is None:
    try:self.f=open(next(self.parts),'rb')
    except StopIteration:break
   x=self.f.read(-1 if n<0 else n-len(out))
   if x:out+=x
   else:self.f.close();self.f=None
  return out
def main():
 root=ROOT/'results/round2_a';assert read(root/'audit_summary.json')['passed'];d=ROOT/'archives/round2_a';d.mkdir(parents=True,exist_ok=False);writer=SplitWriter(d);members={}
 with tarfile.open(fileobj=writer,mode='w|gz') as tar:
  for p in sorted(root.rglob('*')):
   if p.is_file():members[str(p.relative_to(ROOT))]={'sha256':digest(p),'bytes':p.stat().st_size};tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
 writer.close();parts=[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts]
 write(d/'manifest.json',{'format':'concatenate ordered parts; gzip tar','parts':parts,'members':members,'round1_reference_commit':'fc19bd22609295ed405e1ac96bf35d695c42832a','round1_archives_copied':False})
 verified={}
 with tarfile.open(fileobj=Joined(writer.parts),mode='r|gz') as tar:
  for entry in tar:
   if not entry.isfile():continue
   f=tar.extractfile(entry);h=hashlib.sha256()
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
   assert h.hexdigest()==members[entry.name]['sha256'];verified[entry.name]=True
 assert len(verified)==len(members);write(d/'verification.json',{'passed':True,'members':len(verified),'parts':len(parts),'manifest_sha256':digest(d/'manifest.json')})
 (d/'RESTORE.md').write_text('# 第二轮原始证据恢复\n\n在仓库根目录执行：\n\n```bash\ncat archives/round2_a/results.tar.gz.part* | tar -xzf -\n```\n\n逐成员与逐分片哈希见 manifest.json，已完整流式解压校验。第一轮原始归档引用基点 fc19bd22609295ed405e1ac96bf35d695c42832a，不重复复制。\n')
 print('Archived and verified',len(members),'members in',len(parts),'parts',flush=True)
if __name__=='__main__':main()
