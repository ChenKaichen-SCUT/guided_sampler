"""Independent mathematical, official-observation and delivery audit; no solver check."""
from common_bd import *
from runner import stream_rows
from check_blocking import IndependentDomains,packed,nearest
from independent import observations,evaluate,covered,official_trace,export
import collections,functools,z3,math
out=attempt('analysis','audit_v1');cfg=read(ROOT/'configs/refinement_budget_delivery.json');summaries=[];prefixes=[];events_table=[];pre_table=[];distinct=set();official_calls=0;candidate_checks=0;equalities_checked=0;certs=[];real_rows=[]
def masks(js):return {(i,b,v) for i,z,o,*rest in js for b in range(64) for v in (0,1) if (o if v else z)>>b&1}
def meta_core(meta):return {k:v for k,v in meta.items() if k!='score_index'}
def normalize_vector(v):
 v={k:x for k,x in v.items() if x}
 if not v:return []
 g=math.gcd(*v.values());sign=1 if v[min(v)]>0 else -1
 return [[k,str(sign*x//g)] for k,x in sorted(v.items())]
for name in ['convert','SMT_random','SMT_real']:
 data=read(ROOT/f'results/refinement/offline/inputs_v1/{name}.json');ast=data['ast'];models=data['models'];root=z3.And(z3.parse_smt2_file(data['input']));exported,_,vs=export(root);assert exported['nodes']==ast['nodes'] and exported['variables']==ast['variables'];meta_ref=None
 @functools.lru_cache(maxsize=12)
 def inspect(m):
  global official_calls
  legal,tr=evaluate(ast,m);ok,official=official_trace(root,{v['name']:int(x) for v,x in zip(ast['variables'],m)});assert ok==legal and official=={i:value for i,(bits,value) in tr.items()};official_calls+=1;distinct.add((name,m));_,obs=observations(ast,m);return legal,obs
 jobs=[('probes',j) for j in cfg['probes'] if j['instance']==name]+[('offline',j) for j in cfg['offline'] if j['instance']==name]
 for stage,job in jobs:
  d=BASE/stage/'frozen_v1'/job['id'];rows_,truncated=stream_rows(d/'stream.jsonl');terminal=read(d/'terminal.json');assert not any(r['kind']=='failure' for r in rows_)
  meta=next((r['metadata'] for r in rows_ if r['kind']=='metadata'),None);pre=next((r for r in rows_ if r['kind']=='preprocess'),None);summary=next((r for r in rows_ if r['kind']=='summary'),{});events={r['native_event_id']:r for r in rows_ if r['kind']=='event_proposed'};costs={r['native_event_id']:r for r in rows_ if r['kind']=='event_cost_proposed'};probe=stage=='probes';l1=probe or job['track']=='L1';counts=collections.Counter();delivered_models=[];native_history=set();history=set();keys=set()
  if meta:
   if meta_ref is None:meta_ref=meta_core(meta)
   assert meta_core(meta)==meta_ref,('metadata mismatch',job['id'])
   independent=IndependentDomains(ast,models[0],[]);eq=independent.equalities();assert [{ 'coefficients':[[v,str(c)] for v,c in sorted(cs.items())], 'constant':str(c)} for _,c,cs in eq]==meta['equalities']
   for direction in meta['directions']:
    co={v:int(c) for v,c in direction['coefficients']};assert normalize_vector(co)==direction['coefficients'];assert all(sum(c*co.get(v,0) for v,c in cs.items())==0 for _,_,cs in eq)
    assert direction['affected']==[i for i in range(len(ast['nodes'])) if independent.deps[i]&co.keys()];equalities_checked+=len(eq)
  if pre:
   independent=IndependentDomains(ast,models[0],[])
   for direction in pre['trace'].get('verified_directions',[]):
    co={v:int(c) for v,c in direction['coefficients']};assert all(sum(c*co.get(v,0) for v,c in cs.items())==0 for _,_,cs in independent.equalities());equalities_checked+=len(independent.equalities())
   pre_table.append({'sequence':job['id'],'stage':stage,'instance':name,'configuration':job['configuration'],'cpu':summary.get('preprocess_total_cpu'),'wall':summary.get('preprocess_total_wall'),'eligible':summary.get('preprocess_eligible'),'status':summary.get('effective_preprocess_status'),'process_peak_rss_kb':pre.get('preprocess_process_peak_rss_kb'),**pre['trace']['work']})
  receipts=summary.get('receipts',[])
  if not probe:assert len(receipts)==len(models) and not truncated and terminal['returncode']==0
  for rec in receipts:
   pos=rec['native_event_id'];row=events[pos];cost=costs[pos];assert row['native_assignment']==models[pos-1];assert rec['source_assignment_sha']==sha_text(json.dumps(models[pos-1],separators=(',',':')));m=tuple(models[pos-1]);legal,native=inspect(m);assert legal;protected=native-history;gain=(covered(history|native)-covered(history),len(native-history));assert rec['output_history_version']==len(keys)
   if row['baseline_scored']:assert gain==(row['base_gain_covered'],row['base_gain_observed']);assert masks(row['protected_masks'])==protected
   if row['selected_direction_order']:
    assert meta is not None;scores=[]
    cov={(i,b) for i,b,v in history if (i,b,1-v) in history}
    for direction in meta['directions']:scores.append(sum((1 if ast['nodes'][n]['sort']=='Bool' else 64)-sum((n,b) in cov for b in range(1 if ast['nodes'][n]['sort']=='Bool' else 64)) for n in direction['affected']))
    assert scores==row['direction_scores'];ranked=sorted(range(len(scores)),key=lambda i:(-scores[i],i))[:8];rest=[i for i in range(len(scores)) if i not in ranked];chosen=ranked+[rest[(pos+i)%len(rest)] for i in range(min(8,len(rest)))];assert chosen==row['selected_direction_order']
   eligible_candidates=[];unprotected=[];first_gain=None
   for c in row['candidates']:
    if c['kind']=='target':counts['target_records']+=1;counts['proposed_parameters']+=len(c.get('parameters',[]));continue
    counts['candidate_records']+=1;counts['candidate_'+c.get('reason','unclassified')]+=1
    if 'missing_observations' not in c:continue
    q=tuple(c['assignment']);ql,obs=inspect(q);assert ql;candidate_checks+=1
    loss=protected-obs;g=(covered(history|obs)-covered(history),len(obs-history));assert masks(c['actual_observations'])==obs;assert set(map(tuple,c['missing_observations']))==loss;assert c['protected_missing_count']==len(loss);assert g==(c['gain_covered'],c['gain_observed']);assert c['output_duplicate']==(q in keys)
    if not c.get('evaluation_complete',False):continue
    counts['complete_evaluations']+=1
    # A completed evaluation can still fail while saving its candidate; it cannot be assumed delivered.
    if c['reason'].startswith('incomplete'):continue
    expected='protected_observation_missing' if loss else 'output_duplicate' if q in keys else 'legal_not_better_than_native' if g<=gain else 'eligible_strict_improvement';assert expected==c['reason']
    counts['preserved' if not loss else 'protected_rejected']+=1
    if q not in keys and g>gain:
     key=(-g[0],-g[1],c['direction_id'],abs(int(c['t'])),int(c['t']));unprotected.append((key,c))
     if not loss:
      eligible_candidates.append((key,c))
      if first_gain is None and g[0]>gain[0]:first_gain=c
   assert sum(c.get('evaluation_complete',False) for c in row['candidates'] if c['kind']=='candidate')==row['completed_evaluations']
   if row['cancellation']=='first_covered':assert first_gain and row['chosen']['assignment']==first_gain['assignment']
   for field in ['chosen','unprotected_chosen']:
    options=eligible_candidates if field=='chosen' else unprotected
    expected=min(options,key=lambda x:x[0])[1] if options else None
    assert bool(expected)==bool(row[field]),(job['id'],pos,field,'selection existence')
    if expected:assert row[field]['assignment']==expected['assignment'] and row[field]['direction']==expected['direction_id'] and row[field]['t']==expected['t'],(job['id'],pos,field,'selection order')
    if row[field]:
     q=tuple(row[field]['assignment']);ql,obs=inspect(q);assert ql
     if field=='chosen':assert protected<=obs
     assert q not in keys and (covered(history|obs)-covered(history),len(obs-history))>gain
   if rec['budget_eligible']:
    assert row['chosen'] and rec['preprocess_eligible'];assert rec['event_total_cpu']<rec['event_cpu_cap'] and rec['event_total_wall']<rec['event_wall_cap'];assert rec['preprocess_total_cpu']<(2 if probe else .1) and rec['preprocess_total_wall']<(2 if probe else .1)
    counts['budget_eligible']+=1
   if rec['actually_delivered']:assert rec['budget_eligible'] and not l1;counts['actual_replacements']+=1
   output=tuple(rec['candidate_assignment']) if rec['actually_delivered'] else m
   legal,obs=inspect(output);assert legal and protected<=obs;history|=obs;native_history|=native;keys.add(output);delivered_models.append(output)
   assert native_history<=history and rec['prefix_contains_native'];assert covered(history)==rec['output_covered'] and covered(native_history)==rec['native_covered'] and len(keys)==rec['output_count']
   if rec['actually_delivered'] and rec['candidate_gain']['covered']>gain[0]:counts['strict_covered_deliveries']+=1
   counts['completed_domains']+=cost['trace']['completed_domains'];counts['events']+=1
   entry={'sequence':job['id'],'stage':stage,'instance':name,'configuration':job['configuration'],'track':job['track'],'repeat':job.get('repeat'),'position':pos,'extra_covered':covered(history)-covered(native_history),**rec,'cost_trace':cost['trace']};events_table.append(entry);prefixes.append({k:entry[k] for k in ['sequence','stage','instance','configuration','track','repeat','position','extra_covered','native_covered','output_covered','actually_delivered','budget_eligible']})
  if summary:
   assert summary['output_covered']==covered(history) and summary['native_covered']==covered(native_history) and summary['historical_cpu_credit_proven']==False
   tail=read(d/'outer_tail.json') if (d/'outer_tail.json').exists() else None
   optional_c=summary['optional_cpu']+(tail['summary_cpu'] if tail else 0);optional_w=summary['optional_wall']+(tail['summary_wall'] if tail else 0)
   if counts['actual_replacements']:assert optional_c<6 and optional_w<6
  else:tail=None;optional_c=optional_w=None
  item={'sequence':job['id'],'stage':stage,'instance':name,'configuration':job['configuration'],'track':job['track'],'repeat':job.get('repeat'),'counts':dict(counts),'preprocess_status':summary.get('effective_preprocess_status'),'preprocess_eligible':summary.get('preprocess_eligible'),'preprocess_cpu':summary.get('preprocess_total_cpu'),'preprocess_wall':summary.get('preprocess_total_wall'),'final_extra':covered(history)-covered(native_history),'native_covered':covered(native_history),'output_covered':covered(history),'optional_cpu':optional_c,'optional_wall':optional_w,'mandatory_cpu':summary.get('mandatory_cpu'),'mandatory_wall':summary.get('mandatory_wall'),'terminal':terminal,'summary_tail':tail,'truncated':truncated};summaries.append(item)
  if not probe:
   official=out/'official'/job['id'];official.mkdir(parents=True)
   for kind,ms in [('native',models),('output',delivered_models)]:
    unique=list(dict.fromkeys(tuple(m) for m in ms));samples=official/(kind+'.samples');samples.write_text(''.join(str(k)+': '+''.join(v['name']+':'+str(x)+';' for v,x in zip(ast['variables'],m))+'\n' for k,m in enumerate(unique)))
    cmd=[python(),metric_path(),'-s',samples,'-f',data['input'],'-m','wire_coverage'];r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120);(official/(kind+'.stdout')).write_text(r.stdout);(official/(kind+'.stderr')).write_text(r.stderr);expected=covered(native_history) if kind=='native' else covered(history);universe=sum(1 if n['sort']=='Bool' else 64 for n in ast['nodes']);assert r.returncode==0 and r.stdout.strip()==str(round(expected/universe*100,2))+'%'
    write(official/(kind+'.command.json'),{'command':list(map(str,cmd)),'returncode':r.returncode,'script_sha256':digest(metric_path()),'samples_sha256':digest(samples)})
 if name=='SMT_random':assert meta_ref and not meta_ref['directions'] and sum(c['status']=='component_size_limit' for c in meta_ref['components'])==10
 if name=='SMT_real':
  for request in cfg['real_requests']:
   d=BASE/'real_diagnosis/frozen_v1'/f'SMT_real_{request["position"]:02d}';rr,trunc=stream_rows(d/'stream.jsonl');summary=next((r for r in rr if r['kind']=='summary'),{});originals={};seen=set();terminal=read(d/'terminal.json')
   for row in rr:
    if row['kind'] not in ['original','combination']:continue
    identity={'position':request['position'],'kind':row['kind'],'direction_id':row.get('direction_id'),'ordinal':row.get('ordinal')};cost=next((x for x in summary.get('costs',[]) if x['request']['kind']==row['kind'] and x['request'].get('direction_id')==row.get('direction_id') and x['request'].get('ordinal')==row.get('ordinal')),{});within=cost.get('within_request_cap',False) and terminal['returncode']==0 and not terminal['external_timeout'];record={**identity,'status':row['status'],'root_complete':row.get('root_complete',False),'certificate_complete':row.get('certificate_complete',False),'verified':False,'B2':False,'B3':False,'already_in_pool':row.get('already_in_pool',False),'within_request_cap':within}
    if row['kind']=='original':
     old=next(x for x in request['selected'] if x['id']==row['direction_id']);assert row['coefficients']==old['coefficients']
    else:
     pair=request['combinations'][row['ordinal']];assert pair==row['pair'];left=next(x for x in request['selected'] if x['id']==pair['left']);right=next(x for x in request['selected'] if x['id']==pair['right']);v={i:int(c) for i,c in left['coefficients']}
     for i,c in right['coefficients']:v[i]=v.get(i,0)+pair['sign']*int(c)
     normalized=normalize_vector(v)
     if 'coefficients' in row:assert row['coefficients']==normalized
     if row.get('already_in_pool') is not None:assert row['already_in_pool']==any(x['coefficients']==normalized for x in meta_ref['directions'])
    if row.get('certificate_complete'):
     ind=IndependentDomains(ast,models[request['position']-1],row['coefficients']);u=ind.audit(row);record['verified']=True;record['domain']=packed(u);record['blocked']=u==[(0,0)];record['blockers']=ind.summary();certs.append(record)
     if row['kind']=='original':assert row['root_domain']==old['old_domain'];originals[row['direction_id']]=record
     if row.get('nonzero_domain_found'):assert int(row['parameter'])==nearest(u)
     if row.get('legal_witness_verified'):
      q=tuple(row['assignment']);ql,obs=inspect(q);assert ql;anc=list(map(int,models[request['position']-1]));direction={v:int(c) for v,c in row['coefficients']};assert list(map(int,q))==[x+int(row['parameter'])*direction.get(i,0) for i,x in enumerate(anc)]
      if 'protected_missing' in row:
       hist=set()
       for m in models[:request['position']-1]:hist|=inspect(tuple(m))[1]
       native=inspect(tuple(models[request['position']-1]))[1];assert masks(row['actual_observations'])==obs;assert set(map(tuple,row['protected_missing']))==(native-hist)-obs
       gain=(covered(hist|obs)-covered(hist),len(obs-hist));assert list(gain)==row['gain'];assert row['preserved']==((native-hist)<=obs);assert row['covered_gain']==(row['preserved'] and gain[0]>covered(hist|native)-covered(hist))
      if row['kind']=='combination':
       pair=row['pair'];record['B2']=within and all(originals.get(pair[x],{}).get('blocked',False) and originals.get(pair[x],{}).get('within_request_cap',False) for x in ['left','right']) and not row.get('already_in_pool',False);record['B3']=record['B2'] and row.get('covered_gain',False)
     record.update({k:row.get(k,False) for k in ['nonzero_domain_found','legal_witness_verified','preserved','covered_gain']})
    real_rows.append(record)
   write(out/(d.name+'_diagnosis.json'),{'records':[r for r in real_rows if r['position']==request['position']],'terminal':terminal,'truncated':trunc,'costs':summary.get('costs',[])})
write(out/'sequences.json',summaries);write(out/'events.json',events_table);write(out/'preprocess.json',pre_table);write(out/'certificates.json',certs);write(out/'real_funnel.json',real_rows)
csvwrite(out/'prefixes.csv',prefixes);csvwrite(out/'preprocess.csv',pre_table)
write(out/'summary.json',{'passed':True,'sequences':len([x for x in summaries if x['stage']=='offline']),'probes':len([x for x in summaries if x['stage']=='probes']),'source_models':43,'replayed_events':sum(x['counts']['events'] for x in summaries if x['stage']=='offline'),'official_audit_calls':official_calls,'distinct_formula_assignment_objects':len(distinct),'complete_candidate_audits':candidate_checks,'full_equality_row_checks':equalities_checked,'complete_certificates':len(certs),'diagnostic_records':len(real_rows),'B2':sum(x['B2'] for x in real_rows),'B3':sum(x['B3'] for x in real_rows),'historical_cpu_credit_proven':False,'real_solver_checks':0})
print('independent audit PASS',read(out/'summary.json'),flush=True)
