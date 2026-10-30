#!/usr/bin/env python3
"""Same sixteen frozen representatives, actual definitions + equality expansion.
The first pass made zero solver calls. This pass still permits one 2s XOR
check per representative, never a new representative or a sampler execution.
"""
from semantic_oracle import *
import time,shutil
OUT=ROOT/'results/round3_semantics/mapping'
def normal(e):return z3.simplify(e,arith_lhs=True,som=True,eq2ineq=True,elim_and=True,sort_disjunctions=True).sexpr()
def main():
 assert read(OUT/'summary.json')['solver_calls']==0
 previous=OUT/'initial_no_checks';previous.mkdir(exist_ok=False)
 for name in ['summary.json','unmapped_examples.jsonl']:shutil.move(OUT/name,previous/name)
 old=[json.loads(l) for l in (previous/'unmapped_examples.jsonl').read_text().splitlines()];contexts={};cache={};calls=0;rows=[]
 jobs={j['instance']:j for j in read(ROOT/'manifests/round3_d1_plan.json')['jobs'] if j['mode']=='observe_trace'}
 for row in old:
  instance=row['instance'];job=jobs[instance];d=ROOT/job['output']
  if instance not in contexts:
   manual=metric.ManualSatisfiesMetric((ROOT/job['input']).read_text(),Witness());F=z3.And(manual._solver.assertions());nodes,ids=dag(F);vs=variables(nodes);decls={n['decl_id']:n for n in read(d/'original_nodes.json') if n['operator']==z3.Z3_OP_UNINTERPRETED};native={ (a['external_query_id'],a['backend_call_id'],a['decision_id']):a for a in map(json.loads,(d/'atom_dictionary.jsonl').read_text().splitlines())};contexts[instance]=(nodes,vs,decls,native)
  nodes,vs,decls,native=contexts[instance];atom=row['actual_atom'];watch=native[(row['query_id'],row['backend_call_id'],row['decision_id'])];row['actual_native_kind']=watch['atom_kind'];row['native_is_atom']=watch['is_atom'];row['mapping_result']='mapping_unknown';row['solver_call']=False
  if not row['original_declaration_identity_verified']:rows.append(row);continue
  actual=parse_expr(atom['expr'],vs);raw_ids={v['decl_id'] for v in atom['declarations']};entries=[e for c in row['actual_converter_chain'] if c['kind']=='converter_definitions' for e in c['entries']];lhs={e['decl_id'] for e in entries if e['instruction']=='add'};key=(instance,row['query_id'],row['backend_call_id'],tuple(sorted(raw_ids&lhs)))
  if key not in cache:
   defs={};origins={};bad=set();manager=atom['manager_identity']
   for entry in entries:
    did=entry['decl_id'];definition=entry.get('definition')
    if entry['instruction']!='add' or did in raw_ids or did not in decls or entry['manager_identity']!=manager or entry['skolem'] or entry['arity'] or not definition:continue
    if not all(not v['skolem'] and not v['arity'] and v['decl_id'] in decls and decls[v['decl_id']]['expr']==v['name'] and decls[v['decl_id']]['sort']==v['range'] for v in definition['declarations']):continue
    term=parse_expr(definition['expr'],vs) if entry['range']=='Bool' else parse_expr('(>= '+definition['expr']+' 0)',vs).arg(0) if entry['range']=='Int' else None
    if term is None:continue
    if did in defs and not z3.eq(defs[did],term):bad.add(did)
    defs[did]=term;origins[did]=entry['origin']
   for did in bad:defs.pop(did,None)
   name_ids={n['expr']:did for did,n in decls.items()};resolved={};pending=dict(defs)
   def used(e):return {name_ids[str(v.decl().name())] for v in dag(e)[0] if z3.is_const(v) and v.decl().kind()==z3.Z3_OP_UNINTERPRETED and str(v.decl().name()) in name_ids}
   while pending:
    progressed=False
    for did,term in list(pending.items()):
     deps=used(term)
     if deps&set(pending):continue
     pairs=[(vs[decls[k]['expr']],resolved[k]) for k in deps if k in resolved];resolved[did]=z3.simplify(z3.substitute(term,*pairs)) if pairs else term;del pending[did];progressed=True
    if not progressed:break
   candidates=collections.defaultdict(list);direct=collections.defaultdict(list)
   for n,e in enumerate(nodes):
    if not z3.is_bool(e) or z3.is_and(e) or e.decl().kind() in (z3.Z3_OP_TRUE,z3.Z3_OP_FALSE) or z3.is_or(e) and e.num_args()>8:continue
    direct[normal(e)].append((n,False));direct[normal(z3.Not(e))].append((n,True));deps=used(e);pairs=[(vs[decls[k]['expr']],resolved[k]) for k in deps if k in resolved];changed=z3.substitute(e,*pairs) if pairs else e
    candidates[normal(changed)].append((n,False));candidates[normal(z3.Not(changed))].append((n,True))
   cache[key]=(resolved,origins,candidates,direct)
  resolved,origins,candidates,direct=cache[key];norm=normal(actual);matches=direct.get(norm,[]);restored=False
  if not matches:matches=candidates.get(norm,[]);restored=True
  row['classification']='defined_Boolean_gate_without_proved_original_correspondence' if not watch['is_atom'] else 'derived_arithmetic_bound_origin_not_proved';row['reason']='Actual gate/bound kind is observed; full original correspondence requires the independent XOR proof.'
  if matches:
   n,neg=min(matches);original=z3.Not(nodes[n]) if neg else nodes[n];background=[vs[decls[k]['expr']]==term for k,term in resolved.items()] if restored else [];solver=z3.Solver(ctx=metric.CTX);solver.set(timeout=2000,random_seed=0);solver.add(*background,z3.Xor(actual,original));label=instance+'_'+str(row['ordinal']);(OUT/(label+'.smt2')).write_text(solver.to_smt2());exclusive(OUT/(label+'.attempt.json'),{'timeout_ms':2000,'attempt':1,'representative_ordinal':row['ordinal']});t=time.monotonic();r=solver.check();seconds=time.monotonic()-t;calls+=1;assert calls<=16
   row.update(solver_call=True,mapping_result=str(r),mapping_seconds=seconds,timeout_ms=2000,candidate_node=n,candidate_expression=original.sexpr(),restored_actual_definitions=restored,background_satisfiable_by_acyclic_elimination=True,proof_scope='actual converter definition space' if restored else 'unrestricted original declaration space',reason_unknown=solver.reason_unknown() if r==z3.unknown else '')
   if r==z3.unsat:row['classification']='Boolean_gate_after_actual_preprocessing' if not watch['is_atom'] else 'original_atom_after_actual_preprocessing' if restored else 'original_atom_normalization_omission'
   if r==z3.sat:row['counterexample']=solver.model().sexpr()
   if restored:row['restoration_definitions']=[{'decl_id':k,'name':decls[k]['expr'],'definition':v.sexpr(),'origin':origins[k]} for k,v in resolved.items()]
   write(OUT/(label+'.result.json'),{k:v for k,v in row.items() if k not in ('actual_converter_chain',)})
  rows.append(row);print(instance,row['ordinal'],row['classification'],row['mapping_result'],flush=True)
 with (OUT/'unmapped_examples.jsonl').open('x') as f:
  for r in rows:f.write(json.dumps(r)+'\n')
 write(OUT/'summary.json',{'representatives':len(rows),'solver_calls':calls,'initial_pass_calls':0,'maximum_calls':16,'classes':dict(collections.Counter(r['classification'] for r in rows)),'native_gates':sum(not r['native_is_atom'] for r in rows),'native_arithmetic_atoms':sum(r['native_is_atom'] for r in rows),'selection_changed':False,'all_solver_calls_preserved':True})
if __name__=='__main__':main()
