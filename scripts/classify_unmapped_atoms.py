#!/usr/bin/env python3
"""At most 16 independent mapping checks; no invented auxiliary declarations."""
from semantic_oracle import *
import time
BASE=ROOT/'results/round3_semantics'
def main():
 out=BASE/'mapping';out.mkdir(exist_ok=False);result=[];calls=0
 for job in read(ROOT/'manifests/round3_d1_plan.json')['jobs']:
  if job['instance'] not in ('SMT_random','SMT_real') or job['mode']!='observe_trace':continue
  d=ROOT/job['output'];atoms=[json.loads(l) for l in (d/'atom_dictionary.jsonl').read_text().splitlines() if json.loads(l)['kind']=='unmapped'];assert len(atoms)<=8
  manual=metric.ManualSatisfiesMetric((ROOT/job['input']).read_text(),Witness());F=z3.And(manual._solver.assertions());nodes,ids=dag(F);vs=variables(nodes);host_nodes=read(d/'original_nodes.json');decls={n['decl_id']:n for n in host_nodes if n['operator']==z3.Z3_OP_UNINTERPRETED};model_records=list(map(json.loads,(d/'model_stages.jsonl').read_text().splitlines()));converters=[r for r in model_records if r['kind'] in ('converter_chain','converter_definitions')]
  # Independent Z3 arithmetic rewriting only selects a candidate; XOR checking
  # below, not string equality or the sampler's canonicalizer, supplies proof.
  candidates=collections.defaultdict(list)
  for n,e in enumerate(nodes):
   if z3.is_bool(e) and e.num_args() and e.decl().kind() not in (z3.Z3_OP_AND,z3.Z3_OP_OR,z3.Z3_OP_ITE):candidates[z3.simplify(e,arith_lhs=True,som=True).sexpr()].append(n)
  for i,a in enumerate(atoms):
   atom=a['actual_atom'];row={'instance':job['instance'],'ordinal':i,'query_id':a['external_query_id'],'backend_call_id':a['backend_call_id'],'decision_id':a['decision_id'],'actual_atom':atom,'canonical_key':a['canonical_key'],'classification':'insufficient_evidence','mapping_result':'mapping_unknown','solver_call':False}
   chain=[c for c in converters if c['external_query_id']==a['external_query_id'] and c['model_provider_backend_id']==a['backend_call_id']];row['actual_converter_chain']=chain;row['converter_overflow']=any(c['overflow'] for c in chain)
   valid=any(r['kind']=='model_layer' and r['layer']=='M_outer' and r['external_query_id']==a['external_query_id'] and r['backend_call_id']==a['backend_call_id'] and r.get('same_manager') for r in model_records) and all(not x['skolem'] and x['arity']==0 and x['decl_id'] in decls and decls[x['decl_id']]['expr']==x['name'] and decls[x['decl_id']]['sort']==x['range'] for x in atom['declarations'])
   row['original_declaration_identity_verified']=valid
   if not valid:
    row['classification']='auxiliary_Bool_or_generated_declaration' if atom['declarations'] and all(x['range']=='Bool' for x in atom['declarations'] if x['decl_id'] not in decls) else 'insufficient_evidence'
    row['reason']='Actual declaration identity not fully present in original manager; no name-based reconstruction.'
   else:
    actual=parse_expr(atom['expr'],vs);norm=z3.simplify(actual,arith_lhs=True,som=True).sexpr();matches=candidates.get(norm,[]);negated=False
    if not matches:matches=candidates.get(z3.simplify(z3.Not(actual),arith_lhs=True,som=True).sexpr(),[]);negated=True
    if matches:
     n=min(matches);original=z3.Not(nodes[n]) if negated else nodes[n];s=z3.Solver(ctx=metric.CTX);s.set(timeout=2000,random_seed=0);s.add(z3.Xor(actual,original));label=job['instance']+'_'+str(i);(out/(label+'.smt2')).write_text(s.to_smt2());t=time.monotonic();r=s.check();seconds=time.monotonic()-t;calls+=1;assert calls<=16;row.update(candidate_node=n,candidate_expr=original.sexpr(),solver_call=True,mapping_result=str(r),seconds=seconds,timeout_ms=2000,reason_unknown=s.reason_unknown() if r==z3.unknown else '')
     row['classification']='original_atom_normalization_omission' if r==z3.unsat else 'insufficient_evidence'
     if r==z3.sat:row['counterexample']=s.model().sexpr()
    else:
     # Restore only actual, same-manager, acyclic definitions of eliminated
     # original declarations. Never invent a same-named auxiliary variable.
     defs={};origins={};bad=set();raw_ids={v['decl_id'] for v in atom['declarations']};manager=atom['manager_identity']
     for record in chain:
      if record['kind']!='converter_definitions':continue
      for entry in record['entries']:
       did=entry['decl_id'];definition=entry.get('definition')
       if entry['instruction']!='add' or did in raw_ids or did not in decls or entry['manager_identity']!=manager or entry['skolem'] or entry['arity'] or not definition:continue
       if not all(not v['skolem'] and v['arity']==0 and v['decl_id'] in decls and decls[v['decl_id']]['expr']==v['name'] and decls[v['decl_id']]['sort']==v['range'] for v in definition['declarations']):continue
       term=parse_expr(definition['expr'],vs) if entry['range']=='Bool' else parse_expr('(>= '+definition['expr']+' 0)',vs).arg(0) if entry['range']=='Int' else None
       if term is None:continue
       if did in defs and not z3.eq(defs[did],term):bad.add(did)
       defs[did]=term;origins[did]=entry['origin']
     for did in bad:defs.pop(did,None)
     name_ids={n['expr']:did for did,n in decls.items()};resolved={};pending=dict(defs)
     while pending:
      progress=False
      for did,term in list(pending.items()):
       used={name_ids[str(v.decl().name())] for v in dag(term)[0] if z3.is_const(v) and v.decl().kind()==z3.Z3_OP_UNINTERPRETED and str(v.decl().name()) in name_ids}
       if used & set(pending):continue
       pairs=[(vs[decls[k]['expr']],v) for k,v in resolved.items()];resolved[did]=z3.simplify(z3.substitute(term,*pairs)) if pairs else term;del pending[did];progress=True
      if not progress:break
     subs=[(vs[decls[k]['expr']],v) for k,v in resolved.items()];restored=[]
     for n,e in enumerate(nodes):
      if not z3.is_bool(e) or e.decl().kind() in (z3.Z3_OP_AND,z3.Z3_OP_OR,z3.Z3_OP_ITE,z3.Z3_OP_TRUE,z3.Z3_OP_FALSE):continue
      substituted=z3.substitute(e,*subs) if subs else e
      if z3.eq(substituted,e):continue
      positive=z3.simplify(substituted,arith_lhs=True,som=True).sexpr();negative=z3.simplify(z3.Not(substituted),arith_lhs=True,som=True).sexpr()
      if norm in (positive,negative):restored.append((n,norm==negative))
     if restored:
      n,neg=min(restored);original=z3.Not(nodes[n]) if neg else nodes[n];background=[v==term for v,term in subs];s=z3.Solver(ctx=metric.CTX);s.set(timeout=2000,random_seed=0);s.add(*background,z3.Xor(actual,original));label=job['instance']+'_'+str(i);(out/(label+'.smt2')).write_text(s.to_smt2());t=time.monotonic();r=s.check();seconds=time.monotonic()-t;calls+=1;assert calls<=16
      row.update(candidate_node=n,candidate_expr=original.sexpr(),solver_call=True,mapping_result=str(r),seconds=seconds,timeout_ms=2000,restoration_definitions=[{'decl_id':k,'name':decls[k]['expr'],'definition':v.sexpr(),'origin':origins[k]} for k,v in resolved.items()],background_satisfiable_by_acyclic_elimination=True,proof_scope='actual converter definition space; not equivalence for every unrestricted original assignment',reason_unknown=s.reason_unknown() if r==z3.unknown else '')
      row['classification']='actual_preprocessing_substitution' if r==z3.unsat else 'insufficient_evidence'
      if r==z3.sat:row['counterexample']=s.model().sexpr()
     else:
      row['classification']='preprocessing_or_theory_generated_not_independently_resolved';row['reason']='No candidate after recoverable acyclic actual substitutions; missing, cyclic, or truncated definitions are not reconstructed by names.';row['recoverable_definition_count']=len(resolved);row['cyclic_or_unresolved_definition_count']=len(pending)
   result.append(row)
 with (out/'unmapped_examples.jsonl').open('x') as f:
  for r in result:f.write(json.dumps(r)+'\n')
 write(out/'summary.json',{'representatives':len(result),'solver_calls':calls,'maximum_calls':16,'classes':dict(collections.Counter(r['classification'] for r in result)),'no_active_demand_note':'These examples were selected only when the key was absent from the A index; present-key/no-demand events are separately counted in backend funnels.'});print(json.dumps({'representatives':len(result),'calls':calls}))
if __name__=='__main__':main()
