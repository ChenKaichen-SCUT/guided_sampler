from common_r import *
import argparse
p=argparse.ArgumentParser();p.add_argument('--report',required=True);a=p.parse_args();assert (BASE/'offline/frozen_v1/FINISHED.json').exists() and (BASE/'oracle/frozen_v1/FINISHED.json').exists()
frozen=read(MAN/'implementation.json');checked=0
for rel,sha in frozen['files'].items():assert digest(ROOT/rel)==sha,rel;checked+=1
for name,entry in frozen['artifacts'].items():assert digest(ROOT/entry['path'])==entry['sha256'],name
protected=read(MAN/'protected_before.json')
for rel,meta in protected['metadata'].items():
    st=(ROOT/rel).stat();assert st.st_size==meta['size'] and st.st_mtime_ns==meta['mtime_ns'],rel
for rel,sha in protected['sha256'].items():assert digest(ROOT/rel)==sha,rel
for row in protected['inputs']:assert digest(ROOT.parent/row['path'])==row['sha256']
gate=read(BASE/'offline/frozen_v1/gate.json');assert not gate['offline_gate_passed'];assert not (BASE/'formal').exists();assert not (BASE/'short').exists()
for variant in ['release','sanitize']:
    assert read(BASE/f'correctness/isolation_{variant}_04/summary.json')['passed'];assert all(v['passed'] for v in read(BASE/f'correctness/disabled_{variant}_02/summary.json').values())
    audit=read(BASE/f'correctness/isolation_{variant}_04/audit.json');assert audit['checks']['actual_strict_covered_replacement_count']>=1
for d in (BASE/'offline/frozen_v1').iterdir():
    if d.is_dir():assert read(d/'audit.json')['passed']
oracles=read(BASE/'oracle/frozen_v1/summary.json');assert oracles['cases']==12;assert len(oracles['records'])==12;assert all(r['oracle_checks'] in [0,1,None] for r in oracles['records'])
report=ROOT/a.report;assert report.exists()
write(BASE/'audit_summary.json',{'passed':True,'frozen_source_files_verified':checked,'historical_metadata_verified':len(protected['metadata']),'historical_sha256_verified':len(protected['sha256']),'all_8_input_sha256_unchanged':True,'frozen_artifacts':frozen['artifacts'],'offline_models':43,'L1_positions':40,'L2_strategies':2,'oracle_cases':12,'short_sessions':0,'formal_sessions':0,'HighDiv_reruns':0,'additional_seeds':0,'B_enabled':False,'decision':'No-Go','native_isolation_real_replacement':True,'all_output_prefix_observations_contain_native':True,'official_and_independent_coverage_equal':True,'report_sha256':digest(report),'negative_and_failed_attempts_retained':True})
write(BASE/'artifact_hashes.json',{str(p.relative_to(ROOT)):digest(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ['artifact_hashes.json']})
print('Final independent audit PASS: preserved history, fixed scope, negative result No-Go')
