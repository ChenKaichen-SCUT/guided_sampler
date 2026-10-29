#!/usr/bin/env python3
import argparse,json,pathlib
from common import read,write,digest

def records(path):
    result=[]
    if not path.exists():return result
    for line in path.read_text().splitlines():
        try:result.append(json.loads(line))
        except json.JSONDecodeError:break # interrupted trailing receipt never commits
    return result

def finalize(run,wall=900,limit=None):
    run=pathlib.Path(run);raw=(run/'samples.raw').read_bytes() if (run/'samples.raw').exists() else b''
    lines=raw.splitlines(keepends=True);prepares={};commits={};confirms={};rejects={}
    for r in records(run/'sample_receipts.jsonl'):
        dest={'prepare':prepares,'commit':commits,'confirm':confirms,'reject':rejects}.get(r.get('kind'))
        if dest is not None:dest[r['raw_index']]=r
    accepted=[];omitted=[]
    for idx,line in enumerate(lines):
        p,m,c=prepares.get(idx),commits.get(idx),confirms.get(idx)
        reason=None
        if idx in rejects:reason=rejects[idx]['status']
        elif not line.endswith(b'\n') or not p or not m or not c:reason='incomplete_transaction'
        elif not p['legal']:reason='invalid'
        elif p['duplicate']:reason='duplicate'
        elif not m['timely'] or not c['timely'] or c['commit_complete']>=wall:reason='late'
        elif p['formal_index']!=len(accepted):raise RuntimeError('Formal sequence mismatch')
        elif limit is not None and len(accepted)>=limit:raise RuntimeError('Sample count exceeded')
        if reason:omitted.append({'raw_index':idx,'reason':reason})
        else:accepted.append((line,p,c))
    with open(run/'samples.formal','xb') as f:
        for line,p,c in accepted:f.write(line)
    with open(run/'formal_receipts.jsonl','x') as f:
        for _,p,c in accepted:f.write(json.dumps({**p,**c})+'\n')
    result={'formal_count':len(accepted),'omitted':omitted,'raw_sha256':digest(run/'samples.raw') if (run/'samples.raw').exists() else None,'formal_sha256':digest(run/'samples.formal')}
    write(run/'finalization.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--wall',type=float,default=900);p.add_argument('--limit',type=int);a=p.parse_args();print(finalize(a.run,a.wall,a.limit))
