"""Read-only phase and long-tail diagnosis, after timed sampling has stopped."""
import json,statistics
from prepare import ROOT,write
folder=ROOT/'results/comparison_v5_t30';reports=[]
for path in sorted(folder.glob('*/run.json')):
    run=json.loads(path.read_text());d=path.parent
    if not any(x in run['bench'] for x in ['convert','real','random','pb2010']):continue
    qs=[json.loads(s) for s in (d/'queries.jsonl').read_text().splitlines()]
    phases=[json.loads(s) for s in (d/'ccss.jsonl').read_text().splitlines()]
    models={s['query']:s for s in map(json.loads,(d/'receipts.jsonl').read_text().splitlines()) if s.get('accepted') and s['source']=='CDCL'}
    long=[]
    for s in sorted(phases,key=lambda s:s['complete']-s['start'],reverse=True)[:3]:
        model=models.get(s['query']);values=[abs(int(v)) for v in model['assignment'].values()] if model else []
        long.append(dict(query=s['query'],wall=s['complete']-s['start'],result=s['result'],kernel_seconds=s['kernel_seconds'],deadline_hit=s['deadline_hit'],preceding_model_max_bits=max((x.bit_length() for x in values),default=None),preceding_model_outside_signed64=sum(not -(1<<63)<=int(v)<(1<<63) for v in model['assignment'].values()) if model else None))
    times=sorted(q['check_complete']-q['start']-q.get('preparation_wall',0) for q in qs)
    reports.append(dict(bench=run['bench'],mode=run['mode'],seed=run['seed'],ccss_longest=long,cdcl_longest=times[-3:],cdcl_seconds=sum(times),ccss_seconds=sum(s['complete']-s['start'] for s in phases),kernel_seconds=[sum(s['kernel_seconds'][i] for s in phases) for i in range(6)]))
write(ROOT/'results/v5_diagnostics.json',json.dumps(reports,indent=2)+'\n')
