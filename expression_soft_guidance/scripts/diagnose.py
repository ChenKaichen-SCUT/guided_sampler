import argparse,json,statistics
from prepare import ROOT,write
ap=argparse.ArgumentParser();ap.add_argument('name');args=ap.parse_args();folder=ROOT/'results'/args.name
out=[]
for runpath in sorted(folder.glob('*/run.json')):
    run=json.loads(runpath.read_text());path=runpath.parent/'queries.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()]
    integers=[r for r in rows if r.get('target',{}).get('auxiliaries',0)]
    top=sorted(rows,key=lambda r:r.get('preparation_wall',0),reverse=True)[:3]
    out.append(dict(bench=run['bench'],mode=run['mode'],seed=run['seed'],integer_target_queries=len(integers),max_preparation=max([r.get('preparation_wall',0) for r in rows],default=0),slowest_preparations=[{k:r[k] for k in ['query','preparation_wall','target'] if k in r} for r in top]))
write(folder/'diagnosis.json',json.dumps(out,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='slowest_preparations'} for r in out],indent=2))
