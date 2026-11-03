from common_bd import *
from runner import stream_rows
from check_blocking import intersection,unpacked,packed,ALL
import collections
assert read(BASE/'analysis/audit_v1/summary.json')['passed'];data=read(ROOT/'results/refinement/offline/inputs_v1/SMT_real.json');ns=data['ast']['nodes'];mandatory=set();todo=[0]
while todo:
 n=todo.pop()
 if n in mandatory:continue
 mandatory.add(n)
 if ns[n]['op']=='and':todo.extend(ns[n]['children'])
records=[];nonzero=[];clock=[];protected=[]
for d in sorted((BASE/'real_diagnosis/frozen_v1').glob('SMT_real_*')):
 rs,trunc=stream_rows(d/'stream.jsonl');position=int(d.name[-2:]);summary=next(x for x in rs if x['kind']=='summary');terminal=read(d/'terminal.json');pre=next(x for x in rs if x['kind']=='preprocess');orig=next(x for x in rs if x['kind']=='original_phase');inp=next(x for x in rs if x['kind']=='input')
 clock.append({'position':position,'preprocess_cpu':pre['cpu'],'preprocess_wall':pre['wall'],'original_phase_cpu':orig['cpu'],'original_phase_wall':orig['wall'],'combination_phase_cpu':summary['combination_phase_cpu'],'combination_phase_wall':summary['combination_phase_wall'],'parse_prefix_cpu':inp['parse_prefix_cpu'],'parse_prefix_wall':inp['parse_prefix_wall'],'process_cpu':terminal['user_cpu']+terminal['system_cpu'],'process_wall':terminal['parent_wall'],'rss_kb':terminal['max_rss_kb'],'max_certificate_allowance':max(x.get('certificate_storage_allowance',0) for x in rs)})
 for r in rs:
  if r['kind'] not in ['original','combination'] or not r.get('certificate_complete'):continue
  if r['kind']=='original' and r['root_domain']==[['0','0']]:
   domain=ALL.copy();atoms=[]
   for n in r['certificate']:
    if n['node'] in mandatory and n['operation'] in ['eq','distinct','le','lt','ge','gt']:
     domain=intersection(domain,unpacked(n['domain']));atoms.append(n['node'])
   records.append({'position':position,'direction':r['direction_id'],'mandatory_atom_domain':packed(domain),'mandatory_atoms_alone_prove_singleton_zero':domain==[(0,0)],'mandatory_atom_nodes':atoms})
  if r.get('nonzero_domain_found'):
   nonzero.append({'position':position,'kind':r['kind'],'direction':r.get('direction_id'),'ordinal':r.get('ordinal'),'domain':r['root_domain'],'parameter':r['parameter'],'legal':r['legal_witness_verified'],'preserved':r['preserved'],'covered_gain':r['covered_gain'],'gain':r.get('gain'),'native_gain':inp['native_gain'],'protected_missing':r.get('protected_missing'),'protected_count':inp['protected_count']})
write(BASE/'analysis/real_scope_summary.json',{'root_singletons':len(records),'mandatory_atoms_alone':sum(x['mandatory_atoms_alone_prove_singleton_zero'] for x in records),'requires_more_boolean_structure':sum(not x['mandatory_atoms_alone_prove_singleton_zero'] for x in records),'records':records,'nonzero_witnesses':nonzero,'worker_costs':clock,'new_workers':0,'real_solver_checks':0});print('scope diagnosis',len(records),sum(x['mandatory_atoms_alone_prove_singleton_zero'] for x in records),'nonzero witnesses',len(nonzero))
