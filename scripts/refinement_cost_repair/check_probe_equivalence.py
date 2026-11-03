from common_cr import *
from runner import stream_rows
import itertools
out=attempt('analysis','probe_equivalence_v1');counts={'metadata_pairs':0,'direction_selection_pairs':0,'domain_pairs':0,'target_pairs':0,'candidate_pairs':0,'completed_result_pairs':0}
def strip(j):
 if isinstance(j,dict):return {k:strip(v) for k,v in j.items() if not (k.endswith('_cpu') or k.endswith('_wall') or k in ['work_counters_at_cancel','remaining_work_unknown'])}
 if isinstance(j,list):return [strip(v) for v in j]
 return j
for name in ['convert','SMT_random','SMT_real']:
 configs={}
 for mode in ['Legacy','ValueCache','Shared']:
  d=BASE/'probes'/('legacy_v1' if mode=='Legacy' else 'new_v1')/(name+'_'+mode);rs,truncated=stream_rows(d/'stream.jsonl');assert not truncated
  configs[mode]={'metadata':next((r['metadata'] for r in rs if r['kind']=='metadata'),None),'events':{r['native_event_id']:r for r in rs if r['kind']=='event'}}
 for (a,x),(b,y) in itertools.combinations(configs.items(),2):
  if x['metadata'] is not None and y['metadata'] is not None:assert x['metadata']==y['metadata'],(name,a,b,'metadata');counts['metadata_pairs']+=1
  for pos in x['events'].keys()&y['events'].keys():
   p,q=x['events'][pos],y['events'][pos]
   if p['baseline_scored'] and q['baseline_scored']:
    for k in ['protected_masks','protected_count','base_gain_covered','base_gain_observed']:assert p[k]==q[k],(name,a,b,pos,k)
   if p['selected_direction_order'] and q['selected_direction_order']:assert p['selected_direction_order']==q['selected_direction_order'];counts['direction_selection_pairs']+=1
   xd={d['direction_id']:d for d in p['directions']};yd={d['direction_id']:d for d in q['directions']}
   for d in xd.keys()&yd.keys():
    if xd[d]['status'] in ['supported','unsupported'] and yd[d]['status'] in ['supported','unsupported']:assert xd[d]['status']==yd[d]['status'],(name,a,b,pos,d)
    if 'intervals' in xd[d] and 'intervals' in yd[d]:assert xd[d]['intervals']==yd[d]['intervals'];counts['domain_pairs']+=1
    if 'selected_targets' in xd[d] and 'selected_targets' in yd[d]:assert xd[d]['selected_targets']==yd[d]['selected_targets'];counts['target_pairs']+=1
   def candidates(row):
    return {(c['direction_id'],c['t']):c for c in row['candidates'] if c['kind']=='candidate' and 'missing_observations' in c and not c.get('reason','').startswith('incomplete')}
   xc,yc=candidates(p),candidates(q)
   for key in xc.keys()&yc.keys():
    for field in ['assignment','original_formula_valid','hard_conditions_valid','actual_observations','missing_observations','output_duplicate','gain_covered','gain_observed','reason']:assert xc[key][field]==yc[key][field],(name,a,b,pos,key,field)
    counts['candidate_pairs']+=1
   if p['cancellation'] in ['', 'candidate_cap'] and q['cancellation']==p['cancellation']:
    for field in ['chosen','unprotected_chosen','completed_evaluations']:assert p[field]==q[field],(name,a,b,pos,field)
    counts['completed_result_pairs']+=1
write(out/'summary.json',{'passed':True,**counts,'real_solver_checks':0,'semantic_mismatch_stops_before_matrix':True});print('probe equivalence PASS',counts,flush=True)
