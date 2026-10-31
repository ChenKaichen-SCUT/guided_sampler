#!/usr/bin/env python3
"""Reuse frozen R3 feasibility answers only after exact F/A/G identity checks."""
from semantic_oracle import *
import csv,re
BASE=ROOT/'results/round4'
def rows(p):return [json.loads(l) for l in p.open()]
def normalized(s):return re.sub(r'\s+',' ',s).strip()
def reference(d):
 r=next(r for r in rows(d/'query_inputs.jsonl') if r['query_id']==3)
 assert all(x['defined'] and re.fullmatch(r'[A-Za-z0-9_]+',x['name']) for x in r['reference'])
 return {normalized('(= '+x['name']+' '+x['value']+')') for x in r['reference']}
def main():
 directories={m:BASE/'runs'/('convert_'+m) for m in ['S_ref','S_cov']};selected=reference(directories['S_cov']);assert len(selected)==489;assert selected==reference(directories['S_ref'])
 for mode in ['M_observe','M_apply']:
  query=next(q for q in rows(BASE/'runs'/('convert_'+mode)/'queries.jsonl') if q['query']==3);assert {normalized(x) for x in query['assumptions']}==selected
 cases=read(ROOT/'results/round3_semantics/frozen_cases.json')['cases'];oracle=read(ROOT/'results/round3_semantics/oracle/summary.json');answers={(r['case_id'],r['query']):r for r in oracle['results']};targets=list(csv.DictReader((BASE/'analysis/S/target_chain.csv').open()));evidence=[]
 for cid in ['case_05','case_09']:
  case=next(c for c in cases if c['case_id']==cid);assert digest(ROOT/case['input'])==case['input_sha256'];assert {normalized(x) for x in case['assumptions']}==selected
  manual=metric.ManualSatisfiesMetric((ROOT/case['input']).read_text(),metric.WireCoverageStatistics());nodes,_=dag(z3.And(manual._solver.assertions()));event=case['event'];assert nodes[event['node']].sexpr()==case['target_expr'];assert answers[cid,'Q2']['result']=='sat' and answers[cid,'Q3']['result']=='unsat'
  result=next(r for r in targets if r['run_id']=='convert_S_cov' and r['query_id']=='3' and r['node']==str(event['node']) and r['bit']==str(event['bit']) and r['desired']==str(event['desired']));assert all(result[k]=='True' for k in ['value_hit','metric_reached','new_covered'])
  evidence.append({'case_id':cid,'input_sha256':case['input_sha256'],'target_expr':case['target_expr'],'node':event['node'],'bit':event['bit'],'desired':event['desired'],'historical_Q2':answers[cid,'Q2'],'historical_Q3':answers[cid,'Q3'],'same_current_reference_as_old_hard_conditions':True,'same_as_current_M_query_3_hard_conditions':True,'formal_observation':result})
 prefixes={};snapshots={};models={};early={}
 for mode,d in directories.items():
  query=next(q for q in rows(d/'queries.jsonl') if q['query']==3);assert query['assumptions']==[]
  snap=next(r for r in rows(d/'semantic.jsonl') if r['kind']=='semantic_snapshot' and r['external_query_id']==3);prefixes[mode]=[(r['decision_id'],r['canonical_key'],r['native_phase']) for r in snap['encounters'] if r['decision_id']<=30];snapshots[mode]=next(r for r in rows(d/'coverage_snapshots.jsonl') if r['query_id']==3);models[mode]=[(r['query'],r['model_hash']) for r in rows(d/'models.jsonl') if r.get('query') in [1,2]];early[mode]=[r for r in rows(d/'a_actions.jsonl') if r['query_id']==3 and r['decision_id']<=30]
 assert prefixes['S_ref']==prefixes['S_cov'] and len(prefixes['S_cov'])==30;assert snapshots['S_ref']==snapshots['S_cov'];assert models['S_ref']==models['S_cov'];assert not early['S_ref'] and len(early['S_cov'])==1 and early['S_cov'][0]['decision_id']==30
 write(BASE/'analysis/reused_blocker_proof.json',{'passed':True,'additional_solver_calls':0,'source_cases_sha256':digest(ROOT/'results/round3_semantics/frozen_cases.json'),'source_oracle_sha256':digest(ROOT/'results/round3_semantics/oracle/summary.json'),'current_selected_equalities':sorted(selected),'condition_count':489,'comparison':'exact equality-expression text modulo whitespace and conjunction order; original declarations and values independently audited','cases':evidence,'first_two_formal_model_hashes':models,'pre_query_3_coverage_snapshots_equal':True,'first_30_native_key_phase_choices_equal':True,'first_30_native_key_phase_choices':prefixes['S_cov'],'early_actions':early,'oracle_query_definitions':{'Q2':'F + Reach + desired value','Q3':'F + inherited A + Reach + desired value'},'oracle_construction_source_sha256':digest(ROOT/'scripts/check_target_feasibility.py'),'same_internal_solver_state_claim':False,'limitation':'No new oracle or exact internal-state replay. Theory causal association remains incomplete. The two observed nodes express one logical inequality condition.'});print('Reused two frozen blockers for the identical current 489-condition reference; no solver calls')
if __name__=='__main__':main()
