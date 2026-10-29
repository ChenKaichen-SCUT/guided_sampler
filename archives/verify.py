#!/usr/bin/env python3
"""Verify every stored part and every recoverable tar member without extraction."""
import hashlib,json,pathlib,tarfile,time
root=pathlib.Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
def digest(stream):
 h=hashlib.sha256()
 for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
class Parts:
 def __init__(self):self.paths=iter(manifest['parts']);self.file=None
 def read(self,n):
  result=bytearray()
  while len(result)<n:
   if self.file is None:
    try:self.file=open(root/next(self.paths)['file'],'rb')
    except StopIteration:break
   b=self.file.read(n-len(result))
   if b:result.extend(b)
   else:self.file.close();self.file=None
  return bytes(result)
start=time.monotonic();combined=hashlib.sha256()
for p in manifest['parts']:
 with open(root/p['file'],'rb') as f:assert digest(f)==p['sha256'],p['file']
 with open(root/p['file'],'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):combined.update(b)
seen=set()
with tarfile.open(fileobj=Parts(),mode='r|gz') as archive:
 for member in archive:
  assert member.isfile() and member.name in manifest['members'],member.name
  expected=manifest['members'][member.name]
  assert member.size==expected['bytes'] and digest(archive.extractfile(member))==expected['sha256'],member.name
  assert member.name not in seen;seen.add(member.name)
assert seen==set(manifest['members'])
result={'verified':True,'parts':len(manifest['parts']),'members':len(seen),'concatenated_sha256':combined.hexdigest(),'seconds':time.monotonic()-start}
(root/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
