from common_bd import *
from runner import stream_rows
import itertools,collections
out=attempt('analysis','probe_equivalence_v1');streams={};counts=collections.Counter();censored=[]
for mode in ['V0','V1','V2','V3']:
 d=BASE/'probes/frozen_v1'/('convert_'+mode);rs,trunc=stream_rows(d/'stream.jsonl');streams[mode]=rs
 if trunc or not any(x['kind']=='summary' for x in rs):censored.append(mode)
for a,b in itertools.combinations(streams,2):
 left=streams[a];right=streams[b];lm=next((x['metadata'] for x in left if x['kind']=='metadata'),None);rm=next((x['metadata'] for x in right if x['kind']=='metadata'),None)
 if lm and rm:assert {k:v for k,v in lm.items() if k!='score_index'}=={k:v for k,v in rm.items() if k!='score_index'};counts['metadata_pairs']+=1
 le={x['native_event_id']:x for x in left if x['kind']=='event_proposed'};re={x['native_event_id']:x for x in right if x['kind']=='event_proposed'}
 for event in le.keys()&re.keys():
  x,y=le[event],re[event]
  if x['selected_direction_order'] and y['selected_direction_order']:assert x['selected_direction_order']==y['selected_direction_order'];assert x['direction_scores']==y['direction_scores'];counts['rank_pairs']+=1
  xd={d['direction_id']:d for d in x['directions']};yd={d['direction_id']:d for d in y['directions']}
  for direction in xd.keys()&yd.keys():
   q,r=xd[direction],yd[direction]
   if 'intervals' in q and 'intervals' in r:assert q['intervals']==r['intervals'];counts['domain_pairs']+=1
   if 'selected_targets' in q and 'selected_targets' in r:assert q['selected_targets']==r['selected_targets'];counts['target_list_pairs']+=1
  def complete(c):return c['kind']=='target' and 'parameters' in c or c['kind']=='candidate' and c.get('evaluation_complete') and not c['reason'].startswith('incomplete') or c.get('reason')=='candidate_duplicate'
  def canonical(c):return {k:v for k,v in c.items() if not k.endswith(('_cpu','_wall'))}
  xc=[canonical(c) for c in x['candidates'] if complete(c)];yc=[canonical(c) for c in y['candidates'] if complete(c)];n=min(len(xc),len(yc));assert xc[:n]==yc[:n],(a,b,event,'completed work is not the same prefix');counts['candidate_or_target_pairs']+=n
write(out/'summary.json',{'passed':True,'pairs':dict(counts),'censored_workers':censored,'uses_only_jointly_completed_work':True,'new_workers':0});print('probe equivalence PASS',dict(counts),flush=True)
