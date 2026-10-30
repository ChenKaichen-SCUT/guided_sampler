#!/usr/bin/env python3
"""D2: at most 12 x 8 offline checks, fixed 2s, never fed to sampler."""
from semantic_oracle import *
import time
OUT=ROOT/'results/round3_semantics/oracle'
def main():
 plan=read(ROOT/'manifests/round3_semantic_cases.json');OUT.mkdir(parents=True,exist_ok=True);summary=[];calls=0;contexts={}
 if not (OUT/'STARTED.json').exists():exclusive(OUT/'STARTED.json',{'plan_sha256':digest(ROOT/'manifests/round3_semantic_cases.json'),'max_calls':96,'timeout_ms':2000,'Q7_choice':'mapping XOR only with recovered actual declarations; old actual atoms absent => skip'})
 for case in plan['cases']:
  d=OUT/case['case_id'];d.mkdir(exist_ok=True)
  if all((d/(q+'.result.json')).exists() for q in ['Q0','Q1','Q2','Q3','Q4','Q5','Q6','Q7']):
   summary.extend(read(d/(q+'.result.json')) for q in ['Q1','Q2','Q3','Q4','Q5','Q6']);calls+=6;continue
  p=ROOT/case['input'];assert digest(p)==case['input_sha256']
  if case['input'] not in contexts:
   stat=Witness();manual=metric.ManualSatisfiesMetric(p.read_text(),stat);F=z3.And(manual._solver.assertions());nodes,reaches=reach_all(F);vs=variables(nodes);contexts[case['input']]=(stat,manual,F,nodes,reaches,vs)
  stat,manual,F,nodes,reaches,vs=contexts[case['input']];e=nodes[case['event']['node']];assert e.sexpr()==case['target_expr'];V=value_condition(e,case['event']['bit'],case['event']['desired']);R=reaches[case['event']['node']];A=[parse_expr(a,vs) for a in case['assumptions']];D=parse_expr(case['original_suggested_condition'],vs)
  source=ROOT/case['source_output'];index=case['source_receipt']['formal_index'];saved=None
  with (source/'samples.formal').open() as f:
   for i,sample in enumerate(metric.parse_samples(f)):
    if i==index:saved=dict(sample);break
  assert saved is not None and set(saved)==set(vs) and exact_value(z3.And(F,*A),saved,vs)==1
  write(d/'Q0.result.json',{'status':'sat_existing_model_verified','solver_call':False,'formal_index':index,'F_and_assumptions_verified':True});write(d/'Q0.model.json',saved)
  checks={'Q1':[V],'Q2':[R,V],'Q3':A+[R,V],'Q4':A+[D],'Q5':A+[D,z3.Not(V)],'Q6':A+[D,z3.Not(R)]};answers={}
  for label,cs in checks.items():
   if (d/(label+'.result.json')).exists():
    old=read(d/(label+'.result.json'));summary.append(old);answers[label]=old['result'];calls+=int(old['solver_call']);continue
   if (d/(label+'.attempt.json')).exists():raise RuntimeError('Uncompleted prior solver attempt cannot be repeated')
   exclusive(d/(label+'.attempt.json'),{'timeout_ms':2000,'attempt':1,'case_id':case['case_id'],'query':label})
   solver=z3.Solver(ctx=metric.CTX);solver.set(timeout=2000,random_seed=0);solver.add(F,*cs);(d/(label+'.smt2')).write_text(solver.to_smt2());start=time.monotonic();answer=solver.check();elapsed=time.monotonic()-start;calls+=1;assert calls<=96
   row={'case_id':case['case_id'],'query':label,'result':str(answer),'solver_call':True,'seconds':elapsed,'timeout_ms':2000,'timeout_overrun':max(0,elapsed-2),'reason_unknown':solver.reason_unknown() if answer==z3.unknown else '', 'D_provenance':case['D_provenance'],'actual_mapping_proved':False};answers[label]=str(answer)
   if answer==z3.sat:
    model=solver.model();assignment={name:(model.eval(v,model_completion=True).as_long() if z3.is_int(v) else int(z3.is_true(model.eval(v,model_completion=True)))) for name,v in vs.items()};assert exact_value(z3.And(F,*cs),assignment,vs)==1;stat.current={};assert manual.count_sample(list(assignment.items()));reached=e.get_id() in stat.current;value=exact_value(e,assignment,vs);value_hit=((value>>case['event']['bit'])&1)==case['event']['desired'];assert exact_value(R,assignment,vs)==int(reached);assert exact_value(V,assignment,vs)==int(value_hit)
    row.update(F_legal=True,oracle_constraints_verified=True,metric_reached=reached,value_hit=value_hit,observation_hit=reached and value_hit,formal_sample=False);write(d/(label+'.model.json'),assignment)
   if label in ('Q5','Q6') and answers.get('Q4')=='unsat':row['interpretation']='infeasible_antecedent_vacuous_not_mapping_or_reach_proof'
   write(d/(label+'.result.json'),row);summary.append(row);print(case['case_id'],label,str(answer),round(elapsed,3),flush=True)
  write(d/'Q7.result.json',{'status':'mapping_unknown','solver_call':False,'reason':'Historical raw internal atom/declaration provenance was never recorded; canonical key is not equivalence proof.'})
 write(OUT/'summary.json',{'calls':calls,'cases':len(plan['cases']),'Q0_existing_verified':len(plan['cases']),'Q7_mapping_unknown':len(plan['cases']),'results':summary,'official_metric_sha256':digest(metric_path()),'sampler_executions':0,'B_online':False})
if __name__=='__main__':main()
