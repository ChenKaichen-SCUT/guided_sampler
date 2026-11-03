from common_cr import *
from runner import stream_rows
import collections
out=attempt('analysis','diagnosis_v1');events=[];stages=[];pre=[];opportunities=[];reasons=collections.Counter()
for stage in ['probes/legacy_v1','probes/new_v1','offline/frozen_v1']:
 for d in sorted((BASE/stage).iterdir()):
  if not (d/'attempt.json').is_file():continue
  job=read(d/'attempt.json');rs,truncated=stream_rows(d/'stream.jsonl');assert not truncated
  es={r['native_event_id']:r for r in rs if r['kind']=='event'};cs={r['native_event_id']:r for r in rs if r['kind']=='event_cost'};p=next(r for r in rs if r['kind']=='preprocess');pre.append({'track':stage,'sequence':d.name,'status':p['status'],'cpu':p['cpu'],'wall':p['wall'],'trace':p['trace']})
  for pos,r in es.items():
   c=cs[pos];counter=collections.Counter();targets=collections.Counter()
   for x in r['candidates']:
    if x['kind']=='target':targets[x.get('modular_status','unrecorded')]+=1
    else:counter[x.get('reason','unrecorded')]+=1
   row={'track':stage,'sequence':d.name,'instance':job['instance'],'mode':job['mode'],'position':pos,'reason':r['reason'],'cancellation':r['cancellation'],'cancel_stage':c['trace']['last_incomplete_stage'],'domains':c['trace']['completed_domains'],'completed_evaluations':r['completed_evaluations'],'parameters':sum(len(x.get('parameters',[])) for x in r['candidates'] if x['kind']=='target'),'candidate_records':sum(counter.values()),'distinct_complete_assignments':len({tuple(x['assignment']) for x in r['candidates'] if x['kind']=='candidate' and x.get('reason') in ['protected_observation_missing','eligible_strict_improvement','legal_not_better_than_native','output_duplicate']}),'candidate_reasons':dict(counter),'target_statuses':dict(targets),'cpu':c['cpu'],'wall':c['wall'],'trace':c['trace']};events.append(row)
   if r['chosen']:
    q=r['chosen'];opportunities.append({'track':stage,'sequence':d.name,'position':pos,'base_covered_gain':r['base_gain_covered'],'chosen_covered_gain':q['gain_covered'],'extra_covered':q['gain_covered']-r['base_gain_covered'],'protected_count':r['protected_count'],'direction':q['direction'],'parameter':q['t'],'assignment':q['assignment'],'official_trace':q['trace'],'diagnostic_only':stage.startswith('probes')})
write(out/'events.json',events);write(out/'preprocess.json',pre);write(out/'diagnostic_opportunities.json',opportunities)
for track in ['probes','offline']:
 rows=[r for r in events if r['track'].startswith(track) and r['position']!=1];summary={'events':len(rows),'completed_evaluations':sum(r['completed_evaluations'] for r in rows),'completed_domains':sum(r['domains'] for r in rows),'parameters':sum(r['parameters'] for r in rows),'cancel_stages':dict(collections.Counter(str(r['cancel_stage']) for r in rows if r['cancellation'])),'candidate_reasons':dict(sum((collections.Counter(r['candidate_reasons']) for r in rows),collections.Counter())),'target_statuses':dict(sum((collections.Counter(r['target_statuses']) for r in rows),collections.Counter()))};write(out/(track+'_summary.json'),summary)
print('diagnosis written, strict diagnostic opportunities',[(r['sequence'],r['position'],r['extra_covered']) for r in opportunities],flush=True)
