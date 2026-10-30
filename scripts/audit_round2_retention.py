#!/usr/bin/env python3
"""Distinguish final internal Boolean assignment from returned model truth.

No new solver check. Evaluate an original exactly equivalent Boolean atom by
complete substitution in the already archived model; restore literal polarity.
Reach and covered gains remain those of the separate official target audit.
"""
from common import *
from evaluate_exact import load_metric
import collections
def main():
 plan=read(ROOT/'manifests/round2_a_plan.json');metric=load_metric();z3=metric.z3;summary={}
 for run in plan['runs']:
  d=ROOT/run['output'];actions=collections.defaultdict(list)
  for line in (d/'a_actions.jsonl').open():
   a=json.loads(line);actions[a['query_id']].append(a)
  if not actions:summary[run['id']]={'actions':0};continue
  s=z3.Solver(ctx=metric.CTX);s.from_string((ROOT/run['input']).read_text());todo=[z3.And(s.assertions())];nodes=[];seen=set();variables={}
  while todo:
   e=todo.pop()
   if e.get_id() in seen:continue
   seen.add(e.get_id());nodes.append(e);todo.extend(reversed(e.children()))
   if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED:variables[str(e.decl().name())]=e
  catalog={x['key']:x for x in map(json.loads,(d/'a_atom_catalog.jsonl').read_text().splitlines())};counts=collections.Counter();examples=[];done=set()
  with (d/'a_retention.independent.jsonl').open('x') as out,(d/'formal_receipts.jsonl').open() as receipts:
   for line in receipts:
    rec=json.loads(line);q=rec['query']
    if rec['source']!='CDCL' or q not in actions:continue
    done.add(q);values={v['name']:int(v['value']) for v in rec['typed']};pairs=[(v,z3.IntVal(values[n],ctx=metric.CTX) if z3.is_int(v) else z3.BoolVal(bool(values[n]),ctx=metric.CTX)) for n,v in variables.items()]
    for a in actions[q]:
     truths=[]
     for rule in catalog[a['canonical_key']]['rules']:
      e=nodes[rule['node']]
      if not z3.is_bool(e):continue
      value=z3.simplify(z3.substitute(e,*pairs));assert z3.is_true(value) or z3.is_false(value)
      desired=bool(int(rule['known_one']));canonical=bool(rule['phase']) if z3.is_true(value)==desired else not bool(rule['phase']);truths.append(canonical!=a['literal_negated'])
     assert truths and all(v==truths[0] for v in truths),'equivalent original atoms disagree';truth=truths[0];internal=a['final_atom_truth'];counts['actions']+=1;counts['model_phase_retained']+=truth==a['effective_phase'];counts['internal_phase_retained']+=internal is not None and internal==a['effective_phase'];counts['internal_vs_model_disagreement']+=internal is not None and internal!=truth
     row={'query_id':q,'formal_index':rec['formal_index'],'backend_call_id':a['backend_call_id'],'decision_id':a['decision_id'],'phase_changed':a['phase_changed'],'native_phase':a['native_phase'],'suggested_phase':a['suggested_phase'],'final_internal_assignment':internal,'returned_model_atom_truth_via_original_equivalent':truth,'model_phase_retained':truth==a['effective_phase'],'trailed_assignment_popped':a['trailed_assignment_popped'],'causal_gain_claimed':False};out.write(json.dumps(row)+'\n')
     if internal is not None and internal!=truth and len(examples)<3:examples.append(row)
   counts['actions_without_formal_model']=sum(len(v) for q,v in actions.items() if q not in done)
  result={'passed':True,'counts':dict(counts),'examples':examples,'method':'full substitution in archived original-variable model; no check; catalog equivalence and literal polarity; does not imply official Reach','limitation':'online final_atom_truth is an internal Boolean assignment and is not necessarily returned model truth for an irrelevant atom; relevance cause was not logged and remains unproven'};write(d/'retention_audit.json',result);summary[run['id']]=result
 write(ROOT/'results/round2_a/retention_audit_summary.json',summary);print(json.dumps({k:v.get('counts',v) for k,v in summary.items()}))
if __name__=='__main__':main()
