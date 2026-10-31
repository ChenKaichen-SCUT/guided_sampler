#!/usr/bin/env python3
from common import *
import csv,collections
base=ROOT/'results/round4';ts=list(csv.DictReader((base/'analysis/S/target_chain.csv').open()));out=[]
for p in sorted((base/'runs').glob('*_S_cov')):
 aa={(str(a['query_id']),str(a['backend_call_id']),str(a['decision_id'])):a for a in map(json.loads,(p/'a_actions.jsonl').open())};counts=collections.defaultdict(collections.Counter)
 for a in aa.values():
  c=counts[a['preference_source']];c['actions']+=1;c['actual_overrides']+=a['phase_changed'];c['coverage_overrode_defined_reference']+=a['coverage_overrode_reference']
 for r in ts:
  if r['run_id']!=p.name:continue
  a=aa[r['query_id'],r['backend_call_id'],r['decision_id']];c=counts[a['preference_source']];c['target_records']+=1;c['new_covered_records']+=r['new_covered']=='True';c['value_hits']+=r['value_hit']=='True';c['reached']+=r['metric_reached']=='True'
 out.append({'run':p.name,'by_source':counts})
write(base/'analysis/S_action_source_outcomes.json',out)
costs=[]
for p in sorted((base/'runs').iterdir()):
 if not p.is_dir():continue
 qs=[json.loads(l) for l in (p/'queries.jsonl').open()];route=collections.Counter(b.get('outer_route','unknown') for q in qs for b in q['guidance'].get('backend_calls',[]));s=read(p/'summary.json');ledger=json.loads((p/'cost_ledger.jsonl').read_text().splitlines()[-1])
 costs.append({'run':p.name,'routes':route,'CDCL_check_seconds':sum(q['check_seconds'] for q in qs if q['source']=='CDCL'),'CCSS_check_seconds':sum(q['check_seconds'] for q in qs if q['source']=='CCSS'),'explicit_total':s['guidance_cost'],'last_completed_query_categories':ledger['categories'],'uncategorized_tail_included_in_total':s['guidance_cost']-ledger['explicit_seconds'],'exposure_overruns':[q['guidance'].get('exposure_overrun') for q in qs if q['guidance'].get('exposure_overrun',0)>0]})
write(base/'analysis/cost_and_routes.json',costs)
