"""Summarize completed v4 experiments without altering the archived v3 report."""
import json,statistics
from prepare import ROOT,write
time_name='comparison_v4_t30';sample_name='comparison_v4_n20'
audits={name:json.loads((ROOT/'results'/name/'audit.json').read_text()) for name in [time_name,sample_name]}
def groups(name):
    result={}
    for row in audits[name]['runs']:result.setdefault(row['bench'],{}).setdefault(row['mode'],[]).append(row)
    return result
def avg(rows,key):return statistics.mean(r[key] for r in rows)
time_rows=[]
for bench,modes in groups(time_name).items():
    row={'bench':bench,'modes':{m:{'models':avg(rs,'models'),'coverage_percent':100*avg(rs,'coverage'),'covered':avg(rs,'covered'),'target_hits':avg(rs,'target_hits'),'preparation_wall':avg(rs,'preparation_wall'),'cdcl_wall':avg(rs,'cdcl_wall')} for m,rs in modes.items()}}
    row['soft_vs_baseline_pp']=row['modes']['soft']['coverage_percent']-row['modes']['baseline']['coverage_percent']
    row['filter_vs_unfiltered_pp']=row['modes']['soft']['coverage_percent']-row['modes']['soft_unfiltered']['coverage_percent']
    time_rows.append(row)
sample_pairs=[]
for bench,modes in groups(sample_name).items():
    base={r['seed']:r for r in modes['baseline']}
    for mode,rows in modes.items():
        if mode=='baseline':continue
        for r in rows:
            b=base[r['seed']];complete=r['models']>=20 and b['models']>=20
            sample_pairs.append(dict(bench=bench,mode=mode,seed=r['seed'],complete=complete,base_models=b['models'],models=r['models'],delta_bits=r['checkpoints']['20']-b['checkpoints']['20'] if complete else None,last_sample=r['last_sample'],base_last_sample=b['last_sample']))
filter_audits={name:json.loads((ROOT/'results'/name/'impossible_audit.json').read_text()) for name in audits}
prefix=json.loads((ROOT/'results'/sample_name/'prefix_equivalence.json').read_text())
report=dict(time=time_rows,sample_pairs=sample_pairs,audit_passed=all(a['all_passed'] for a in audits.values()),filter_audit_passed=all(a['all_passed'] for a in filter_audits.values()),models_audited=sum(r['models'] for a in audits.values() for r in a['runs']),exclusion_certificates=sum(b['unique_proofs'] for a in filter_audits.values() for b in a['benches']),prefix_checks=len(prefix),prefix_passed=all(r['identical'] for r in prefix),mean_soft_delta_pp=statistics.mean(r['soft_vs_baseline_pp'] for r in time_rows))
write(ROOT/'results/v4_summary.json',json.dumps(report,indent=2)+'\n')
lines=['| 输入 | 基线样本 | 空接入样本 | 无过滤软指引样本 | 新软指引样本 | 基线覆盖% | 新覆盖% | Δ百分点 | 过滤贡献百分点 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in time_rows:
    m=r['modes'];short=r['bench'].split('.')[0]
    lines.append(f'| {short} | {m["baseline"]["models"]:g} | {m["route"]["models"]:g} | {m["soft_unfiltered"]["models"]:g} | {m["soft"]["models"]:g} | {m["baseline"]["coverage_percent"]:.5f} | {m["soft"]["coverage_percent"]:.5f} | {r["soft_vs_baseline_pp"]:+.5f} | {r["filter_vs_unfiltered_pp"]:+.5f} |')
write(ROOT/'results/v4_tables.zh.md','\n'.join(lines)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['time','sample_pairs']},indent=2))
