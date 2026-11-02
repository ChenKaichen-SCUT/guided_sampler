"""Post-F source/duplicate and diagnostic-volume diagnosis; no solver calls."""
from common6 import *
assert (BASE/'F_FINISHED.json').exists();out=BASE/'formal_analysis';records=[]
names=['samples.raw','sample_receipts.jsonl','queries.jsonl','models.jsonl','semantic_host.jsonl','coverage_snapshots.jsonl','reference_sources.jsonl','query_inputs.jsonl','ccss_guard.jsonl','ccss_guard_host.jsonl','cost_ledger.jsonl']
for j in read(ROOT/'manifests/round6_formal_plan.json')['jobs']:
    d=BASE/'formal'/j['id'];c=collections.Counter()
    with (d/'sample_receipts.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['kind'] in ['prepare','reject']:
                c[r['source']+'_raw']+=1
                if r.get('duplicate'):c[r['source']+'_duplicates']+=1
    r=read(d/'run_analysis.json');sizes={name:(d/name).stat().st_size if (d/name).exists() else 0 for name in names}
    records.append({'run':j['id'],'input_index':j['input_index'],'instance':j['instance'],'budget':j['budget'],'mode':j['mode'],**c,'CDCL_formal':r['formal_CDCL'],'CCSS_formal':r['formal_CCSS'],'CDCL_raw_duplicate_fraction':c['CDCL_duplicates']/c['CDCL_raw'] if c['CDCL_raw'] else None,'listed_sampler_output_bytes':sum(sizes.values()),'output_bytes_by_file':sizes})
csvwrite(out/'source_mix_and_output_cost.csv',records);write(out/'source_mix_and_output_cost.json',{'rows':records,'sampler_output_files':names,'exact_offline_score_files_excluded':True,'new_solver_calls':0});print('Retained source mix and runtime output sizes32')
