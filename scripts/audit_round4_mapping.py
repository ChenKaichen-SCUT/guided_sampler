#!/usr/bin/env python3
"""M opportunities, independently checked before S implementation. No online feedback."""
from semantic_oracle import *
import time
BASE=ROOT/'results/round4';OUT=BASE/'analysis';checks=BASE/'mapping_checks'
def rows(p):return [json.loads(l) for l in p.open()] if p.exists() else []
def main():
 checks.mkdir(exist_ok=False);summaries=[];total_calls=0;unique=set();audit_rows=[];cases=[]
 for job in read(ROOT/'manifests/round4_short_plan.json')['jobs']:
  if job['stage']!='M':continue
  d=BASE/'runs'/job['id'];assert read(d/'target_audit.json')['passed'];assert read(d/'terminal.json')['exit_code']==0
  qs={r['query']:r for r in rows(d/'queries.jsonl')};states={r['query_id']:r for r in rows(d/'coverage_snapshots.jsonl')};cat={r['key']:r for r in rows(d/'a_atom_catalog.jsonl')};funnel=collections.Counter()
  for b in rows(d/'a_backend_calls.jsonl'):
   if 'funnel' in b:funnel.update(b['funnel'])
  semantic=rows(d/'semantic.jsonl');outer={(r['external_query_id'],r['backend_call_id']):r for r in semantic if r['kind']=='model_layer' and r['layer']=='M_outer'};snapshots=[r for r in semantic if r['kind']=='semantic_snapshot'];originals={n['decl_id']:n for n in read(d/'original_nodes.json') if n['operator']==z3.Z3_OP_UNINTERPRETED and not n['children']}
  stat=Witness();manual=metric.ManualSatisfiesMetric((ROOT/job['input']).read_text(),stat);F=z3.And(manual._solver.assertions());nodes,_=dag(F);vs=variables(nodes);demand_events=positive_score=0
  for snap in snapshots:
   q=snap['external_query_id'];query=qs[q];assert snap['coverage_version']==states[q]['coverage_version'];assert query['guidance']['suggestions']<=4
   for rec in snap['encounters']:
    if not rec.get('new_mapping_rule'):continue
    actual=rec['actual_atom'];entry=cat[rec['canonical_key']];mask=states[q]['seen_masks'];scores=[0,0];targets=[set(),set()];single=set()
    for rule in entry['rules']:
     n=rule['node'];s0,s1=map(int,mask[n]);w1=s0&~s1;w0=s1&~s0;one=int(rule['known_one'])&w1;zero=int(rule['known_zero'])&w0
     for bit in range(1 if z3.is_bool(nodes[n]) else 64):
      if (w1|w0)>>bit&1:single.add((n,bit,int(bool(w1>>bit&1))))
      if one>>bit&1:targets[rule['phase']].add((n,bit,1))
      if zero>>bit&1:targets[rule['phase']].add((n,bit,0))
    scores=list(map(len,targets));demand_events+=bool(single and snap['coverage_version']);positive_score+=bool(scores[0]!=scores[1] and snap['coverage_version']);meta=outer.get((q,snap['backend_call_id']));identity=bool(meta and meta['same_manager']) and all(not x['skolem'] and x['arity']==0 and x['decl_id'] in originals and originals[x['decl_id']]['expr']==x['name'] and originals[x['decl_id']]['sort']==x['range'] for x in actual['declarations'])
    row={'run_id':job['id'],'query_id':q,'decision_id':rec['decision_id'],'coverage_version':snap['coverage_version'],'new_mapping_rule':rec['new_mapping_rule'],'actual_atom':actual,'originals':rec['originals'],'canonical_negated':rec['canonical_negated'],'current_single_sided_targets':sorted(single),'positive_support_targets':list(map(sorted,targets)),'raw_positive_scores_before_old_attempted_filter':scores,'declaration_identity_proved':identity,'native_selected':True,'unassigned_at_callback':True,'equivalence_check':'not_selected_within_fixed_16_cap'}
    if identity:
     original=sorted(rec['originals'],key=lambda x:x['original_node_id'])[0];n=original['original_node_id'];key=(job['instance'],actual['expr'],n,rec['canonical_negated'],original['canonical_negated'])
     if key not in unique and len(cases)<16:unique.add(key);cases.append((row,n,original,vs,nodes))
    else:row['equivalence_check']='unknown_original_declaration_identity'
    audit_rows.append(row)
  summaries.append({'id':job['id'],'summary':read(d/'summary.json'),'funnel':dict(funnel),'new_mapping_records':sum(r['run_id']==job['id'] for r in audit_rows),'independently_reconstructed_single_sided_encounters':demand_events,'raw_support_nontie_before_attempted_filter':positive_score,'target_audit':read(d/'target_audit.json')['counts']})
 # Selection written before independent answers; no target-result-dependent selection.
 exclusive(checks/'selected.json',[{'run_id':r['run_id'],'query_id':r['query_id'],'decision_id':r['decision_id'],'expr':r['actual_atom']['expr'],'original_node':n} for r,n,o,v,ns in cases])
 for i,(r,n,original,vs,nodes) in enumerate(cases):
  actual=parse_expr(r['actual_atom']['expr'],vs);expected=nodes[n] if r['canonical_negated']==original['canonical_negated'] else z3.Not(nodes[n]);s=z3.Solver(ctx=metric.CTX);s.set(timeout=2000,random_seed=0);s.add(actual!=expected);p=checks/f'case_{i:02}';p.with_suffix('.smt2').write_text(s.to_smt2());exclusive(p.with_suffix('.attempt.json'),{'timeout_ms':2000,'seed':0,'formula_background':False});t=time.monotonic();answer=s.check();total_calls+=1;result={'result':str(answer),'seconds':time.monotonic()-t,'reason_unknown':s.reason_unknown() if answer==z3.unknown else '', 'equivalence_scope':'unrestricted_original_declaration_space'};write(p.with_suffix('.result.json'),result);r['equivalence_check']=str(answer);assert answer!=z3.sat,'Unsound new mapping counterexample'
 with (checks/'opportunities.jsonl').open('x') as f:
  for r in audit_rows:f.write(json.dumps(r)+'\n')
 result={'passed':True,'stage':'M','sessions':summaries,'mapping_check_calls':total_calls,'mapping_proofs':sum(r['equivalence_check']=='unsat' for r in audit_rows),'post_first_model_new_mapping_demand_events':sum(s['independently_reconstructed_single_sided_encounters'] for s in summaries),'expanded_rule_set':False,'expanded_window':False,'S_implemented_before_M_audit':False,'interpretation':'raw support opportunities are prior to old attempted-target filtering; actual advice and hits come from frozen action/official target logs'};write(OUT/'M_summary.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
