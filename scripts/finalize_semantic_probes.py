#!/usr/bin/env python3
from common import *
from semantic_oracle import metric,z3,dag
from finalize_round2_stream import finalize
from evaluate_round2_official import evaluate
from audit_round2_targets import audit
BASE=ROOT/'results/round3_semantics'
for job in read(ROOT/'manifests/round3_d1_plan.json')['jobs']:
 d=ROOT/job['output'];assert read(d/'terminal.json')['exit_code']==0
 finalize(d,60,None);assert evaluate(d,ROOT/job['input'])=={'official_exit':0,'exact_exit':0};assert audit(d,ROOT/job['input'])['passed']
 manual=metric.ManualSatisfiesMetric((ROOT/job['input']).read_text(),metric.WireCoverageStatistics());nodes,_=dag(z3.And(manual._solver.assertions()));catalog={r['key']:r['rules'] for r in map(json.loads,(d/'a_atom_catalog.jsonl').read_text().splitlines())}
 # Split the bounded native records into directly reviewable evidence channels.
 with (d/'semantic_events.jsonl').open('x') as events,(d/'atom_dictionary.jsonl').open('x') as atoms,(d/'model_stages.jsonl').open('x') as models:
  if (d/'semantic.jsonl').exists():
   for line in (d/'semantic.jsonl').open():
    row=json.loads(line)
    if row['kind']=='semantic_snapshot':
     base={k:row[k] for k in ['run_id','external_query_id','backend_call_id','context_generation','coverage_version']}
     for event in row['events']:events.write(json.dumps({**base,**event,'overflow':row['overflow']})+'\n')
     for atom in row['watches']:
      rules=[]
      for rule in catalog.get(atom.get('canonical_key'),[]):
       n=rule['node'];rules.append({**rule,'original_expression':nodes[n].sexpr(),'original_sort':nodes[n].sort().sexpr(),'rule_source':'Bool_self' if z3.is_bool(nodes[n]) else 'explicit_equality_to_constant_true_supports_integer_bits'})
      atoms.write(json.dumps({**base,**atom,'overflow':row['overflow'],'original_rules':rules,'raw_expression':atom['actual_atom']['expr'],'normal_form_key':atom.get('canonical_key')})+'\n')
    else:models.write(line)
 print(job['id'],'finalized and officially scored',flush=True)
