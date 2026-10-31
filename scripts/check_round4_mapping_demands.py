#!/usr/bin/env python3
from semantic_oracle import *
import time
BASE=ROOT/'results/round4';out=BASE/'mapping_checks/demand_feasibility'
def main():
 out.mkdir(exist_ok=False);jobs={j['id']:j for j in read(ROOT/'manifests/round4_short_plan.json')['jobs']};selected=[];seen=set()
 for r in map(json.loads,(BASE/'mapping_checks/opportunities.jsonl').open()):
  if not r['coverage_version'] or not r['declaration_identity_proved']:continue
  scores=r['raw_positive_scores_before_old_attempted_filter']
  if scores[0]==scores[1]:continue
  phase=int(scores[1]>scores[0]);job=jobs[r['run_id']]
  for n,bit,desired in r['positive_support_targets'][phase]:
   k=(job['instance'],n,bit,desired)
   if k in seen or len(selected)>=6:continue
   seen.add(k);selected.append({'id':len(selected),'input':job['input'],'input_sha256':job['input_sha256'],'run_id':r['run_id'],'query_id':r['query_id'],'node':n,'bit':bit,'desired':desired})
 exclusive(out/'selected.json',selected);contexts={};results=[];calls=0
 for case in selected:
  p=ROOT/case['input'];assert digest(p)==case['input_sha256']
  if case['input'] not in contexts:
   stat=Witness();manual=metric.ManualSatisfiesMetric(p.read_text(),stat);F=z3.And(manual._solver.assertions());nodes,reaches=reach_all(F);vs=variables(nodes);contexts[case['input']]=(stat,manual,F,nodes,reaches,vs)
  stat,manual,F,nodes,reaches,vs=contexts[case['input']];V=value_condition(nodes[case['node']],case['bit'],case['desired']);R=reaches[case['node']];query=next(q for q in map(json.loads,(BASE/'runs'/case['run_id']/'queries.jsonl').open()) if q['query']==case['query_id']);
  try:A=[parse_expr(x,vs) for x in query['assumptions']];assumption_error=''
  except z3.Z3Exception as err:A=None;assumption_error=str(err)
  for label,constraints in [('global',[F,R,V]),('inherited',[F,*(A or []),R,V])]:
   stem=out/f"case_{case['id']:02}_{label}"
   if label=='inherited' and A is None:
    row={**case,'condition':label,'result':'unknown','solver_call':False,'reason_unknown':'assumption_declaration_provenance_unavailable','detail':assumption_error,'formal_sample':False};write(stem.with_suffix('.result.json'),row);results.append(row);continue
   solver=z3.Solver(ctx=metric.CTX);solver.set(timeout=2000,random_seed=0);solver.add(*constraints);stem.with_suffix('.smt2').write_text(solver.to_smt2());exclusive(stem.with_suffix('.attempt.json'),{'timeout_ms':2000,'seed':0});t=time.monotonic();a=solver.check();calls+=1;row={**case,'condition':label,'solver_call':True,'result':str(a),'seconds':time.monotonic()-t,'reason_unknown':solver.reason_unknown() if a==z3.unknown else '', 'formal_sample':False}
   if a==z3.sat:
    m=solver.model();assignment={name:m.eval(v,True).as_long() if z3.is_int(v) else int(z3.is_true(m.eval(v,True))) for name,v in vs.items()};assert exact_value(z3.And(*constraints),assignment,vs)==1;stat.current={};assert manual.count_sample(list(assignment.items()));assert nodes[case['node']].get_id() in stat.current;assert ((exact_value(nodes[case['node']],assignment,vs)>>case['bit'])&1)==case['desired'];write(stem.with_suffix('.model.json'),assignment);row['independent_F_value_reach_verified']=True
   write(stem.with_suffix('.result.json'),row);results.append(row);print(case['id'],label,str(a),flush=True)
 write(out/'summary.json',{'passed':True,'cases':len(selected),'solver_calls':calls,'maximum_calls':12,'answers_online':False,'results':results});r=read(BASE/'analysis/M_summary.json');r['new_mapping_demand_feasibility']=read(out/'summary.json');write(BASE/'analysis/M_summary.json',r)
if __name__=='__main__':main()
