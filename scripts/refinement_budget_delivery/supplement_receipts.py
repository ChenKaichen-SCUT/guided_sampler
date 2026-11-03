"""Fill analysis-only marginal gains for disabled/identity events; retain raw nulls."""
from common_bd import *
from independent import evaluate
from runner import stream_rows
assert read(BASE/'analysis/audit_v1/summary.json')['passed']
records=[]
for name in ['convert','SMT_random','SMT_real']:
 data=read(ROOT/f'results/refinement/offline/inputs_v1/{name}.json');ast=data['ast'];seen0=[0]*len(ast['nodes']);seen1=seen0.copy();prefix=[]
 for pos,m in enumerate(data['models'],1):
  legal,tr=evaluate(ast,m);assert legal;cov=obs=0
  for n,(one,value) in tr.items():
   mask=1 if ast['nodes'][n]['sort']=='Bool' else (1<<64)-1;zero=mask^one
   cov+=((seen0[n]|zero)&(seen1[n]|one)).bit_count()-(seen0[n]&seen1[n]).bit_count();obs+=(zero&~seen0[n]).bit_count()+(one&~seen1[n]).bit_count();seen0[n]|=zero;seen1[n]|=one
  prefix.append({'covered':cov,'observed':obs})
 for stage in ['probes','offline']:
  for d in sorted((BASE/stage/'frozen_v1').glob(name+'_*')):
   rs,trunc=stream_rows(d/'stream.jsonl');s=next(r for r in rs if r['kind']=='summary');assert not trunc
   for rec in s['receipts']:
    assert not rec['actually_delivered'],'this supplement is registered only for the observed all-native outcome'
    gain=prefix[rec['native_event_id']-1]
    if rec['native_gain'] is not None:assert rec['native_gain']==gain
    records.append({'stage':stage,'sequence':d.name,'native_event_id':rec['native_event_id'],'source_assignment_sha':rec['source_assignment_sha'],'native_gain':gain,'delivered_gain':gain,'raw_native_gain_was_null':rec['native_gain'] is None,'origin':'independent post-run analysis of already official-audited frozen assignment; not timed worker work','raw_logs_unchanged':True})
write(BASE/'analysis/receipt_gain_supplement.json',{'records':records,'derived_records':len(records),'raw_null_records':sum(r['raw_native_gain_was_null'] for r in records),'real_solver_checks':0,'new_workers':0});print('analysis-only marginal gain supplement',len(records),flush=True)
