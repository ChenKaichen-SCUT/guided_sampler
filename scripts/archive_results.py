#!/usr/bin/env python3
import tarfile,hashlib,io
from common import *
class SplitWriter:
    def __init__(self,d,limit=50*1024*1024):self.d=d;self.limit=limit;self.i=0;self.n=0;self.f=None;self.parts=[]
    def write(self,b):
        total=len(b)
        while b:
            if self.f is None:self.p=self.d/f'results.tar.gz.part{self.i:04d}';self.f=open(self.p,'xb');self.parts.append(self.p);self.i+=1;self.n=0
            chunk=b[:self.limit-self.n];self.f.write(chunk);self.n+=len(chunk);b=b[len(chunk):]
            if self.n==self.limit:self.f.close();self.f=None
        return total
    def close(self):
        if self.f:self.f.close();self.f=None

def main():
    assert (ROOT/'results/QUEUE_FINISHED.json').exists()
    d=ROOT/'archives';d.mkdir(exist_ok=False);writer=SplitWriter(d);members={}
    with tarfile.open(fileobj=writer,mode='w|gz') as tar:
        for p in sorted((ROOT/'results').rglob('*')):
            if p.is_file():members[str(p.relative_to(ROOT))]={'sha256':digest(p),'bytes':p.stat().st_size};tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    writer.close();write(d/'manifest.json',{'format':'concatenate parts in listed order, gzip tar','parts':[{'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in writer.parts],'members':members})
    (d/'RESTORE.md').write_text('# 恢复原始结果\n\n在仓库根目录执行：\n\n```bash\ncat archives/results.tar.gz.part* | tar -xzf -\n```\n\n逐片与逐成员 SHA-256 见 manifest.json。所有片段均随 Git 提交，不依赖本机绝对路径。\n')
    print('Archived',len(members),'members in',len(writer.parts),'parts')
if __name__=='__main__':main()
