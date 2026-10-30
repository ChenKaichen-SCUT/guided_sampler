#!/usr/bin/env python3
"""Independent reconstruction from actual layer models and frozen official visitor."""
from semantic_oracle import *
import csv,hashlib
BASE=ROOT/'results/round3_semantics'
def rows(p):
 if p.exists():
  with p.open() as f:
   for l in f:yield json.loads(l)
def main():
 out=BASE/'analysis';out.mkdir(exist_ok=True);chains=[];targets=[];run_summaries=[];errors=[];checkpoints=[]
 for job in read(ROOT/'manifests/round3_d1_plan.json')['jobs']:
  d=ROOT/job['output'];all_rows=list(rows(d/'semantic.jsonl'));snapshots=[r for r in all_rows if r['kind']=='semantic_snapshot'];layers=collections.defaultdict(list)
  for r in all_rows:
   if r['kind']=='model_layer':layers[(r['external_query_id'],r['backend_call_id'],r['layer'])].append(r)
  stat=Witness();manual=metric.ManualSatisfiesMetric((ROOT/job['input']).read_text(),stat);F=z3.And(manual._solver.assertions());nodes,ids=dag(F);vs=variables(nodes);host_nodes=read(d/'original_nodes.json');assert len(nodes)==len(host_nodes)
  orig_decls={n['decl_id']:n for n in host_nodes if n['operator']==z3.Z3_OP_UNINTERPRETED and n['children']==[]}
  formal={};before={};host_original={};seen_masks={r['query_id']:r for r in rows(d/'coverage_snapshots.jsonl')}
  for h in rows(d/'semantic_host.jsonl'):
   if h['kind']=='M_original' and h['source']=='CDCL':host_original[h['query_id']]={v['name']:int(v['value']) for v in h['original_projection']}
  with (d/'samples.formal').open() as f,(d/'formal_receipts.jsonl').open() as recs:
   for i,sample in enumerate(metric.parse_samples(f)):
    rec=json.loads(next(recs));stat.current={};assert manual.count_sample(sample)
    if rec['source']=='CDCL':formal[rec['query']]={'assignment':dict(sample),'reached':set(stat.current),'formal_index':i,'model_hash':rec['model_hash']}
  counts=collections.Counter();atoms=set();unique_targets=set();queries=set()
  for snap in snapshots:
   q,b=snap['external_query_id'],snap['backend_call_id'];counts['snapshots']+=1
   for w in snap['watches']:
    wi=w['watch'];ev=[e for e in snap['events'] if e['watch']==wi];finals=[e for e in ev if e['kind']=='final_internal_assignment'];internal=finals[-1]['truth'] if finals else None;token=finals[-1]['assignment_token'] if finals else w['last_assignment_token'];token_events=[e for e in ev if e['assignment_token']==token];kinds=[e['kind'] for e in token_events];direct=any(k in kinds for k in ['equality_merged','disequality_added','theory_atom_assign_eh','bool_enode_propagated']);relevant=finals[-1]['relevant'] if finals else None
    def layer(name):
     ls=layers.get((q,b,name),[])
     if not ls:return None,None
     vals=[v for v in ls[-1].get('values',[]) if v['watch']==wi];return (vals[-1] if vals else None),ls[-1]
    leaf,lmeta=layer('M_leaf');outer,ometa=layer('M_outer');lt=leaf['truth'] if leaf else None;ot=outer['truth'] if outer else None
    if ometa and ometa['model_provider_backend_id']!=b:errors.append('wrong_model_provider')
    declarations=w['actual_atom']['declarations'];identity_ok=bool(ometa and ometa.get('same_manager')) and all(not x['skolem'] and x['arity']==0 and x['decl_id'] in orig_decls and orig_decls[x['decl_id']]['expr']==x['name'] and orig_decls[x['decl_id']]['sort']==x['range'] for x in declarations)
    raw_expr=None;original_truth=None;formal_truth=None
    if identity_ok:
     raw_expr=parse_expr(w['actual_atom']['expr'],vs)
     if q in host_original:original_truth=exact_value(raw_expr,host_original[q],vs);original_truth=None if original_truth is None else bool(original_truth)
     if q in formal:formal_truth=exact_value(raw_expr,formal[q]['assignment'],vs);formal_truth=None if formal_truth is None else bool(formal_truth)
    if internal is not None and lt is not None and internal!=lt:first='internal_assignment_to_M_leaf'
    elif lt is not None and ot is not None and lt!=ot:first='M_leaf_to_M_outer'
    elif ot is not None and original_truth is not None and ot!=original_truth:first='M_outer_to_M_original'
    elif original_truth is not None and formal_truth is not None and original_truth!=formal_truth:first='M_original_to_M_formal'
    elif leaf and leaf['truth'] is None:first='M_leaf_undef'
    elif ometa is None:first='provider_or_export_missing'
    elif not identity_ok:first='original_mapping_unknown'
    else:first='no_truth_break_observed'
    model_break=first
    initial_assignments=[e for e in ev if e['kind'] in ('assignment_decision','assignment_propagation')]
    initial_token=initial_assignments[0]['assignment_token'] if initial_assignments else None
    original_withdrawn=any(e['kind']=='assignment_withdrawn' and e['assignment_token']==initial_token for e in ev)
    if w['kind']=='suggestion':
     if job['mode']=='observe_trace' and w['effective_phase']!=w['suggested_phase']:first='observe_native_phase_not_suggested_phase'
     elif internal is not None and internal!=w['suggested_phase']:first='suggested_phase_not_retained'
    row={'run_id':job['id'],'query_id':q,'backend_call_id':b,'generation':snap['context_generation'],'decision_id':w['decision_id'],'watch':wi,'kind':w['kind'],'assignment_token':token,'atom_kind':w['atom_kind'],'phase_changed':w.get('phase_changed',False),'native_phase':w.get('native_phase'),'suggested_phase':w.get('suggested_phase'),'effective_phase':w.get('effective_phase'),'final_internal_assignment':internal,'M_leaf':lt,'M_outer':ot,'M_original':original_truth,'M_formal':formal_truth,'same_original_declarations_proved':identity_ok,'final_relevant':relevant,'final_token_direct_transmission':direct,'final_token_enqueued':any(k.startswith('atom_queue_enqueued') for k in kinds),'final_token_consumed':'atom_queue_consumed' in kinds,'overflow':snap['overflow'],'indirect_euf_association':'partial_unknown','first_broken_link':first,'first_model_truth_break':model_break,'initial_assignment_token':initial_token,'original_token_withdrawn':original_withdrawn,'final_token_same_as_initial':token==initial_token,'canonical_key':w.get('canonical_key'),'atom_expr':w['actual_atom']['expr']};chains.append(row);counts[first]+=1
    if w['kind']!='suggestion':continue
    counts['actions']+=1;counts['overrides']+=w['phase_changed'];atoms.add((w['actual_atom']['sort'],w['actual_atom']['expr']));queries.add(q)
    if job['mode']=='apply_trace' and w['phase_changed'] and model_break=='internal_assignment_to_M_leaf' and not direct and not snap['overflow'] and w['is_atom'] and ometa is not None and q in formal and identity_ok:
     checkpoints.append({'run_id':job['id'],'input':job['input'],'query_id':q,'backend_call_id':b,'decision_id':w['decision_id'],'canonical_key':w['canonical_key'],'actual_atom':w['actual_atom'],'native_phase':w['native_phase'],'suggested_phase':w['suggested_phase'],'coverage_version':snap['coverage_version'],'support':w['support'],'interpretation':'no direct transmission of final token observed; indirect association incomplete'})
    for support in w['support']:
     n=support['node'];e=nodes[n]
     for desired,key in [(1,'desired_one_mask'),(0,'desired_zero_mask')]:
      for bit in range(1 if z3.is_bool(e) else 64):
       if not int(support[key])>>bit&1:continue
       value=exact_value(e,formal[q]['assignment'],vs) if q in formal else None;reached=e.get_id() in formal[q]['reached'] if q in formal else None;hit=((value>>bit)&1)==desired if value is not None else None;coverage=seen_masks.get(q);missing=None
       if coverage:
        s0,s1=map(int,coverage['seen_masks'][n]);missing=bool(((s0&~s1) if desired else (s1&~s0))>>bit&1);assert missing
       target={**{k:row[k] for k in ['run_id','query_id','backend_call_id','generation','decision_id','watch','assignment_token','phase_changed','first_broken_link']},'coverage_version':snap['coverage_version'],'node':n,'bit':bit,'desired':desired,'value':value,'value_hit':hit,'metric_reached':reached,'observation_hit':hit and reached if hit is not None else None,'new_covered':bool(hit and reached and missing) if hit is not None else None,'formal_model':q in formal};targets.append(target);counts['target_records']+=1;counts['value_hit']+=hit is True;counts['metric_reached']+=reached is True;counts['observation_hit']+=target['observation_hit'] is True;counts['new_covered']+=target['new_covered'] is True;unique_targets.add((n,bit,desired))
  run_summaries.append({'run_id':job['id'],'counts':dict(counts),'unique_atoms':len(atoms),'unique_targets':len(unique_targets),'action_queries':len(queries),'formal_models':len(list(rows(d/'formal_receipts.jsonl')))})
 for name,rs in [('event_chain.csv',chains),('first_broken_link.csv',chains),('target_chain.csv',targets)]:
  with (out/name).open('x') as f:
   if rs:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 checkpoints=sorted(checkpoints,key=lambda r:(r['run_id'],r['query_id'],r['decision_id']));unique=[];keys=set()
 for c in checkpoints:
  k=(c['run_id'],c['query_id'],c['decision_id'])
  if k not in keys:keys.add(k);unique.append(c)
 write(out/'conditional_checkpoint_candidates.json',unique[:6]);write(out/'chain_summary.json',{'passed':not errors,'errors':errors,'runs':run_summaries,'conditional_checkpoints':len(unique[:6]),'oracle_calls':0,'old_cases_not_rewritten':True});print(json.dumps(run_summaries))
if __name__=='__main__':main()
