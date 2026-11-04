"""Summarize paired runs without treating prefixes as independent n20 trials."""
import json,statistics,collections
from prepare import ROOT,write
time_name='comparison_v3_t30';sample_name='comparison_v3_n20'
time_data=json.loads((ROOT/'results'/time_name/'audit.json').read_text());sample_data=json.loads((ROOT/'results'/sample_name/'audit.json').read_text())
groups=collections.defaultdict(dict)
for r in time_data['runs']:groups[r['bench']].setdefault(r['mode'],[]).append(r)
short=lambda n: 'Bromberger' if 'Bromberger' in n else 'CAV' if 'CAV' in n else 'random' if 'random' in n else 'real' if 'real' in n else 'convert' if 'convert' in n else 'dillig' if 'dillig' in n else 'pb' if 'pb2010' in n else 'prime'
rows=[];delta=[];release_delta=[];scope_delta=[]
for name,modes in groups.items():
    avg=lambda mode,key:statistics.mean(r[key] for r in modes[mode])
    d=100*(avg('soft','coverage')-avg('baseline','coverage'));delta.append(d)
    rd=100*(avg('soft_release','coverage')-avg('baseline','coverage'));release_delta.append(rd)
    sd=100*(avg('scope','coverage')-avg('baseline','coverage'));scope_delta.append(sd)
    rows.append(dict(benchmark=short(name),baseline_models=avg('baseline','models'),soft_models=avg('soft','models'),baseline_coverage=100*avg('baseline','coverage'),soft_coverage=100*avg('soft','coverage'),delta_pp=d,scope_delta_pp=sd,release_delta_pp=rd))
pairs=collections.defaultdict(dict)
for r in sample_data['runs']:pairs[(r['bench'],r['seed'])][r['mode']]=r
n20=[]
for (name,seed),modes in pairs.items():
    for mode in ['soft','soft_release']:
        b=modes['baseline'];r=modes[mode];complete=b['models']==20 and r['models']==20
        n20.append(dict(benchmark=short(name),seed=seed,mode=mode,baseline_models=b['models'],models=r['models'],complete=complete,delta_pp=100*(r['coverage']-b['coverage']) if complete else None,baseline_seconds=b['sampling_wall'],seconds=r['sampling_wall']))
definitions=json.loads((ROOT/'results/comparison_v3_definitions_t30/audit.json').read_text())
allruns=time_data['runs']+sample_data['runs']+definitions['runs'];summary=dict(time_rows=rows,time_equal_instance_delta_pp=statistics.mean(delta),time_release_delta_pp=statistics.mean(release_delta),time_scope_delta_pp=statistics.mean(scope_delta),n20=n20,checked_models=sum(r['models'] for r in allruns),history_checks=sum(r['history_checks'] for r in allruns),goal_checks=sum(r['independent_goal_checks'] for r in allruns),target_hits=sum(r['target_hits'] for r in time_data['runs'] if r['mode']=='soft'),preferred_decisions=sum(r['preferred_decisions'] for r in time_data['runs'] if r['mode']=='soft'),all_passed=time_data['all_passed'] and sample_data['all_passed'] and definitions['all_passed'])
summary['runs']=len(allruns)
summary['n20_completed_summary']={}
for mode in ['soft','soft_release']:
    selected=[r for r in n20 if r['mode']==mode and r['complete']];d=[r['delta_pp'] for r in selected]
    summary['n20_completed_summary'][mode]=dict(pairs=len(d),wins=sum(x>0 for x in d),ties=sum(x==0 for x in d),losses=sum(x<0 for x in d),mean_delta_pp=statistics.mean(d))
write(ROOT/'results/final_summary.json',json.dumps(summary,indent=2)+'\n')
lines=['| 输入 | HighDiv 模型数 | soft 模型数 | HighDiv 覆盖率 | soft 覆盖率 | soft Δ百分点 | scope Δ百分点 | release Δ百分点 |','|---|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:lines.append('| {benchmark} | {baseline_models:.1f} | {soft_models:.1f} | {baseline_coverage:.4f}% | {soft_coverage:.4f}% | {delta_pp:+.4f} | {scope_delta_pp:+.4f} | {release_delta_pp:+.4f} |'.format(**r))
lines+=['',f'输入等权平均 soft Δ：{statistics.mean(delta):+.6f} 个百分点；release Δ：{statistics.mean(release_delta):+.6f} 个百分点。','', '| 输入 | seed | 模式 | HighDiv N | 新 N | 完成等样本比较 | Δ百分点 | HighDiv 秒 | 新秒 |','|---|---:|---|---:|---:|---|---:|---:|---:|']
for r in n20:lines.append(f"| {r['benchmark']} | {r['seed']} | {r['mode']} | {r['baseline_models']} | {r['models']} | {'是' if r['complete'] else '否'} | {format(r['delta_pp'],'+.4f') if r['complete'] else 'NA'} | {r['baseline_seconds']:.3f} | {r['seconds']:.3f} |")
write(ROOT/'results/tables.zh.md','\n'.join(lines)+'\n');print(json.dumps(summary,indent=2))
