import json,argparse
from prepare import ROOT,write
ap=argparse.ArgumentParser();ap.add_argument('name');args=ap.parse_args();folder=ROOT/'results'/args.name
runs=json.loads((folder/'runs.json').read_text());groups={};report=[]
for r in runs:groups.setdefault((r['bench'],r['seed']),{})[r['mode']]=r
def rows(r):
    path=folder/(r['bench'][:-5]+'__'+r['mode']+'__s'+str(r['seed']))/'receipts.jsonl'
    return [(e['source'],e['assignment']) for e in map(json.loads,path.read_text().splitlines()) if e.get('accepted')]
for (bench,seed),modes in groups.items():
    if 'baseline' not in modes:continue
    base=rows(modes['baseline'])
    for mode in ['native','observe','route']:
        if mode not in modes:continue
        other=rows(modes[mode]);n=min(len(base),len(other));equal=base[:n]==other[:n]
        report.append(dict(bench=bench,seed=seed,mode=mode,compared_models=n,identical=equal))
write(folder/'prefix_equivalence.json',json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if any(not x['identical'] for x in report):raise SystemExit(1)
