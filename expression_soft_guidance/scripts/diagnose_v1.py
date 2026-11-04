"""Classify actual V1 targets, costs and coverage gains without throughput scoring."""
import json,statistics,collections
from prepare import ROOT,write
folder=ROOT/'results/comparison_v5_t30';out=[]
for p in sorted(folder.glob('*__soft_budget__*/run.json')):
    r=json.loads(p.read_text());d=p.parent
    qs=[json.loads(x) for x in (d/'queries.jsonl').read_text().splitlines()]
    receipts=[x for x in map(json.loads,(d/'receipts.jsonl').read_text().splitlines()) if x.get('accepted')]
    models={x['query']:x for x in receipts if x['source']=='CDCL'}
    targets=[q for q in qs if 'target' in q]
    costs=lambda q:q['check_complete']-q['start']-q['preparation_wall']
    stats=collections.defaultdict(lambda:dict(calls=0,seconds=0,gain=0,hits=0,sat=0))
    for q in targets:
        t=q['target'];category='bool' if len(t['bits'])==1 and t['auxiliaries']==0 else 'int'
        key=(category, max(t['bits'])//8)
        s=stats[key];s['calls']+=1;s['seconds']+=costs(q);s['sat']+=q['result']=='sat'
        if q['query'] in models:s['gain']+=models[q['query']]['gain'];s['hits']+=q.get('model_goal_hits',0)
    long=sorted(qs,key=costs,reverse=True)[:5]
    out.append(dict(bench=r['bench'],seed=r['seed'],queries=len(qs),target_queries=len(targets),repeated_targets=len(targets)-len({q['target']['node'] for q in targets}),cdcl_seconds=sum(map(costs,qs)),preparation_seconds=sum(q['preparation_wall'] for q in qs),direct_hits=sum(q.get('model_goal_hits',0) for q in targets if q['query'] in models),cdcl_gain=sum(m['gain'] for m in models.values()),by_kind_high_byte={str(k):v for k,v in stats.items()},longest=[dict(query=q['query'],seconds=costs(q),result=q['result'],target=q.get('target'),gain=models.get(q['query'],{}).get('gain')) for q in long]))
write(ROOT/'results/V1_target_diagnosis.json',json.dumps(out,indent=2)+'\n')
for r in out:print(json.dumps({k:v for k,v in r.items() if k not in ['longest','by_kind_high_byte']},ensure_ascii=False))
