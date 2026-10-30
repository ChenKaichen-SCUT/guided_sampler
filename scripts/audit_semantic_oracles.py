#!/usr/bin/env python3
"""Independent persisted-witness audit; zero new check calls."""
from semantic_oracle import *
BASE=ROOT/'results/round3_semantics'
def main():
 plan=read(ROOT/'manifests/round3_semantic_cases.json');contexts={};verified=[];calls=0
 for case in plan['cases']:
  p=ROOT/case['input'];assert digest(p)==case['input_sha256']
  if case['input'] not in contexts:
   stat=Witness();manual=metric.ManualSatisfiesMetric(p.read_text(),stat);F=z3.And(manual._solver.assertions());nodes,_=dag(F);vs=variables(nodes);contexts[case['input']]=(stat,manual,F,nodes,vs)
  stat,manual,F,nodes,vs=contexts[case['input']];d=BASE/'oracle'/case['case_id']
  for q in ['Q0','Q1','Q2','Q3','Q4','Q5','Q6','Q7']:
   r=read(d/(q+'.result.json'));calls+=int(r['solver_call'])
   if r['solver_call']:assert r['timeout_ms']==2000 and (d/(q+'.smt2')).exists()
   model=d/(q+'.model.json')
   if not model.exists():continue
   a={k:int(v) for k,v in read(model).items()};assert set(a)==set(vs);assert exact_value(F,a,vs)==1
   if q=='Q0':constraints=z3.And(F,*[parse_expr(x,vs) for x in case['assumptions']])
   else:constraints=z3.And(z3.parse_smt2_file(str(d/(q+'.smt2')),ctx=metric.CTX))
   ns,_=dag(constraints);assert exact_value(constraints,a,variables(ns))==1
   stat.current={};assert manual.count_sample(list(a.items()));e=nodes[case['event']['node']];value=exact_value(e,a,vs);reached=e.get_id() in stat.current;hit=((value>>case['event']['bit'])&1)==case['event']['desired']
   if q!='Q0':assert r['metric_reached']==reached and r['value_hit']==hit and r['observation_hit']==(reached and hit)
   verified.append({'case_id':case['case_id'],'query':q,'model_sha256':digest(model),'F_legal':True,'persisted_query_satisfied':True,'official_metric_reached':reached,'pure_value_hit':hit,'formal_sample':False})
 assert calls==read(BASE/'oracle/summary.json')['calls']==72
 result={'passed':True,'solver_calls_added':0,'historical_calls_verified':calls,'models_verified':len(verified),'models':verified,'official_metric_sha256':digest(metric_path())};write(BASE/'oracle/independent_audit.json',result);print('Verified',len(verified),'persisted witnesses; no solver calls added')
if __name__=='__main__':main()
