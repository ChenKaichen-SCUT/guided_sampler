#!/usr/bin/env python3
"""Same receipt acceptance rules as finalize_samples, using bounded memory."""
from common import *
import itertools
def records(path):
 with path.open() as f:
  for line in f:
   try:yield json.loads(line)
   except json.JSONDecodeError:break
def finalize(run,wall=900,limit=None):
 run=pathlib.Path(run);groups=iter(itertools.groupby(records(run/'sample_receipts.jsonl'),lambda r:r['raw_index']));pending=next(groups,None);accepted=0;omitted=[]
 with (run/'samples.raw').open('rb') as raw,(run/'samples.formal').open('xb') as formal,(run/'formal_receipts.jsonl').open('x') as output:
  for idx,line in enumerate(raw):
   group={}
   if pending and pending[0]<idx:raise RuntimeError('Nonmonotone receipt sequence')
   if pending and pending[0]==idx:group={r['kind']:r for r in pending[1]};pending=next(groups,None)
   p,m,c=group.get('prepare'),group.get('commit'),group.get('confirm');reason=None
   if 'reject' in group:reason=group['reject']['status']
   elif not line.endswith(b'\n') or not p or not m or not c:reason='incomplete_transaction'
   elif not p['legal']:reason='invalid'
   elif p['duplicate']:reason='duplicate'
   elif not m['timely'] or not c['timely'] or c['commit_complete']>=wall:reason='late'
   elif p['formal_index']!=accepted:raise RuntimeError('Formal sequence mismatch')
   elif limit is not None and accepted>=limit:raise RuntimeError('Sample count exceeded')
   if reason:omitted.append({'raw_index':idx,'reason':reason})
   else:formal.write(line);output.write(json.dumps({**p,**c})+'\n');accepted+=1
 result={'formal_count':accepted,'omitted':omitted,'raw_sha256':digest(run/'samples.raw'),'formal_sha256':digest(run/'samples.formal')};write(run/'finalization.json',result);return result
