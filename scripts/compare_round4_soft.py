#!/usr/bin/env python3
"""Predeclared common target pools; independent exact official evaluation only."""
from semantic_oracle import *
from audit_round4_soft import rows,targets
BASE=ROOT/'results/round4'
def main():
 result=[];plan=read(ROOT/'manifests/round4_S_comparison_audit_plan.json');assert plan['solver_calls']==0
 for instance in ['convert','SMT_random','SMT_real']:
  jobs=[j for j in read(ROOT/'manifests/round4_short_plan.json')['jobs'] if j['instance']==instance and j['stage']=='S'];data={};pool=set()
  for j in jobs:
   d=BASE/'runs'/j['id'];counts=collections.defaultdict(lambda:collections.Counter());stat=Witness();manual=metric.ManualSatisfiesMetric((ROOT/j['input']).read_text(),stat);F=z3.And(manual._solver.assertions());nodes,_=dag(F);vs=variables(nodes);cat=rows(d/'a_atom_catalog.jsonl');known=collections.defaultdict(int)
   for entry in cat:
    for r in entry['rules']:known[r['node']]|=int(r['known_one'])|int(r['known_zero'])
   actions=rows(d/'a_actions.jsonl');selected=set().union(*(targets(a['support']) for a in actions)) if actions else set()
   if j['mode']=='S_cov':pool=selected
   data[j['mode']]={'directory':d,'job':j,'nodes':nodes,'vs':vs,'manual':manual,'stat':stat,'selected':selected,'known':known}
  initial={}
  for mode,r in data.items():
   with (r['directory']/'samples.formal').open() as f:first=next(metric.parse_samples(f))
   r['first']=dict(first);stat=r['stat'];stat.current={};assert r['manual'].count_sample(first);initial[mode]=set()
   for n,mask in r['known'].items():
    nid=r['nodes'][n].get_id()
    if nid not in stat.current:continue
    v=int(stat.current[nid]);initial[mode].update((n,bit,1-((v>>bit)&1)) for bit in range(64) if mask>>bit&1)
  common=initial['S_ref']&initial['S_cov'];row={'instance':instance,'first_formal_assignment_equal':data['S_ref']['first']==data['S_cov']['first'],'shared_initial_mappable_demands':len(common),'S_cov_selected_target_pool':len(pool),'modes':{}}
  # A fresh visitor ensures no first-model double count in final observations.
  for mode,r in data.items():
   stat=Witness();manual=metric.ManualSatisfiesMetric((ROOT/r['job']['input']).read_text(),stat);nodes,_=dag(z3.And(manual._solver.assertions()));vs=variables(nodes);tracked=common|pool;pure=set();observed=set();new=set();previous=collections.defaultdict(set);seen_first={};by_source=collections.Counter();receipts=rows(r['directory']/'formal_receipts.jsonl');local_vars={n:variables(dag(nodes[n])[0]) for n,bit,desired in tracked}
   with (r['directory']/'samples.formal').open() as f:
    for receipt,sample in zip(receipts,metric.parse_samples(f)):
     assignment=dict(sample);stat.current={};assert manual.count_sample(sample);cache={}
     for n,bit,desired in tracked:
      if n not in cache:cache[n]=int(stat.current[nodes[n].get_id()]) if nodes[n].get_id() in stat.current else exact_value(nodes[n],assignment,local_vars[n])
      v=cache[n];t=(n,bit,desired)
      if ((v>>bit)&1)==desired:pure.add(t)
      if nodes[n].get_id() in stat.current:
       actual=(int(stat.current[nodes[n].get_id()])>>bit)&1
       if actual==desired:
        observed.add(t)
        if 1-desired in previous[n,bit]:new.add(t)
        if t not in seen_first:seen_first[t]={'query':receipt['query'],'formal_index':receipt['formal_index'],'source':receipt['source']};by_source[receipt['source']]+=1
       previous[n,bit].add(actual)
   row['modes'][mode]={label:{'targets':len(p),'pure_value_hits':len(p&pure),'official_observation_hits':len(p&observed),'newly_covered':len(p&new)} for label,p in [('shared_initial',common),('cov_selected',pool)]};row['modes'][mode]['first_hit_sources']=by_source
  result.append(row)
 write(BASE/'analysis/S_comparison.json',{'passed':True,'plan_sha256':digest(ROOT/'manifests/round4_S_comparison_audit_plan.json'),'instances':result,'solver_calls':0,'same_internal_state':False,'cov_selected_pool_is_policy_selected':True});print(json.dumps(result))
if __name__=='__main__':main()
