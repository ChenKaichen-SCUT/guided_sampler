#!/usr/bin/env python3
from common import *
from evaluate_exact import load_metric
import collections,csv
def main():
 root=ROOT/'results/round2_a/micro';plan=read(root/'selection_plan.json');metric=load_metric();z3=metric.z3;rows=[];details=[]
 for case in plan['cases']:
  cid=case['case_id'];snap=read(root/'snapshots'/f'{cid}.state.json');solver=z3.Solver(ctx=metric.CTX);solver.from_string((ROOT/case['input']).read_text());todo=[z3.And(solver.assertions())];nodes=[];seen=set()
  while todo:
   e=todo.pop()
   if e.get_id() in seen:continue
   seen.add(e.get_id());nodes.append(e);todo.extend(reversed(e.children()))
  assert len(nodes)==len(snap['nodes']);window=set()
  for n,e in enumerate(nodes):
   if z3.is_int_value(e) or z3.is_true(e) or z3.is_false(e):continue
   a,b=map(int,snap['nodes'][n]);demand=a^b
   for bit in range(1 if z3.is_bool(e) else 64):
    if len(window)<8 and demand>>bit&1:window.add((n,bit,int(bool(a>>bit&1))))
   if len(window)==8:break
  for mode in ('a_off_test','a_observe_test','a_apply_test'):
   d=root/'runs'/cid/mode;j=read(d/'result.json');s=j['stats'];funnel=collections.Counter();binding=collections.Counter();potential=set();outside=set();leaves=[]
   for b in s.get('backend_calls',[]):
    leaves.append(b['tactic_name']+'/'+b['entry_function']);funnel.update(b['funnel']);binding.update(x['state'] for x in b.get('binding_snapshot',[]))
    for encounter in b.get('native_encounters',[]):
     dest=outside if encounter['outside_window'] else potential
     for t in encounter.get('supported_demands',[]):
      for desired,mask in ((1,int(t['one'])),(0,int(t['zero']))):
       for bit in range(64):
        if mask>>bit&1:dest.add((t['node'],bit,desired))
   row={'case_id':cid,'mode':mode,'result':j['result'],'reason':j['reason_unknown'],'check_seconds':j['check_seconds'],'initialization_seconds':j['initialization_seconds'],'leaves':';'.join(leaves),'ordinary':s.get('ordinary',0),'suggestions':s.get('suggestions',0),'phase_overrides':s.get('phase_overrides',0),'explicit_callback_seconds':s.get('direct_seconds',0),'potential_demands_first64':len(potential),'potential_outside_hypothetical_window':len(potential-window),'potential_decisions65to80':len(outside),'mappable_targets':next((x['A_mappable_targets'] for x in map(json.loads,(d/'a_requests.jsonl').read_text().splitlines())),None) if mode!='a_off_test' else None}
   rows.append(row);details.append({**row,'binding_bounded_sample':dict(binding),'funnel':dict(funnel),'hypothetical_old_window':sorted(window),'actual_old_cursor':'unrecoverable_not_measured','binding_encountered_flag_rederived_from_native_ordinal':'use native_encounters ordinal<=64, not snapshot flag (diagnostic flag can also include 65..80)'})
 comparisons=[]
 for c in plan['cases']:
  d=root/'runs'/c['case_id'];a=d/'a_off_test/native_decisions.txt';b=d/'a_observe_test/native_decisions.txt'
  x=a.read_text().splitlines() if a.exists() else [];y=b.read_text().splitlines() if b.exists() else [];prefix=next((i for i,(u,v) in enumerate(zip(x,y)) if u!=v),min(len(x),len(y)))
  comparisons.append({'case_id':c['case_id'],'off_decisions':len(x),'observe_decisions':len(y),'common_prefix':prefix,'prefix_identical':prefix==min(len(x),len(y))})
 with (root/'mechanism.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 write(root/'analysis.json',{'rows':details,'off_observe_native_prefixes':comparisons,'solver_calls_added':0,'window_comparison':'cursor=0 counterfactual only; historical round1 cursor is unavailable','formal_outside_window_potential':'NA; formal callbacks do not scan beyond64','learned_state_reconstructed':False,'timing_limitations':'micro checks overlap SAN compilation; use for mechanism and ledger separation, not performance claims'})
 print('Analyzed 36 retained calls; all off/observe common native prefixes identical:',all(x['prefix_identical'] for x in comparisons))
if __name__=='__main__':main()
