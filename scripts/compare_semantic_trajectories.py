#!/usr/bin/env python3
"""Visible-history fingerprints; no claim to reconstruct missing internal state."""
from common import *
BASE=ROOT/'results/round3_semantics'
def records(path):return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
def fingerprint(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def trajectory(d):
 models={r['query']:r['model_hash'] for r in records(d/'formal_receipts.jsonl')}
 actions={}
 for r in records(d/'a_actions.jsonl'):actions.setdefault(r['query_id'],[]).append({k:r[k] for k in ['decision_id','native_var','native_phase','suggested_phase','effective_phase','canonical_key','coverage_version','support']})
 return [{'query':q['query'],'source':q['source'],'assumptions':q['assumptions'],'seed':q['highdiv_ls_seed'],'result':q['result'],'model_hash':models.get(q['query']),'actions':actions.get(q['query'],[])} for q in records(d/'queries.jsonl')]
def compare(left,right):
 prefix=[];first=None
 for i,(a,b) in enumerate(zip(left,right)):
  if a!=b:first={'position':i,'left_query':a['query'],'right_query':b['query'],'different_fields':[k for k in a if a[k]!=b[k]],'left_sha256':fingerprint(a),'right_sha256':fingerprint(b)};break
  prefix.append(fingerprint(a))
 if first is None and len(left)!=len(right):first={'position':min(len(left),len(right)),'different_fields':['trace_length'],'left_length':len(left),'right_length':len(right)}
 return {'equal_visible_prefix_count':len(prefix),'prefix_sha256':fingerprint(prefix),'first_observable_divergence':first,'full_internal_state_reconstructed':False}
result={}
for name in ['convert','SMT_random','SMT_real']:
 obs=trajectory(BASE/'traces'/(name+'_observe_trace'));app=trajectory(BASE/'traces'/(name+'_apply_trace'));result[name+'_observe_vs_apply']=compare(obs,app)
old=trajectory(ROOT/'results/round2_a/formal/time900/04');new=trajectory(BASE/'traces/convert_apply_trace');result['historical_convert_vs_new_apply']=compare(old,new);anchors=[]
for q,d in [(5,25),(7,30),(11,64)]:
 olda=[a for row in old if row['query']==q for a in row['actions'] if a['decision_id']==d];newa=[a for row in new if row['query']==q for a in row['actions'] if a['decision_id']==d];same=olda==newa and bool(olda);anchors.append({'query_id':q,'decision_id':d,'same_visible_action':same,'historical_full_state':'not_verifiable_from_old_logs' if same else 'historical_trace_not_reproduced','reason':'Old logs did not retain the complete native decision prefix/RNG/internal state. Matching query numbers or action fields alone is not a state reproduction.','old_action':olda,'new_action':newa})
result['historical_anchors']=anchors;result['fingerprint_scope']='All committed model hashes including CCSS, original assumptions, results, LS seeds and visible A actions; resource deadlines are separately recorded and intentionally differ from historical 900s runs.';write(BASE/'analysis/trajectory_comparison.json',result);print(json.dumps(result,ensure_ascii=False))
