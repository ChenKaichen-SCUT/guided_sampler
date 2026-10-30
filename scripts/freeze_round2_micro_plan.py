#!/usr/bin/env python3
"""Deterministic selection from the UNIQUE historical baseline; no solver calls."""
from common import *
def main():
 out=ROOT/'results/round2_a/micro';out.mkdir(parents=True,exist_ok=True)
 old=read(ROOT/'manifests/plan.json');cases=[]
 for input_id in (0,2,3,4):
  run=next(r for r in old['runs'] if r['id']==f'highdiv_time900_{input_id:02}')
  d=ROOT/run['output'];hashes=read(d/'artifact_hashes.json')
  assert digest(d/'queries.jsonl')==hashes['queries.jsonl']
  # First query has no observation history; all later CDCL queries have at least
  # the first confirmed baseline model on these sealed runs (verified below).
  eligible=[]
  with (d/'queries.jsonl').open() as f:
   for line in f:
    q=json.loads(line)
    if q['source']=='CDCL' and q['query']>1 and q['end']<run['wall'] and q['reason_unknown']!='canceled':eligible.append(q)
  chosen=[('first_history',eligible[0] if eligible else None),('tenth_history',eligible[9] if len(eligible)>9 else None),('last_complete',eligible[-1] if eligible else None)]
  counts={q['query']:0 for _,q in chosen if q}
  assert digest(d/'formal_receipts.jsonl')==hashes['formal_receipts.jsonl']
  with (d/'formal_receipts.jsonl').open() as f:
   for line in f:
    rec=json.loads(line)
    for q in counts:
     if rec['query']<q:counts[q]+=1
  for tag,q in chosen:
   case={'case_id':f'{input_id:02}_{tag}','source_run':run['id'],'source_commit':'fc19bd22609295ed405e1ac96bf35d695c42832a','input':run['input'],'input_sha256':run['input_sha256'],'selection':tag,'query':q,'history_models':counts.get(q['query']) if q else None,'source_samples':str((d/'samples.formal').relative_to(ROOT)),'source_samples_sha256':hashes['samples.formal'],'reconstructed_learned_state':False,'upstream_timeout_ms':50000,'micro_timeout_ms':2000,'state':'selected' if q else 'missing'}
   assert not q or case['history_models']>0
   cases.append(case)
 modes=['a_off_test','a_observe_test','a_apply_test'];jobs=[]
 for i,case in enumerate(cases):
  if case['state']=='missing':continue
  for j in range(3):jobs.append({'case_id':case['case_id'],'mode':modes[(i+j)%3],'ordinal':len(jobs)})
 exclusive(out/'selection_plan.json',{'selection_source':'frozen HighDiv time900 query and formal receipts','cases':cases,'jobs':jobs,'maximum_calls':36,'timeout_ms':2000,'parameters_tuned_on_results':False})
 print('Frozen',len(cases),'snapshots and',len(jobs),'rotating calls; no samplers invoked')
if __name__=='__main__':main()
