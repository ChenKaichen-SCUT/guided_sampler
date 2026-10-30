#!/usr/bin/env python3
"""D0: read-only audit and deterministic selection; never calls Solver.check."""
from common import *
from evaluate_exact import load_metric
import collections,csv
OUT=ROOT/'results/round3_semantics'
def rows(path):
 with pathlib.Path(path).open() as f:
  for line in f:yield json.loads(line)
def main():
 plan=read(ROOT/'manifests/round2_a_plan.json');metric=load_metric();z3=metric.z3;output=[];actions_all={};case_data={};overview=[];verified={};fingerprints={}
 class Seen(metric.WireCoverageStatistics):
  def __init__(self):super().__init__();self.current={}
  def evaluate_node(self,n,v):self.current[n]=v;super().evaluate_node(n,v)
 for run in plan['runs']:
  d=ROOT/run['output'];hashes=read(d/'artifact_hashes.json');acts=list(rows(d/'a_actions.jsonl'));overview.append({'id':run['id'],'input':run['input_name'],'actions':len(acts),'overrides':sum(a['phase_changed'] for a in acts)})
  verified[str((d/'a_actions.jsonl').relative_to(ROOT))]=digest(d/'a_actions.jsonl');assert verified[str((d/'a_actions.jsonl').relative_to(ROOT))]==hashes['a_actions.jsonl']
  if not acts:continue
  for name in ['a_atom_catalog.jsonl','queries.jsonl','formal_receipts.jsonl','samples.formal','a_outcomes.independent.jsonl','a_retention.independent.jsonl']:
   path=d/name;verified[str(path.relative_to(ROOT))]=digest(path);assert verified[str(path.relative_to(ROOT))]==hashes[name],name
  stat=Seen();manual=metric.ManualSatisfiesMetric((ROOT/run['input']).read_text(),stat);root=z3.And(manual._solver.assertions());todo=[root];nodes=[];seen=set();variables={}
  while todo:
   e=todo.pop()
   if e.get_id() in seen:continue
   seen.add(e.get_id());nodes.append(e);todo.extend(reversed(e.children()))
   if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED:variables[str(e.decl().name())]=e
  catalog={x['key']:x for x in rows(d/'a_atom_catalog.jsonl')};queries={q['query']:q for q in rows(d/'queries.jsonl')};group=collections.defaultdict(list);retention={(x['query_id'],x['backend_call_id'],x['decision_id']):x for x in rows(d/'a_retention.independent.jsonl')}
  for a in acts:
   key=(run['id'],a['query_id'],a['backend_call_id'],a['context_generation'],a['decision_id']);assert key not in actions_all;actions_all[key]=a;group[a['query_id']].append(a)
  with (d/'samples.formal').open() as inp,(d/'formal_receipts.jsonl').open() as receipts:
   for i,sample in enumerate(metric.parse_samples(inp)):
    rec=json.loads(next(receipts));assignment=dict(sample);assert set(assignment)==set(variables);qa=group[rec['query']] if rec['source']=='CDCL' else []
    before={s['node']:stat._storage[nodes[s['node']].get_id()][:2] for a in qa for s in a['support']};stat.current={};assert manual.count_sample(sample)
    if not qa:continue
    pairs=[(e,z3.IntVal(assignment[n],ctx=metric.CTX) if z3.is_int(e) else z3.BoolVal(bool(assignment[n]),ctx=metric.CTX)) for n,e in variables.items()];pure={}
    for a in qa:
     assert a['coverage_version']==i and rec['coverage_version']==i+1
     q=queries[a['query_id']];backends=q['guidance']['backend_calls'];leaf=next(b for b in backends if b['backend_call_id']==a['backend_call_id']);assert leaf['context_generation']==a['context_generation'];key=(a['query_id'],a['backend_call_id'],a['decision_id']);ret=retention[key]
     for support in a['support']:
      n=support['node'];e=nodes[n];fp=__import__('hashlib').sha256((e.sort().sexpr()+'\n'+e.sexpr()).encode()).hexdigest();fingerprints[str(n)]={'node':n,'sort':e.sort().sexpr(),'sexpr':e.sexpr(),'sha256':fp}
      if n not in pure:
       v=z3.simplify(z3.substitute(e,*pairs));pure[n]=int(z3.is_true(v)) if z3.is_bool(v) and (z3.is_true(v) or z3.is_false(v)) else v.as_long() if z3.is_int_value(v) else None
      seen1,seen0=map(int,before[n]);reached=e.get_id() in stat.current
      for desired,mask in [(1,int(support['desired_one_mask'])),(0,int(support['desired_zero_mask']))]:
       for bit in range(1 if z3.is_bool(e) else 64):
        if not (mask>>bit&1):continue
        missing=bool(((seen0&~seen1) if desired else (seen1&~seen0))>>bit&1);assert missing
        value_hit=None if pure[n] is None else ((pure[n]>>bit)&1)==desired;observation_hit=None if value_hit is None else value_hit and reached
        row={'run_id':run['id'],'query_id':a['query_id'],'backend_call_id':a['backend_call_id'],'context_generation':a['context_generation'],'decision_id':a['decision_id'],'assignment_token':a['assignment_token'],'coverage_version':a['coverage_version'],'formal_index':i,'node':n,'node_sort':e.sort().sexpr(),'node_sha256':fp,'bit':bit,'desired':desired,'phase_changed':a['phase_changed'],'popped':a['trailed_assignment_popped'],'final_internal_assignment':a['final_atom_truth'],'legacy_model_atom_truth':ret['returned_model_atom_truth_via_original_equivalent'],'model_integer_or_bool_value':str(pure[n]) if pure[n] is not None else None,'value_hit':value_hit,'metric_reached':reached,'observation_hit':observation_hit,'was_missing_before_commit':missing,'new_covered':observation_hit and missing if observation_hit is not None else None,'projected_model_complete':True,'model_value_provenance':'old_log_missing','raw_internal_atom':'raw_internal_atom_missing','old_original_node_fingerprint':'not_recorded_reconstructed_from_frozen_formula','leaf_link':'single_success_leaf_inferred' if len(backends)==1 and leaf['result']=='sat' else 'provider_unknown','first_proven_break':'value_not_achieved' if value_hit is False else 'VALUE_HIT_NOT_REACHED' if value_hit and not reached else 'UNKNOWN'}
        output.append(row);event_id=(run['id'],a['query_id'],a['decision_id'],n,bit,desired)
        bool_rules=[r for r in catalog[a['canonical_key']]['rules'] if z3.is_bool(nodes[r['node']])];representative=bool_rules[0];node_val=bool(int(representative['known_one']));native_positive=(bool(representative['phase'])!=a['literal_negated']);desired_original=node_val if a['suggested_phase']==native_positive else not node_val;original_D=nodes[representative['node']] if desired_original else z3.Not(nodes[representative['node']])
        case_data[event_id]={'event':row,'input':run['input'],'input_sha256':run['input_sha256'],'source_output':run['output'],'source_samples_sha256':hashes['samples.formal'],'action':a,'target_expr':e.sexpr(),'target_sort':e.sort().sexpr(),'original_suggested_condition':original_D.sexpr(),'D_provenance':'legacy_catalog_representative_not_independent_actual_atom_proof','assumptions':q['assumptions'],'Q0_policy':'verify_existing_complete_original_model_and_assumptions_then_skip','Q7_policy':'actual_atom_mapping_XOR_only_if_declarations_and_provenance_recovered_else_mapping_unknown','node_fingerprint':fp,'source_receipt':{'formal_index':i,'model_hash':rec['model_hash']}}
 out=OUT/'offline';out.mkdir(parents=True,exist_ok=True)
 with (out/'reclassified_targets.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=output[0]);w.writeheader();w.writerows(output)
 write(out/'node_dictionary.json',fingerprints);write(out/'verified_sources.json',verified);write(out/'overview.json',overview)
 counts=collections.Counter()
 for r in output:
  counts['targets']+=1;counts['value_hit']+=r['value_hit'] is True;counts['metric_reached']+=r['metric_reached'];counts['observation_hit']+=r['observation_hit'] is True;counts['new_covered']+=r['new_covered'] is True;counts[r['first_proven_break']]+=1
 assert len(actions_all)==916 and len(output)==941
 write(out/'summary.json',{'actions':len(actions_all),'overrides':sum(a['phase_changed'] for a in actions_all.values()),'counts':dict(counts),'solver_calls':0,'raw_internal_atom_missing':916,'model_provenance_missing':916,'mapping_independently_proved':False,'official_metric_sha256':digest(metric_path())})
 # Anchors first; then category and lexicographic selection, with atom diversity.
 selected=[];used=set();per_action=collections.Counter();used_atoms=set()
 def take(row):
  eid=(row['run_id'],row['query_id'],row['decision_id'],row['node'],row['bit'],row['desired']);ak=eid[:3]
  if eid in used or per_action[ak]>=2 or len(selected)>=12:return False
  used.add(eid);per_action[ak]+=1;case=case_data[eid];case['case_id']=f'case_{len(selected):02}';selected.append(case);used_atoms.add(case['action']['canonical_key']);return True
 ordered=sorted(output,key=lambda r:(r['run_id'],r['query_id'],r['decision_id'],r['node'],r['bit'],r['desired']))
 for q,decision in [(5,25),(7,30),(11,64)]:
  candidates=[r for r in ordered if r['run_id']=='a_only_v2_time900_04' and r['query_id']==q and r['decision_id']==decision]
  for row in candidates[:2]:take(row)
 categories=[lambda r:r['phase_changed'] and not r['popped'] and r['final_internal_assignment']!=r['legacy_model_atom_truth'],lambda r:r['phase_changed'] and r['popped'],lambda r:not r['phase_changed'] and r['final_internal_assignment']!=r['legacy_model_atom_truth'],lambda r:r['metric_reached'],lambda r:not r['metric_reached']]
 for predicate in categories:
  candidates=[r for r in ordered if predicate(r)]
  fresh=[r for r in candidates if case_data[(r['run_id'],r['query_id'],r['decision_id'],r['node'],r['bit'],r['desired'])]['action']['canonical_key'] not in used_atoms]
  for row in fresh+candidates:
   if take(row):break
 for row in ordered:
  if len(selected)>=12:break
  take(row)
 frozen={'base_commit':'2f839861acf0a8cec78e05dac256b98b0dc30099','selection':'anchors then fixed categories and lexicographic order, maximum two targets per action; distinct atoms preferred','cases':selected,'D1_sessions':6,'D1_wall_seconds':60,'D1_CDCL_caps':{'convert':32,'SMT_random':8,'SMT_real':8},'D2_max_calls':96,'D2_timeout_ms':2000,'mapping_max_atoms_per_instance':8,'mapping_max_calls':16,'D3_max_checkpoints':6,'D3_cells':['N0','A0','N1','A1'],'D3_wall_seconds':5,'D3_conditional':'only after observed non-transmission; scope contract verified or N1/A1 skipped','D3_safe_fallback':'same_query_not_same_state, no fork of watchdog process','formal_900_runs':0,'HighDiv_executions':0,'B_enabled':False,'seed':0}
 exclusive(ROOT/'manifests/round3_semantic_cases.json',frozen);exclusive(OUT/'frozen_cases.json',frozen);print(json.dumps({'actions':len(actions_all),'targets':counts,'selected':len(selected)},default=dict))
if __name__=='__main__':main()
