"""Audit already-recorded domains and statuses. No new candidates or solver calls."""
from common_cr import *
from runner import stream_rows
import collections
out=attempt('analysis','domain_records_v1');totals=collections.defaultdict(collections.Counter);rows_out=[]
for track in ['probes/legacy_v1','probes/new_v1','offline/frozen_v1']:
 for p in (BASE/track).glob('*/attempt.json'):
  job=read(p);rs,truncated=stream_rows(p.parent/'stream.jsonl');assert not truncated
  group=('probe' if track.startswith('probes') else 'main_L2' if job['layer']=='L2' and not job['component_only'] else 'supplement')+':'+job['instance']+':'+job['mode'];counts=totals[group]
  for r in rs:
   if r['kind']!='event':continue
   dirs={d['direction_id']:d for d in r['directions']}
   for d in dirs.values():
    counts['status_'+d['status']]+=1
    if 'intervals' not in d:continue
    u=d['intervals'];counts['logged_complete_domains']+=1
    cls='exact_empty' if not u else 'singleton_zero' if u==[['0','0']] else 'has_nonzero_parameter';counts[cls]+=1
    # Full legal original formula contains its verified native anchor.
    assert cls!='exact_empty';assert any((lo=='-inf' or int(lo)<=0) and (hi=='+inf' or int(hi)>=0) for lo,hi in u)
   for c in r['candidates']:
    if c['kind']!='target':continue
    if c.get('modular_status')=='no_nonzero_legal_parameter':assert dirs[c['direction_id']]['intervals']==[['0','0']];counts['verified_no_nonzero_legal_parameter']+=1
    if c.get('modular_status') in ['wall_budget_exhausted','cpu_budget_exhausted']:assert not c.get('search_complete',True);counts['incomplete_hit_search']+=1
  rows_out.append({'sequence':p.parent.name,'group':group})
write(out/'summary.json',{'passed':True,'groups':dict(totals),'solver_checks':0,'additional_real_experiment_workers':0,'scope':'classify and verify recorded completed intervals; no reconstruction of uncompleted work or changes to raw logs'});print(json.dumps(dict(totals),ensure_ascii=False))
