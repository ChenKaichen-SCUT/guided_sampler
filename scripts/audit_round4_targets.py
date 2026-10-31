#!/usr/bin/env python3
"""Independent target reach/value audit using the frozen official evaluator.

No sampler and no solver check are invoked. The subclass records the values
already delivered by the unmodified evaluator to its statistics callback.
"""
import argparse,collections,json,pathlib
from common import *
from evaluate_exact import load_metric
def audit(d,formula):
 d=pathlib.Path(d);metric=load_metric();z3=metric.z3
 class Witness(metric.WireCoverageStatistics):
  def __init__(self):super().__init__();self.current={}
  def evaluate_node(self,node_id,value):self.current[node_id]=value;super().evaluate_node(node_id,value)
 stat=Witness();manual=metric.ManualSatisfiesMetric(pathlib.Path(formula).read_text(),stat);root=z3.And(manual._solver.assertions());nodes=[];seen=set();todo=[root]
 while todo:
  e=todo.pop()
  if e.get_id() in seen:continue
  seen.add(e.get_id());nodes.append(e);todo.extend(reversed(e.children()))
 actions=collections.defaultdict(list)
 for line in (d/'a_actions.jsonl').read_text().splitlines():
  a=json.loads(line);actions[a['query_id']].append(a)
 online={}
 for line in (d/'a_outcomes.jsonl').read_text().splitlines():
  r=json.loads(line);online[(r['query_id'],r['formal_index'])]=r
 receipt_file=(d/'formal_receipts.jsonl').open();receipts=(json.loads(l) for l in receipt_file);done=set();counts=collections.Counter();examples=[];errors=[]
 with (d/'a_outcomes.independent.jsonl').open('x') as out,(d/'samples.formal').open() as inp:
  for i,sample in enumerate(metric.parse_samples(inp)):
   rec=next(receipts);qa=actions.get(rec['query'],[]) if rec['source']=='CDCL' else []
   old={s['node']:stat._storage[nodes[s['node']].get_id()][:2] for a in qa for s in a['support']};stat.current={};assert manual.count_sample(sample)
   if not qa:continue
   done.add(rec['query']);outcomes=[];demands=set()
   for a in qa:
    targets=[]
    for s in a['support']:
     n=s['node'];node=nodes[n];nid=node.get_id();reached=nid in stat.current;v=int(stat.current.get(nid,0));one=int(s['desired_one_mask']);zero=int(s['desired_zero_mask']);before1,before0=map(int,old[n]);hit1=one&v if reached else 0;hit0=zero&~v if reached else 0;new1=hit1&~before1;new0=hit0&~before0
     target={'node':n,'reached':reached,'desired_one_mask':str(one),'desired_zero_mask':str(zero),'hit_one_mask':str(hit1),'hit_zero_mask':str(hit0),'new_one_mask':str(new1),'new_zero_mask':str(new0),'new_covered_for_targets':(new1&before0).bit_count()+(new0&before1).bit_count()}
     for bit in range(1 if z3.is_bool(node) else 64):
      for desired,mask in ((1,one),(0,zero)):
       if mask>>bit&1:
        key=(n,bit,desired)
        if key in demands:counts['repeated_target_across_distinct_actions']+=1
        demands.add(key);counts['targets']+=1;counts['reached' if reached else 'not_reached']+=1
        if reached and ((v>>bit)&1)==desired:counts['desired_value_observed']+=1
        counts['was_missing_before_commit']+=int(bool(((before0&~before1) if desired else (before1&~before0))>>bit&1))
     counts['new_covered_for_targets']+=target['new_covered_for_targets'];targets.append(target)
    outcome={'decision_id':a['decision_id'],'backend_call_id':a['backend_call_id'],'phase_changed':a['phase_changed'],'targets':targets};outcomes.append(outcome);counts['actions_with_formal_model']+=1
    if a['trailed_assignment_popped']:counts['popped_with_formal_model']+=1
    kind='positive' if any(t['new_covered_for_targets'] for t in targets) else 'zero_gain'
    if not any(e['kind']==kind for e in examples):examples.append({'kind':kind,'formal_index':i,'query_id':rec['query'],'action':a,'outcome':outcome})
   row={'query_id':rec['query'],'formal_index':i,'formal_model':True,'outcomes':outcomes};out.write(json.dumps(row)+'\n')
   expected=online.get((rec['query'],i))
   if expected and expected['outcomes'] and expected['outcomes']!=outcomes:errors.append('online_target_outcome_mismatch')
  for q,qa in actions.items():
   if q not in done:
    for a in qa:
     counts['actions_without_formal_model']+=1;out.write(json.dumps({'query_id':q,'decision_id':a['decision_id'],'backend_call_id':a['backend_call_id'],'formal_model':False,'reason':'no_same_query_formal_CDCL_model','reached':None,'desired_value_observed':None})+'\n')
 result={'passed':not errors,'errors':sorted(set(errors)),'counts':dict(counts),'examples':examples,'node_count':len(nodes),'method':'unchanged frozen official ManualSatisfiesMetric, intercepted statistics callbacks; no additional solver check','metric_sha256':digest(metric_path())};write(d/'target_audit.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('formula');a=p.parse_args();r=audit(a.run,a.formula);print(json.dumps({'passed':r['passed'],'counts':r['counts']}));sys.exit(0 if r['passed'] else 1)
