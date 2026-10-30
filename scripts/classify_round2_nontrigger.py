#!/usr/bin/env python3
from common import *
import collections,csv
def rows(p):
 with p.open() as f:
  for line in f:yield json.loads(line)
def main():
 results=[]
 for run in read(ROOT/'manifests/round2_a_plan.json')['runs']:
  d=ROOT/run['output'];queries={q['query'] for q in rows(d/'queries.jsonl')};c=collections.Counter();funnel=collections.Counter()
  for req in rows(d/'a_requests.jsonl'):
   if not req['has_request']:c['cost_disabled_requests']+=1
   elif req['query_id'] not in queries:c['registered_without_check_at_deadline']+=1
  for b in rows(d/'a_backend_calls.jsonl'):
   if b.get('kind')=='tactic_stages':continue
   if b.get('disabled_reason')=='non_smt_leaf':c['unsupported_leaf']+=1
   if b['entry_function'] in ('check','setup_and_check') and b['ordinary_decisions']==0:c['SMT_calls_without_native_ordinary']+=1
   funnel.update(b['funnel'])
  results.append({'id':run['id'],**{k:c[k] for k in ['cost_disabled_requests','registered_without_check_at_deadline','unsupported_leaf','SMT_calls_without_native_ordinary']},**{k:funnel[k] for k in ['unmapped_reason_unknown','normalization_incomplete','unsupported_normal_form','already_assigned','no_active_demand','score_tie','quota_rejected','cost_rejected','exposure_rejected','outside_decision_window']},'assigned_targets_over_full_catalog':'NA','unencountered_targets_over_full_catalog':'NA','outside_window_potential':'NA'})
 with (ROOT/'results/round2_a/analysis/nontrigger_reasons.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=results[0]);w.writeheader();w.writerows(results)
 print('Classified query/backend/decision gates separately; unmeasured full-catalog states remain NA')
if __name__=='__main__':main()
