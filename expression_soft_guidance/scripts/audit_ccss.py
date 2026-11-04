"""Reconcile phase timing, budget aborts, model sources and explicit profiles."""
import argparse,json,statistics
from prepare import ROOT,write
ap=argparse.ArgumentParser();ap.add_argument('name');args=ap.parse_args();folder=ROOT/'results'/args.name
reports=[]
for p in sorted(folder.glob('*/run.json')):
    r=json.loads(p.read_text());d=p.parent;meta=json.loads((d/'metadata.json').read_text());summary=r['summary'];errors=[]
    phases=[json.loads(s) for s in (d/'ccss.jsonl').read_text().splitlines()]
    queries=[json.loads(s) for s in (d/'queries.jsonl').read_text().splitlines()]
    receipts=[json.loads(s) for s in (d/'receipts.jsonl').read_text().splitlines() if json.loads(s).get('accepted')]
    byquery={}
    for s in receipts:
        if s['source']=='CCSS':byquery.setdefault(s['query'],[]).append(s)
    off=meta['ccss_disabled'];costs=[];overshoots=[];kernels=[0.]*6;gains=0;hits=0
    if off and (phases or any(s['source']=='CCSS' for s in receipts)):errors.append('disabled CCSS executed')
    previous=0
    for i,s in enumerate(phases):
        if s['call']!=i+1 or not previous<=s['start']<=s['check_complete']<=s['complete']:errors.append('phase chronology')
        previous=s['complete'];costs.append(s['complete']-s['start'])
        kernels=[a+b for a,b in zip(kernels,s['kernel_seconds'])]
        gains+=s['covered_after']-s['covered_before'];hits+=s['deadline_hit']
        if s['deadline_hit'] and s['result']!='unknown':errors.append('timeout was not unknown')
        if s['budget_ms']>0:overshoots.append(max(0,(s['check_complete']-s['start'])*1000-s['budget_ms']))
        delivered=[x for x in byquery.get(s['query'],[]) if s['start']<=x['time']<=s['complete']]
        if len(delivered)!=s['models_after']-s['models_before']:errors.append('CCSS receipt accounting')
        if s['result']!='sat' and delivered:errors.append('non-SAT CCSS delivered model')
    if len(phases)!=summary['ccss_calls'] or hits!=summary['ccss_deadline_hits']:errors.append('CCSS summary counts')
    if abs(sum(costs)-summary['ccss_wall'])>1e-7:errors.append('CCSS summary time')
    for q in queries:
        if meta['feedback']=='hold' and 'target' in q and q['exchange_delivered']!=q['exchange_before']:errors.append('held map size changed')
        if 'exchange_projected' in q and q['exchange_delivered']!=q['exchange_projected']:errors.append('complete map size changed')
    reports.append(dict(bench=r['bench'],mode=r['mode'],seed=r['seed'],calls=len(phases),sat=sum(s['result']=='sat' for s in phases),deadline_hits=hits,ccss_wall=sum(costs),max_call=max(costs,default=0),max_overshoot_ms=max(overshoots,default=0),kernel_seconds=kernels,gain=gains,ccss_models=sum(x['source']=='CCSS' for x in receipts),errors=sorted(set(errors))))
out=dict(all_passed=all(not r['errors'] for r in reports),runs=reports)
write(folder/'ccss_audit.json',json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if not out['all_passed']:raise SystemExit(1)
