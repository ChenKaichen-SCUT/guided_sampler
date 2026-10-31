#!/usr/bin/env python3
"""Independent S provenance, partial-reference, score and checklist audit. No check()."""
from semantic_oracle import *
import csv
BASE=ROOT/'results/round4'
def rows(p):return [json.loads(l) for l in p.open()] if p.exists() else []
def fnv(s):
 h=14695981039346656037
 for b in s.encode():h=((h^b)*1099511628211)&((1<<64)-1)
 return format(h,'x')
def dumped(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def integer(s):
 if s in ['true','false']:return int(s=='true')
 if s.startswith('(- '):return -int(s[3:-1])
 return int(s)
def targets(masks):
 out=set()
 for m in masks:
  for d,k in [(1,'desired_one_mask'),(0,'desired_zero_mask')]:
   bits=int(m[k])
   for bit in range(64):
    if bits>>bit&1:out.add((m['node'],bit,d))
 return out
def main():
 summaries=[];all_cases=[];oracle=read(ROOT/'results/round3_semantics/oracle/summary.json');answers={(r['case_id'],r['query']):r['result'] for r in oracle['results']};checklist=[c for c in read(ROOT/'results/round3_semantics/frozen_cases.json')['cases'] if answers[c['case_id'],'Q2']=='sat' and answers[c['case_id'],'Q3']=='unsat'];assert len(checklist)==4;assert {c['case_id'] for c in checklist}=={c['case_id'] for c in read(ROOT/'results/round3_semantics/frozen_cases.json')['cases'] if answers[c['case_id'],'Q2']=='sat' and answers[c['case_id'],'Q4']=='unsat'}
 binary=ROOT/'build/round4-audit-reference-rng';subprocess.run(['g++','-std=c++20','-O2',ROOT/'tests/round4/audit_reference_rng.cpp','-o',binary],check=True)
 for job in read(ROOT/'manifests/round4_short_plan.json')['jobs']:
  if job['stage']!='S':continue
  d=BASE/'runs'/job['id'];qs=rows(d/'queries.jsonl');inputs={r['query_id']:r for r in rows(d/'query_inputs.jsonl')};sources={r['query_id']:r for r in rows(d/'reference_sources.jsonl')};states={r['query_id']:r for r in rows(d/'coverage_snapshots.jsonl')};cat={r['key']:r for r in rows(d/'a_atom_catalog.jsonl')};counts=collections.Counter();actions=rows(d/'a_actions.jsonl');aa={(a['query_id'],a['backend_call_id'],a['decision_id']):a for a in actions};action_sources=collections.Counter(a['preference_source'] for a in actions);last_ls=0
  for q in qs:
   if q['source']=='CCSS':
    if q['result']=='sat':assert q['query'] in sources;last_ls=q['query']
    continue
   ref=inputs[q['query']];assert ref['reference_source_query']==last_ls;assert ref['hard_assumptions']==q['assumptions']==[];assert ref['hard_assumptions_count']==0;assert fnv(dumped(ref['hard_assumptions']))==ref['hard_assumptions_hash'];assert fnv(dumped(ref['reference']))==ref['reference_hash'];assert len(ref['reference'])==ref['reference_count'];eligible=[r for r in sources[last_ls]['entries'] if r['original'] and r['constant']] if last_ls else [];draws=ref['selection_draws'];assert [r['model_index'] for r in eligible]==[r['model_index'] for r in draws];selected=[r for r in draws if r['selected']];assert len(selected)==len(ref['reference'])
   for draw,r in zip(selected,ref['reference']):
    source=next(e for e in eligible if e['model_index']==draw['model_index']);assert r['model_index']==source['model_index'] and r['decl_id']==source['decl_id'] and r['value']==source['value'] and r['name']==source['name'];assert r['origin']=='sampler_m_ls';counts['softened_selected_values']+=1
   counts['checks_with_reference']+=bool(ref['reference_count'])
  entered={q['query'] for q in qs if q['source']=='CDCL'}
  pending=[r for q,r in inputs.items() if q not in entered]
  for ref in pending:
   assert ref['query_id']>max(q['query'] for q in qs) and read(d/'summary.json')['status']=='deadline'
   assert ref['reference_source_query']==last_ls and ref['hard_assumptions']==[] and ref['hard_assumptions_count']==0
   assert fnv(dumped(ref['reference']))==ref['reference_hash'] and fnv(dumped([]))==ref['hard_assumptions_hash']
   eligible=[r for r in sources[last_ls]['entries'] if r['original'] and r['constant']] if last_ls else []
   assert [r['model_index'] for r in eligible]==[r['model_index'] for r in ref['selection_draws']]
   selected=[r for r in ref['selection_draws'] if r['selected']];assert len(selected)==len(ref['reference'])
   for draw,r in zip(selected,ref['reference']):
    source=next(e for e in eligible if e['model_index']==draw['model_index']);assert r['decl_id']==source['decl_id'] and r['value']==source['value'] and r['origin']=='sampler_m_ls'
   counts['unentered_reference_preparations']+=1;counts['unentered_selected_values']+=len(selected)
  replay=subprocess.run([binary,d],capture_output=True,text=True);(d/'reference_rng.audit.stdout').write_text(replay.stdout);(d/'reference_rng.audit.stderr').write_text(replay.stderr);assert replay.returncode==0;replay=json.loads(replay.stdout)
  stat=Witness();manual=metric.ManualSatisfiesMetric((ROOT/job['input']).read_text(),stat);F=z3.And(manual._solver.assertions());nodes,_=dag(F);vs=variables(nodes);originals={n['decl_id']:n for n in read(d/'original_nodes.json') if n['operator']==z3.Z3_OP_UNINTERPRETED and not n['children']};sem=rows(d/'semantic.jsonl');outer={(r['external_query_id'],r['backend_call_id']):r for r in sem if r['kind']=='model_layer' and r['layer']=='M_outer'};encounters=[];qrefused=collections.defaultdict(set);qcovused=collections.defaultdict(set);qcovcount=collections.Counter()
  for snap in sem:
   if snap['kind']!='semantic_snapshot':continue
   for rec in snap['encounters']:
    if 'preference_source' in rec:encounters.append((snap,rec))
  for snap,rec in sorted(encounters,key=lambda pair:(pair[0]['external_query_id'],pair[1]['decision_id'])):
   q=snap['external_query_id'];b=snap['backend_call_id'];ref=inputs[q];assert rec['hard_assumptions_hash']==ref['hard_assumptions_hash'] and rec['reference_hash']==ref['reference_hash'];mask=states[q]['seen_masks'];support=[set(),set()];block=[set(),set()];key=rec['canonical_key'];neg=rec['canonical_negated'];counts['native_encounters']+=1
   for rule in cat.get(key,{}).get('rules',[]):
    n=rule['node'];s0,s1=map(int,mask[n]);w1=s0&~s1;w0=s1&~s0;one=int(rule['known_one']);zero=int(rule['known_zero']);p=int(rule['phase'])
    for bit in range(1 if z3.is_bool(nodes[n]) else 64):
     for desired,want,known,opposite in [(1,w1,one,zero),(0,w0,zero,one)]:
      if want>>bit&1:
       if known>>bit&1:support[p].add((n,bit,desired))
       if opposite>>bit&1:block[p].add((n,bit,desired))
   if rec['evidence_complete']:
    for phase,label in [(0,'false'),(1,'true')]:
     cp=phase!=neg;assert rec['support_'+label]==len(support[cp]);assert rec['block_'+label]==len(block[cp])
    scores=[(len(support[p]),-len(block[p])) for p in range(2)];best=None if scores[0]==scores[1] else scores[1]>scores[0];expected_phase=None if best is None else best!=neg;assert rec['coverage_phase']==expected_phase
   else:best=None;counts['incomplete_score']+=1
   actual=rec['actual_atom'];meta=outer.get((q,b));identity=bool(meta and meta['same_manager']) and all(not x['skolem'] and x['arity']==0 and x['decl_id'] in originals and originals[x['decl_id']]['expr']==x['name'] and originals[x['decl_id']]['sort']==x['range'] for x in actual['declarations'])
   if rec['reference_phase'] is not None:
    if identity:
     assignment={r['name']:integer(r['value']) for r in ref['reference'] if r['defined']};names={r['name'] for r in actual['declarations']};assert names.issubset(assignment);atom=parse_expr(actual['expr'],vs);val=exact_value(atom,assignment,{k:v for k,v in vs.items() if k in assignment});assert val is not None and bool(val)==rec['reference_phase'];counts['reference_phase_independently_verified']+=1
    else:counts['reference_identity_unknown']+=1
   a=aa.get((q,b,rec['decision_id']))
   if not a:continue
   counts['actions_audited']+=1;source=a['preference_source'];assert a['effective_phase']==a['suggested_phase'];assert a['phase_changed']==(a['native_phase']!=a['effective_phase']);assert a['coverage_overrode_reference']==(source in ['coverage_support','avoid_direct_blocker'] and rec['reference_phase'] is not None and a['effective_phase']!=rec['reference_phase'])
   if source in ['coverage_support','avoid_direct_blocker']:
    assert job['mode']=='S_cov' and best is not None and qcovcount[q]<4;avoid=len(support[0])==len(support[1]);assert source==('avoid_direct_blocker' if avoid else 'coverage_support');assert a['suggested_phase']==(best!=neg);candidate=(block[not best]-block[best]) if avoid else support[best];expected={t for t in candidate if (key,best,t,source) not in qcovused[q]};assert targets(a['support'])==expected and expected;assert a['target_semantics']==('avoid_known_opposite_not_guaranteed_value' if avoid else 'direct_value_support_not_guaranteed_reach');qcovused[q].update((key,best,t,source) for t in expected);qcovcount[q]+=1
   elif source=='inherited_reference':
    assert a['suggested_phase']==rec['reference_phase'] and not a['support'];rk=(key,a['suggested_phase']!=neg);assert rk not in qrefused[q];qrefused[q].add(rk)
   else:raise AssertionError('unexpected action source')
  assert counts['actions_audited']==len(actions),(job['id'],counts,len(actions))
  formal=rows(d/'formal_receipts.jsonl');model_stats=collections.Counter();case_counts={c['case_id']:collections.Counter() for c in checklist if c['input']==job['input']};case_details=[]
  with (d/'samples.formal').open() as f:
   for receipt,sample in zip(formal,metric.parse_samples(f)):
    stat.current={};assert manual.count_sample(sample);assignment=dict(sample)
    for c in checklist:
     if c['input']!=job['input']:continue
     e=c['event'];node=nodes[e['node']];assert node.sexpr()==c['target_expr'];val=exact_value(node,assignment,vs);reached=node.get_id() in stat.current;hit=((val>>e['bit'])&1)==e['desired'];counter=case_counts[c['case_id']];counter['formal_models']+=1;counter['value_hits']+=hit;counter['reached']+=reached;counter['observation_hits']+=hit and reached;counter['CDCL_observation_hits']+=receipt['source']=='CDCL' and hit and reached
     if hit and reached:case_details.append({'case_id':c['case_id'],'query':receipt['query'],'formal_index':receipt['formal_index'],'source':receipt['source'],'value':val})
  for c in checklist:
   if c['input']!=job['input']:continue
   e=c['event'];t=(e['node'],e['bit'],e['desired']);case_counts[c['case_id']]['selected_in_advice']=sum(t in targets(a['support']) for a in actions);case_counts[c['case_id']]['native_encounters_with_target_mapping']=sum(any(r['node']==e['node'] for r in cat.get(rec['canonical_key'],{}).get('rules',[])) for snap,rec in encounters)
  all_cases.append({'run_id':job['id'],'cases':case_counts,'observations':case_details})
  receipts=rows(d/'sample_receipts.jsonl');rejects=[r for r in receipts if r['kind']=='reject'];counts['duplicate_candidates']=sum(r['status']=='duplicate' for r in rejects);counts['invalid_candidates']=sum(r['status']=='invalid' for r in rejects);assert not counts['invalid_candidates'];counts['formal_CDCL']=sum(r['source']=='CDCL' for r in formal);counts['formal_CCSS']=sum(r['source']=='CCSS' for r in formal);counts['CCSS_unknown']=sum(q['source']=='CCSS' and q['result']=='unknown' for q in qs);counts['CDCL_unknown']=sum(q['source']=='CDCL' and q['result']=='unknown' for q in qs)
  exposure=sum(q['check_seconds'] for q in qs if q['guidance'].get('intervened_check'));assert abs(exposure-read(d/'summary.json')['A_exposure'])<1e-6
  unique_targets=set();unique_new=set();chain=[r for r in csv.DictReader((BASE/'analysis/S/target_chain.csv').open()) if r['run_id']==job['id']];fullchain=[r for r in csv.DictReader((BASE/'analysis/S/event_chain.csv').open()) if r['run_id']==job['id']];complete={(r['query_id'],r['backend_call_id'],r['decision_id']) for r in fullchain if r['first_broken_link']=='no_truth_break_observed' and r['final_token_direct_transmission']=='True' and r['overflow']=='False'};positive_chains=set()
  for r in chain:
   target=(r['node'],r['bit'],r['desired']);unique_targets.add(target)
   if r['new_covered']=='True':
    unique_new.add(target)
    if (r['query_id'],r['backend_call_id'],r['decision_id']) in complete:positive_chains.add((r['query_id'],r['backend_call_id'],r['decision_id'],*target))
  counts['unique_action_targets']=len(unique_targets);counts['unique_action_targets_newly_covered']=len(unique_new);counts['complete_direct_theory_positive_target_chains']=len(positive_chains)
  funnel=collections.Counter()
  for b in rows(d/'a_backend_calls.jsonl'):
   if 'funnel' in b:funnel.update(b['funnel'])
  summaries.append({'id':job['id'],'passed':True,'counts':counts,'action_sources':action_sources,'phase_overrides_by_source':collections.Counter(a['preference_source'] for a in actions if a['phase_changed']),'funnel':funnel,'host_rng_replay':replay,'summary':read(d/'summary.json'),'official':{k:v for k,v in read(d/'exact.json').items() if k!='prefixes'},'routes':dict(collections.Counter(q['guidance'].get('backend_calls',[{}])[0].get('outer_route','no_backend') if q['guidance'].get('backend_calls') else 'no_backend' for q in qs if q['source']=='CDCL')),'cost_ledger_last':rows(d/'cost_ledger.jsonl')[-1]})
 write(BASE/'analysis/S_checklist.json',{'source_cases_sha256':digest(ROOT/'results/round3_semantics/frozen_cases.json'),'source_oracle_sha256':digest(ROOT/'results/round3_semantics/oracle/summary.json'),'blocking_query':'Q3 = F + A + Reach + desired value','frozen_plan_Q4_label_corrected_without_changing_case_set':True,'checklist_case_ids':[c['case_id'] for c in checklist],'runs':all_cases,'additional_solver_calls':0,'oracle_models_used_online':False});write(BASE/'analysis/S_summary.json',{'passed':True,'runs':summaries,'additional_solver_calls':0,'interpretation':'S_ref is the common soft-host control; action-target denominators are policy dependent, not same-state causal samples'});print(json.dumps([{'id':r['id'],'counts':r['counts']} for r in summaries]))
if __name__=='__main__':main()
