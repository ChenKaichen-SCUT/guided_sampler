"""Report complete CCSS ablations, keeping mechanism and infrastructure effects separate."""
import json,statistics
from prepare import ROOT,write
names=['comparison_v5_t30','comparison_v5_n20','confirmation_v5_t60']
audits={n:json.loads((ROOT/'results'/n/'audit.json').read_text()) for n in names}
phases={n:json.loads((ROOT/'results'/n/'ccss_audit.json').read_text()) for n in names}
def mean(rows,key):return statistics.mean(r[key] for r in rows)
def groups(rows):
    out={}
    for r in rows:out.setdefault(r['bench'],{}).setdefault(r['mode'],[]).append(r)
    return out
time_rows=[];phase_groups=groups(phases[names[0]]['runs'])
for bench,modes in groups(audits[names[0]]['runs']).items():
    arms={}
    for mode,rs in modes.items():
        ps=phase_groups[bench][mode]
        arms[mode]=dict(models=mean(rs,'models'),covered=mean(rs,'covered'),coverage_percent=100*mean(rs,'coverage'),coverage_29_percent=statistics.mean(100*r['time_checkpoints']['29']/r['total'] for r in rs),cdcl_wall=mean(rs,'cdcl_wall'),preparation_wall=mean(rs,'preparation_wall'),ccss_wall=mean(ps,'ccss_wall'),ccss_calls=mean(ps,'calls'),ccss_sat=mean(ps,'sat'),max_ccss=max(r['max_call'] for r in ps),max_overshoot_ms=max(r['max_overshoot_ms'] for r in ps),ccss_bits=statistics.mean(r['source_gains'].get('CCSS',0) for r in rs),cdcl_bits=statistics.mean(r['source_gains'].get('CDCL',0) for r in rs))
    time_rows.append(dict(bench=bench,modes=arms,vs_original_pp=arms['soft_complete']['coverage_percent']-arms['baseline']['coverage_percent'],vs_matched_pp=arms['soft_complete']['coverage_percent']-arms['base_complete']['coverage_percent'],vs_v4_pp=arms['soft_complete']['coverage_percent']-arms['soft']['coverage_percent']))
pairs=[]
for bench,modes in groups(audits[names[1]]['runs']).items():
    for control in ['baseline','base_complete']:
        bases={r['seed']:r for r in modes[control]}
        for r in modes['soft_complete']:
            b=bases[r['seed']];complete=b['models']>=20 and r['models']>=20
            pairs.append(dict(bench=bench,seed=r['seed'],control=control,complete=complete,models=r['models'],base_models=b['models'],delta_bits=r['checkpoints']['20']-b['checkpoints']['20'] if complete else None,seconds=r['last_sample'],base_seconds=b['last_sample']))
confirmation=[]
confirm=groups(audits[names[2]]['runs'])
for bench,modes in confirm.items():
    for seed in sorted({r['seed'] for r in modes['baseline']}):
        bymode={m:next(r for r in rs if r['seed']==seed) for m,rs in modes.items()}
        confirmation.append(dict(bench=bench,seed=seed,modes={m:{k:r[k] for k in ['models','coverage','covered','cdcl_wall','source_gains']} for m,r in bymode.items()},budget_vs_baseline_pp=100*(bymode['soft_budget']['coverage']-bymode['baseline']['coverage']),budget_vs_matched_pp=100*(bymode['soft_budget']['coverage']-bymode['base_budget']['coverage']),complete_vs_budget_pp=100*(bymode['soft_complete']['coverage']-bymode['soft_budget']['coverage'])))
result=dict(time=time_rows,sample_pairs=pairs,confirmation=confirmation,models_audited=sum(r['models'] for a in audits.values() for r in a['runs']),all_passed=all(a['all_passed'] for a in [*audits.values(),*phases.values()]),mean_vs_original_pp=mean(time_rows,'vs_original_pp'),mean_vs_matched_pp=mean(time_rows,'vs_matched_pp'),mean_vs_v4_pp=mean(time_rows,'vs_v4_pp'),mean_budget_vs_original_pp=statistics.mean(r['modes']['soft_budget']['coverage_percent']-r['modes']['baseline']['coverage_percent'] for r in time_rows),mean_budget_vs_matched_pp=statistics.mean(r['modes']['soft_budget']['coverage_percent']-r['modes']['base_budget']['coverage_percent'] for r in time_rows))
write(ROOT/'results/v5_summary.json',json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['time','sample_pairs','confirmation']},indent=2))
for r in time_rows:print(r['bench'],r['vs_original_pp'],r['vs_matched_pp'])
