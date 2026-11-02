"""Read frozen HighDiv receipts; do not execute or rescore the baseline."""
from common6 import *
assert (BASE/'F_FINISHED.json').exists()
out=BASE/'formal_analysis';out.mkdir(exist_ok=True);result=[]
for i,entry in enumerate(read(ROOT/'manifests/inputs.json')):
    for budget in ['time900','n100_t900']:
        p=ROOT/'results/baseline_seed0_v1/highdiv'/budget/f'{i:02}'/'formal_receipts.jsonl';counts=collections.Counter()
        with p.open() as f:
            for line in f:counts[json.loads(line).get('source','not_recorded')]+=1
        result.append({'input_index':i,'instance':pathlib.Path(entry['path']).name,'budget':budget,'formal_sources':dict(counts),'receipt_sha256':digest(p),'new_baseline_runs':0})
csvwrite(out/'historical_sources.csv',result);write(out/'historical_sources.json',result)
print('Read16 frozen baseline source counters, no sampler execution')
