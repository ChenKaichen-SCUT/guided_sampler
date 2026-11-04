import collections,json,statistics
from prepare import ROOT,write
folder=ROOT/'results/comparison_v4_t30';runs=json.loads((folder/'runs.json').read_text());groups=collections.defaultdict(dict)
filters={};timings=[]
for r in runs:
    groups[r['bench']].setdefault(r['mode'],[]).append(r['summary']['models'])
    directory=folder/(r['bench'][:-5]+'__'+r['mode']+'__s'+str(r['seed']))
    if r['mode']=='soft':
        group=filters.setdefault(r['bench'],dict(static=set(),unsat=set(),proof_wall=[],probe_results=collections.Counter()))
        group['proof_wall'].append(r['summary']['filter']['proof_wall'])
        for row in map(json.loads,(directory/'impossible.jsonl').read_text().splitlines()):
            if row['kind']=='static':
                for b in range(64):
                    if (row['mask']>>b)&1:group['static'].add((row['node'],b))
            else:
                group['probe_results'][row['result']]+=1
                if row['result']=='unsat':group['unsat'].add((row['node'],row['bit'],row['desired']))
    if 'convert' in r['bench'] or 'real' in r['bench']:
        qs=list(map(json.loads,(directory/'queries.jsonl').read_text().splitlines()))
        gap=max([(b['start']-a['complete'],a['query'],b['query']) for a,b in zip(qs,qs[1:])],default=(0,0,0))
        timings.append(dict(bench=r['bench'],mode=r['mode'],seed=r['seed'],models=r['summary']['models'],preparation=sum(q['preparation_wall'] for q in qs),checks=sum(q['check_complete']-q['start']-q['preparation_wall'] for q in qs),largest_between_query_gap=gap,wall=r['summary']['wall']))
summary=dict(models={b:{m:statistics.mean(v) for m,v in ms.items()} for b,ms in groups.items()},filters={b:dict(static_unique_bits=len(r['static']),F_only_unsat_sides=len(r['unsat']),mean_proof_wall=statistics.mean(r['proof_wall']),probe_results=dict(r['probe_results'])) for b,r in filters.items()},timing_diagnostics=timings)
write(ROOT/'results/v4_diagnostics.json',json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='timing_diagnostics'},indent=2))
