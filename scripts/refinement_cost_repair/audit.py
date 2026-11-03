"""Independent integer/official-observer audit. Never calls a real solver."""
from common_cr import *
from independent import observations,evaluate,covered,official_trace,export
from runner import stream_rows
import collections,functools,z3
out=attempt('analysis','audit_v1');cfg=read(ROOT/'configs/refinement_cost_repair.json');all_summaries=[];partitions=[];losses=[];unique_official=0;candidate_checks=0;metadata_by_instance={};probe_comparison=[]

def masks(js):return {(i,b,v) for i,z,o,*rest in js for b in range(64) for v in (0,1) if (o if v else z)>>b&1}
for name in ['convert','SMT_random','SMT_real']:
 data=read(ROOT/'results/refinement/offline/inputs_v1'/f'{name}.json');ast=data['ast'];models=data['models'];root=z3.And(z3.parse_smt2_file(data['input']));aa,ns,vs=export(root);assert aa['nodes']==ast['nodes'] and aa['variables']==ast['variables']
 @functools.lru_cache(maxsize=32)
 def inspect(m):
  global unique_official
  legal,tr=evaluate(ast,m);ok,official=official_trace(root,{v['name']:int(x) for v,x in zip(ast['variables'],m)});assert ok==legal and official=={i:value for i,(bits,value) in tr.items()};unique_official+=1
  _,obs=observations(ast,m);return legal,obs
 first=inspect(tuple(models[0]))[1];first_bits={(i,b) for i,b,v in first};known=set()
 for entry in rows(ROOT/'results/round5/W'/f'{name}_S_ref/a_atom_catalog.jsonl'):
  for rule in entry['rules']:
   mask=int(rule['known_zero'])|int(rule['known_one']);known.update((rule['node'],bit) for bit in range(64) if mask>>bit&1)
 universe={(i,b) for i,n in enumerate(ast['nodes']) for b in range(1 if n['sort']=='Bool' else 64)};groups={'G1':known&first_bits,'G2':first_bits-known,'G3':universe-first_bits};assert sum(map(len,groups.values()))==len(universe)
 jobs=[]
 for stage in ['probes/legacy_v1','probes/new_v1','offline/frozen_v1']:
  for d in sorted((BASE/stage).glob(name+'_*')):
   if d.is_dir() and (d/'attempt.json').exists():jobs.append((stage,d))
 for stage,d in jobs:
  job=read(d/'attempt.json');rs,truncated=stream_rows(d/'stream.jsonl');assert not truncated;pre=next((r for r in rs if r['kind']=='preprocess'),None);metas=[r['metadata'] for r in rs if r['kind']=='metadata'];events=[r for r in rs if r['kind']=='event'];costs={r['native_event_id']:r for r in rs if r['kind']=='event_cost'};summary=next((r for r in rs if r['kind']=='summary'),{});terminal=read(d/'terminal.json');probe=stage.startswith('probes');l1=probe or job.get('layer')=='L1'
  if metas:
   meta=metas[0]
   if name in metadata_by_instance:assert meta==metadata_by_instance[name],('completed_metadata_mismatch',d)
   else:metadata_by_instance[name]=meta
  history=set();native_history=set();keys=set();counts=collections.Counter();positions=[];domains=[];timely_candidates=0;noncompleted=0
  for row in events:
   pos=row['native_event_id']
   # A partial last event without delivery accounting is retained, never scored.
   if pos not in costs:noncompleted+=1;continue
   cst=costs[pos];assert row['native_assignment']==models[pos-1];m=tuple(row['native_assignment']);legal,native=inspect(m);assert legal;protected=native-history;gain=(covered(history|native)-covered(history),len(native-history))
   if row['baseline_scored']:assert row['base_gain_covered']==gain[0] and row['base_gain_observed']==gain[1];assert masks(row['protected_masks'])==protected
   complete=[];unprotected=[]
   for c in row['candidates']:
    if c['kind']=='target':counts['target_records']+=1;counts['proposed_parameters']+=len(c.get('parameters',[]));continue
    counts['candidate_records']+=1;counts['candidate_'+c.get('reason','unclassified')]+=1
    if 'assignment' not in c:continue
    q=tuple(c['assignment']);ql,obs=inspect(q);assert ql,('illegal_candidate',d,pos,c)
    counts['legal_assigned_records']+=1
    if 'missing_observations' not in c:continue
    candidate_checks+=1
    missing=protected-obs;assert set(map(tuple,c['missing_observations']))==missing;assert masks(c['actual_observations'])==obs
    expected=(covered(history|obs)-covered(history),len(obs-history));assert expected==(c['gain_covered'],c['gain_observed']);duplicate=q in keys;assert duplicate==c['output_duplicate']
    if c.get('reason','').startswith('incomplete'):continue
    counts['complete_candidate_records']+=1
    better=expected>gain;reason='protected_observation_missing' if missing else 'output_duplicate' if duplicate else 'legal_not_better_than_native' if not better else 'eligible_strict_improvement';assert reason==c['reason'];counts['preserved' if not missing else 'rejected']+=1
    if not duplicate and better:
     unprotected.append(((-expected[0],-expected[1],c['direction_id'],abs(int(c['t'])),int(c['t'])),c))
     if not missing:complete.append(unprotected[-1])
    if missing and better:losses.append({'sequence':d.name,'stage':stage,'position':pos,'direction':c['direction_id'],'t':c['t'],'assignment':c['assignment'],'missing':c['missing_observations'],'gain':expected,'native_gain':gain})
   assert len(complete)<=row['completed_evaluations'];assert sum(c.get('reason') in ('protected_observation_missing','output_duplicate','legal_not_better_than_native','eligible_strict_improvement') for c in row['candidates'] if c['kind']=='candidate')==row['completed_evaluations']
   for label,choices in [('chosen',complete),('unprotected_chosen',unprotected)]:
    chosen=row[label];expected=min(choices,key=lambda x:x[0])[1] if choices else None;assert bool(chosen)==bool(expected),(d,pos,label)
    if chosen:assert chosen['assignment']==expected['assignment'] and chosen['direction']==expected['direction_id'] and chosen['t']==expected['t']
   if row['chosen']:
    counts['selected_replacements']+=1;ql,obs=inspect(tuple(row['chosen']['assignment']));assert protected<=obs and ql
    counts['strict_covered_replacements' if covered(history|obs)>covered(history|native) else 'one_sided_replacements']+=1
   if row['unprotected_chosen'] and row['unprotected_chosen']!=row['chosen']:counts['unprotected_choice_differs']+=1
   output=tuple(row['output_assignment']);expected=m if l1 or not row['chosen'] else tuple(row['chosen']['assignment']);assert output==expected;legal,obs=inspect(output);assert legal and protected<=obs
   duplicate=output in keys;assert duplicate==cst['output_duplicate'];counts['output_duplicates']+=duplicate;keys.add(output);history|=obs;native_history|=native
   assert native_history<=history and cst['prefix_contains_native'];assert cst['output_covered']==covered(history) and cst['native_covered']==covered(native_history);assert cst['output_count']==len(keys)
   counts['completed_evaluations']+=row['completed_evaluations'];counts['baseline_scored']+=row['baseline_scored'];counts['ranking_completed']+=bool(row['selected_direction_order']);counts['completed_domains']+=cst['trace']['completed_domains']
   for dr in row['directions']:
    counts['direction_'+dr['status']]+=1
    if 'intervals' in dr:domains.append({'position':pos,'direction':dr['direction_id'],'intervals':dr['intervals'],'targets':dr.get('selected_targets')})
   tails=next((t for t in summary.get('record_tails',[]) if t.get('native_event_id')==pos),{'wall':0,'cpu':0});overw=max(0,cst['wall']+tails['wall']-cst['wall_cap']);overc=max(0,cst['cpu']+tails['cpu']-cst['cpu_cap'])
   positions.append({'position':pos,'native_covered':covered(native_history),'output_covered':covered(history),'extra':covered(history)-covered(native_history),'completed_evaluations':row['completed_evaluations'],'reason':row['reason'],'cancellation':row['cancellation'],'cancellation_stage':cst['trace']['last_incomplete_stage'],'optional_wall':cst['wall']+tails['wall'],'optional_cpu':cst['cpu']+tails['cpu'],'overrun_wall':overw,'overrun_cpu':overc,'replacement':bool(row['chosen']),'diagnostic_only':probe,'L1_selection_only':l1})
  if not probe:assert len(positions)==len(models) and not noncompleted
  if summary:assert summary['native_covered']==covered(native_history) and summary['output_covered']==covered(history);assert summary['historical_cpu_credit_proven']==False
  native_bits={(i,b) for i,b,v in native_history if (i,b,1-v) in native_history};output_bits={(i,b) for i,b,v in history if (i,b,1-v) in history}
  for group,mask in groups.items():partitions.append({'stage':stage,'sequence':d.name,'group':group,'size':len(mask),'gain':len((output_bits-native_bits)&mask),'loss':len((native_bits-output_bits)&mask),'net':len(output_bits&mask)-len(native_bits&mask)})
  combined=collections.defaultdict(lambda:collections.Counter())
  for cost in [pre]+list(costs.values()):
   if cost:
    for st,r in cost['trace']['stages'].items():
     for key,value in r.items():
      if isinstance(value,(int,float)) and key not in ('current_node','current_direction'):combined[st][key]+=value
  item={'stage':stage,'sequence':d.name,'instance':name,'mode':job['mode'],'layer':job.get('layer','probe'),'repeat':job.get('repeat'),'component_only':job.get('component_only',False),'completed_events':len(positions),'counts':dict(counts),'preprocess':pre,'effective_preprocess_status':summary.get('effective_preprocess_status'),'summary':summary,'terminal':terminal,'native_covered':covered(native_history),'output_covered':covered(history),'extra':covered(history)-covered(native_history),'stages':dict(combined),'positions':positions,'historical_cpu_credit_proven':False}
  write(out/(stage.replace('/','_')+'_'+d.name+'.json'),item);all_summaries.append(item)
  if probe:probe_comparison.append({'instance':name,'mode':job['mode'],'domains':domains})
  # Independently run the frozen official command on each completed production
  # sequence. No solver calls, and none during the timing matrix.
  if not probe:
   od=out/'official'/d.name;od.mkdir(parents=True)
   for kind,ms in [('native',models),('output',[r['output_assignment'] for r in events if r['native_event_id'] in costs])]:
    path=od/(kind+'.samples');unique=[];seen=set()
    for m in ms:
     if tuple(m) not in seen:seen.add(tuple(m));unique.append(m)
    path.write_text(''.join(str(k)+': '+''.join(v['name']+':'+str(x)+';' for v,x in zip(ast['variables'],m))+'\n' for k,m in enumerate(unique)))
    cmd=[python(),metric_path(),'-s',path,'-f',data['input'],'-m','wire_coverage'];r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120);(od/(kind+'.stdout')).write_text(r.stdout);(od/(kind+'.stderr')).write_text(r.stderr);expected=covered(native_history) if kind=='native' else covered(history);assert r.returncode==0 and r.stdout.strip()==str(round(expected/len(universe)*100,2))+'%'
    write(od/(kind+'.command.json'),{'command':list(map(str,cmd)),'returncode':r.returncode,'metric_sha256':digest(metric_path()),'samples_sha256':digest(path),'input_sha256':ast['input_sha']})
 # Structural skipped-component audit; deliberately no rank/elimination/solver.
 if name=='SMT_random':
  meta=metadata_by_instance[name];skips=[c for c in meta['components'] if c['status']=='component_size_limit'];assert len(skips)==10 and len(meta['directions'])==0;struct=[]
  for c in skips:
   rr=[meta['equalities'][i] for i in c['rows']];lens=collections.Counter(len(r['coefficients']) for r in rr);struct.append({**c,'rank':'rank_unknown','row_length_distribution':dict(lens),'unit_coefficient_rows':sum(any(abs(int(v))==1 for _,v in r['coefficients']) for r in rr),'single_variable_definition_rows':sum(len(r['coefficients'])==1 and abs(int(r['coefficients'][0][1]))==1 for r in rr),'full_rows':rr})
  write(out/'random_skipped_structure.json',struct)
