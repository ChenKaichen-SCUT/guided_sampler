#!/usr/bin/env python3
from common import *
from finalize_samples import finalize,records
from evaluate_official import evaluate
import collections,concurrent.futures,traceback
def rows(path):
 if not path.exists():return
 with path.open() as f:
  for line in f:
   try:yield json.loads(line)
   except json.JSONDecodeError:break
def audit(run):
 d=ROOT/run['output'];r={'id':run['id'],'mode':run['mode'],'input':run['input_name'],'errors':[]}
 try:
  final=finalize(d,900,run['limit']);metrics=evaluate(d,ROOT/run['input']);assert metrics=={'official_exit':0,'exact_exit':0},metrics
  ex=read(d/'exact.json');assert ex['legal'] and ex['models']==final['formal_count'];assert ex['official_class_result'] in (d/'wire_coverage.stdout').read_text()
  cmd=[python(),ROOT/'scripts/audit_round2_targets.py',d,ROOT/run['input']]
  with (d/'target_audit.stdout').open('x') as out,(d/'target_audit.stderr').open('x') as err:p=subprocess.run(cmd,stdout=out,stderr=err)
  assert p.returncode==0,'independent target audit failed';target=read(d/'target_audit.json')
  counts=collections.Counter();funnel=collections.Counter();backend=collections.Counter();qc=collections.Counter();cost=collections.Counter();requests=0;registered=0;max_mappable=0;reason=collections.Counter();stages=collections.Counter();action_count=0;supported_queries=set();metadata_queries=set()
  for x in rows(d/'a_requests.jsonl'):
   requests+=1;registered+=x['has_request'];max_mappable=max(max_mappable,x.get('A_mappable_targets') or 0)
  for x in rows(d/'a_backend_calls.jsonl'):
   if x.get('kind')=='tactic_stages':
    stages.update(s['tactic_name'] for s in x['stages']);continue
   metadata_queries.add(x['query_id'])
   if x['entry_function'] in ('check','setup_and_check') and not x.get('disabled_reason'):supported_queries.add(x['query_id'])
   backend[x['tactic_name']+'/'+x['entry_function']]+=1;counts['metadata_received']+=bool(x['metadata_received']);counts['supported_SMT_calls']+=(x['entry_function'] in ('check','setup_and_check') and not x.get('disabled_reason'));funnel.update(x.get('funnel',{}))
   assert not x.get('ls_sampling',False),'A reached CCSS'
  for q in rows(d/'queries.jsonl'):
   qc[q['source']+'_'+q['result']]+=1;cost[q['source']+'_check_seconds']+=q['check_seconds'];g=q.get('guidance',{});reason[q['reason_unknown']]+=int(q['result']=='unknown')
   if not g:continue
   assert q['source']=='CDCL';assert g['suggestions']<=4
   for k in ('b_encoded','b_internalized','b_selected','guidance_created_bool_vars','guidance_added_assertions','guidance_marked_relevant'):assert g[k]==0,k
   counts['suggestions']+=g['suggestions'];counts['phase_overrides']+=g['phase_overrides'];counts['ordinary']+=g['ordinary'];counts['intervened_checks']+=bool(g['intervened_check']);counts['exposure_limit_queries']+=bool(g['exposure_limit'])
   attempted={}
   for a in g['actions']:
    assert a['native_var']==a['actual_var'] and a['decision_id']<=64
    assert a['phase_changed']==(a['effective_phase']!=a['native_phase']);assert a['effective_phase']==a['suggested_phase']
    for t in a['support']:
     n=t['node'];one=int(t['desired_one_mask']);zero=int(t['desired_zero_mask']);old=attempted.get(n,(0,0));assert not (old[0]&one or old[1]&zero);attempted[n]=(old[0]|one,old[1]|zero)
  mapping=collections.Counter()
  for a in rows(d/'a_actions.jsonl'):
   action_count+=1;counts['popped']+=bool(a['trailed_assignment_popped']);counts['reassigned_same']+=a['reassigned_same'];counts['reassigned_opposite']+=a['reassigned_opposite'];counts['same_phase_suggestions']+=not a['would_override'];mapping[a['mapping_kind']]+=1
  assert action_count==counts['suggestions'];host=read(d/'summary.json') if (d/'summary.json').exists() else {};terminal=read(d/'terminal.json');assert terminal['exit_code'] in (0,-15,-9)
  if 'formal_count' in host:assert host['formal_count']==ex['models']
  last={}
  for ledger in rows(d/'cost_ledger.jsonl'):last=ledger
  sources=collections.Counter(p['source'] for p in ex['prefixes']);times=[p['commit_complete'] for p in ex['prefixes']];last_t=0;last_c=0;auc=0
  for p in ex['prefixes']:auc+=(p['commit_complete']-last_t)*last_c;last_t=p['commit_complete'];last_c=p['covered']
  auc+=(900-last_t)*last_c
  for model in rows(d/'models.jsonl'):assert model.get('legal') is not False
  lib=ROOT/'deps/round2_release/lib/libz3.so';loaded=(d/'loaded_library.txt').read_text();assert str(lib) in loaded
  r.update(valid=True,models=ex['models'],covered=ex['covered'],total=ex['total'],percentage=100*ex['covered']/ex['total'],official=ex['official_class_result'],auc_percentage=100*auc/900/ex['total'],complete100=ex['models']>=100,time100=times[99] if len(times)>=100 else None,first_model=times[0] if times else None,source_models=dict(sources),status=host.get('status'),terminal=terminal,queries=dict(qc),unknown_reasons=dict(reason),requests=requests,registered=registered,max_mappable=max_mappable,supported_queries=len(supported_queries),metadata_queries=len(metadata_queries),counts=dict(counts),funnel=dict(funnel),backend=dict(backend),stages=dict(stages),mapping=dict(mapping),costs=dict(cost),ledger=last,host=host,target_audit=target,late=sum(x['reason']=='late' for x in final['omitted']),omitted=dict(collections.Counter(x['reason'] for x in final['omitted'])),time_curve={str(t):next((p['covered'] for p in reversed(ex['prefixes']) if p['commit_complete']<=t),0) for t in [1,5,10,30,60,120,300,600,900]},sample_curve={str(n):ex['prefixes'][n-1]['covered'] if len(times)>=n else None for n in [1,2,5,10,20,50,100]})
 except Exception as e:r['valid']=False;r['errors'].append(str(e));(d/'audit_exception.txt').write_text(traceback.format_exc())
 write(d/'audit.json',r);write(d/'artifact_hashes.json',{str(p.relative_to(d)):digest(p) for p in sorted(d.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'});print(run['id'],r['valid'],r['errors'],flush=True);return r
def main():
 root=ROOT/'results/round2_a';assert (root/'QUEUE_FINISHED.json').exists();plan=read(ROOT/'manifests/round2_a_plan.json')
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(audit,plan['runs']))
 exclusive(root/'audit_summary.json',{'count':len(results),'passed':all(r['valid'] for r in results),'runs':results});assert all(r['valid'] for r in results)
if __name__=='__main__':main()
