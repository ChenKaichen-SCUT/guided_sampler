#!/usr/bin/env python3
from semantic_oracle import *
import csv,hashlib
BASE=ROOT/'results/round3_semantics';OUT=BASE/'micro'
def main():
 summary=read(OUT/'summary.json');plan=read(ROOT/'manifests/round3_d3_plan.json');contexts={};rows=[];errors=[]
 for c in plan['cases']:
  if c['input'] not in contexts:
   stat=Witness();manual=metric.ManualSatisfiesMetric((ROOT/c['input']).read_text(),stat);F=z3.And(manual._solver.assertions());nodes,ids=dag(F);vs=variables(nodes);contexts[c['input']]=(stat,manual,F,nodes,vs)
  stat,manual,F,nodes,vs=contexts[c['input']];A=[parse_expr(a,vs) for a in c['query']['assumptions']];cell_rows=[]
  for cell in plan['cells']:
   d=OUT/'runs'/c['case_id']/cell;terminal=read(d/'terminal.json');r=read(d/'result.json') if (d/'result.json').exists() else {'result':'unknown','checkpoint_seen':None,'reason_unknown':'external_deadline_missing_boundary_record'};cp=r.get('checkpoint');row={'checkpoint_id':c['case_id'],'historical_query':c['query_id'],'historical_decision':c['decision_id'],'cell':cell,'result':r['result'],'checkpoint_seen':r['checkpoint_seen'],'reason_unknown':r.get('reason_unknown',''),'process_seconds':terminal['parent_seconds'],'exit_code':terminal['exit_code'],'state_relation':'same_query_not_same_state','activation':cp['activation'] if cp else False,'phase_changed':cp['phase_changed'] if cp else False,'propagated_before_test_decision':cp['propagated_before_test_decision'] if cp else None,'conflict_before_test_decision':cp['conflict_before_test_decision'] if cp else None,'value_hits':None,'observation_hits':None,'new_target_coverage':None,'actual_atom_truth':None,'official_original_F_legal':None,'original_Aq_legal':None,'comparison_limit':'historical state not cloned','checkpoint_status':'observed' if cp else ('not_encountered_in_completed_run' if (d/'result.json').exists() else 'unknown_missing_boundary_record'),'deadline_overrun':terminal['deadline_overrun']}
   semantic=[json.loads(line) for line in (d/'semantic.jsonl').open()] if (d/'semantic.jsonl').exists() else []
   snapshots=[v for v in semantic if v['kind']=='semantic_snapshot'];layers=[v for v in semantic if v['kind']=='model_layer']
   for snap in snapshots:
    for watch in snap['watches']:
     if watch['kind']!='D3_checkpoint':continue
     ev=[v for v in snap['events'] if v['watch']==watch['watch']];assign=[v for v in ev if v['kind'] in ('assignment_decision','assignment_propagation')];final=[v for v in ev if v['kind']=='final_internal_assignment'];token=final[-1]['assignment_token'] if final else watch['last_assignment_token'];kinds=[v['kind'] for v in ev if v['assignment_token']==token]
     row.update(semantic_overflow=snap['overflow'],final_token=token,final_internal_assignment=final[-1]['truth'] if final else None,final_relevant=final[-1]['relevant'] if final else None,initial_token_withdrawn=any(v['kind']=='assignment_withdrawn' and assign and v['assignment_token']==assign[0]['assignment_token'] for v in ev),final_token_direct_transmission=any(k in kinds for k in ['equality_merged','disequality_added','theory_atom_assign_eh','bool_enode_propagated']),theory_delivery_events=sum(v['kind'] in ('theory_equality_delivered','theory_disequality_delivered') for v in ev))
     for layer in layers:
      if layer['backend_call_id']!=snap['backend_call_id']:continue
      vals=[v for v in layer['values'] if v['watch']==watch['watch']]
      if vals:row[layer['layer']]=vals[-1]['truth']
   if cp:
    assert cp['native_var']==cp['actual_var'] and cp['assertions_before']==cp['assertions_after'];assert cp['activation']==cell.endswith('1');row.update(actual_decision=cp['actual_decision_id'],native_phase=cp['native_phase'],suggested_phase=cp['suggested_phase'],effective_phase=cp['effective_phase'],relevant_before=cp['relevant_before'],relevant_after=cp['relevant_after_activation'],scope_level=cp['scope_level'],trail_before=cp['trail_size_before'],bool_vars_before=cp['bool_vars_before'],bool_vars_after=cp['bool_vars_after'],process_threads=cp['process_thread_count'],activation_seconds=cp['activation_and_native_propagation_seconds'])
    for label,fn,field in [('native','native_decisions.txt','native_trace_bytes_before'),('rng','rng.txt','rng_trace_bytes_before')]:
     data=(d/fn).read_bytes()[:cp[field]] if (d/fn).exists() else b'';row[label+'_prefix_sha256']=hashlib.sha256(data).hexdigest()
   if r['result']=='sat' and terminal['exit_code']==0:
    assignment={k:int(v) for k,v in r['projection'].items()};assert exact_value(F,assignment,vs)==1 and exact_value(z3.And(*A) if A else z3.BoolVal(True,ctx=metric.CTX),assignment,vs)==1;stat.current={};assert manual.count_sample(list(assignment.items()));row['official_original_F_legal']=True;row['original_Aq_legal']=True;row['actual_atom_truth']=bool(exact_value(parse_expr(c['actual_atom']['expr'],vs),assignment,vs));vh=oh=0;target_rows=[]
    for support in c['support']:
     n=support['node'];e=nodes[n];value=exact_value(e,assignment,vs);reached=e.get_id() in stat.current
     for desired,key in [(1,'desired_one_mask'),(0,'desired_zero_mask')]:
      for bit in range(1 if z3.is_bool(e) else 64):
       if int(support[key])>>bit&1:hit=((value>>bit)&1)==desired;vh+=hit;oh+=hit and reached;target_rows.append({'node':n,'bit':bit,'desired':desired,'value_hit':hit,'metric_reached':reached,'observation_hit':hit and reached})
    row['value_hits']=vh;row['observation_hits']=oh;row['new_target_coverage']=oh;write(d/'independent_targets.json',{'F_legal':True,'Aq_legal':True,'formal_sample':False,'targets':target_rows})
   elif r['result']=='sat':row['comparison_limit']='SAT output not accepted after abnormal or late process termination'
   cell_rows.append(row);rows.append(row)
  seen=[r for r in cell_rows if r['checkpoint_seen']]
  if len(seen)==4:
   for field in ['native_prefix_sha256','rng_prefix_sha256','actual_decision','native_phase','trail_before','bool_vars_before']:
    if len({r[field] for r in seen})!=1:
     for r in cell_rows:r['comparison_limit']='fresh-query prefixes differ; not a controlled state comparison'
 with (BASE/'analysis/cause_matrix.csv').open('x') as f:
  fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 result={'passed':not errors,'errors':errors,'real_runs':len(rows),'checkpoint_seen':sum(r['checkpoint_seen'] is True for r in rows),'not_reproduced':sum(r['checkpoint_seen'] is False for r in rows),'checkpoint_unknown_missing_boundary':sum(r['checkpoint_seen'] is None for r in rows),'actual_phase_changes':sum(r['phase_changed'] for r in rows),'local_activations':sum(r['activation'] for r in rows),'value_hits':sum(r['value_hits'] or 0 for r in rows),'observation_hits':sum(r['observation_hits'] or 0 for r in rows),'max_deadline_overrun':max(r['deadline_overrun'] for r in rows),'counter_scope':'actual changes and activation counts are lower bounds over cells with a completed boundary record','same_state':False,'results':dict(collections.Counter(r['result'] for r in rows))};write(OUT/'audit_summary.json',result);print(json.dumps(result))
if __name__=='__main__':main()