# Compare every completed domain/target record available on both probes.
comparisons=0
for name in ['convert','SMT_random','SMT_real']:
 xs={r['mode']:r['domains'] for r in probe_comparison if r['instance']==name}
 for left,right in [('Legacy','ValueCache'),('Legacy','Shared'),('ValueCache','Shared')]:
  a={(r['position'],r['direction']):r for r in xs[left]};b={(r['position'],r['direction']):r for r in xs[right]}
  for k in a.keys()&b.keys():
   assert a[k]['intervals']==b[k]['intervals']
   if a[k]['targets'] is not None and b[k]['targets'] is not None:assert a[k]['targets']==b[k]['targets']
   comparisons+=1
write(out/'summaries.json',all_summaries);write(out/'partitions.json',partitions);write(out/'protected_losses.json',losses)
write(out/'summary.json',{'passed':True,'source_models':43,'production_sequences':39,'replayed_events':sum(r['completed_events'] for r in all_summaries if r['stage'].startswith('offline')),'independent_completed_candidate_checks':candidate_checks,'unique_official_assignments_checked':unique_official,'completed_real_probe_domain_pairs':comparisons,'no_new_solver_checks':True,'historical_cpu_credit_proven':False});print('audit PASS',candidate_checks,unique_official,comparisons,flush=True)
