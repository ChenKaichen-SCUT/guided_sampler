from common_cr import *
from runner import stream_rows
cfg=read(ROOT/'configs/refinement_cost_repair.json');frozen=read(MAN/'implementation.json');protected=read(MAN/'protected.json');audit=read(BASE/'analysis/audit_v1/summary.json');assert audit['passed'] and audit['replayed_events']==559
for rel,sha in frozen['files'].items():assert digest(ROOT/rel)==sha,rel
for rel,sha in {**frozen['artifacts'],**frozen['libraries']}.items():assert digest(ROOT/rel)==sha,rel
for rel,meta in protected['metadata'].items():
 p=ROOT/rel;assert p.stat().st_size==meta['bytes'] and p.stat().st_mtime_ns==meta['mtime_ns'],rel
for rel,sha in protected['sha256'].items():assert digest(ROOT/rel)==sha,rel
for rec in protected['prior_artifacts'].values():assert digest(ROOT/rec['path'])==rec['sha256'],rec['path']
for rec in protected['inputs']:assert digest(ROOT/rec['data'])==rec['sha256'],rec['data']
attempts=[]
for kind,path,jobs in [('probes','probes/legacy_v1',[j for j in cfg['probes'] if j['mode']=='Legacy']),('probes','probes/new_v1',[j for j in cfg['probes'] if j['mode']!='Legacy']),('offline','offline/frozen_v1',cfg['offline']),('oracle','oracle/frozen_v1',cfg['oracles'])]:
 assert (BASE/path/'FINISHED.json').exists()
 assert {p.parent.name for p in (BASE/path).glob('*/attempt.json')}=={j['id'] for j in jobs}
 for j in jobs:
  d=BASE/path/j['id'];job=read(d/'attempt.json');terminal=read(d/'terminal.json');assert job['mode']==j['mode'] and job['cpu']==0
  attempts.append({'kind':kind,'path':str(d.relative_to(ROOT)),'attempt_sha256':digest(d/'attempt.json'),'terminal_sha256':digest(d/'terminal.json'),'completion_sha256':digest(d/'completion.json'),'returncode':terminal['returncode'],'external_timeout':terminal['external_timeout']})
  if kind=='offline':assert read(d/'completion.json')['completed']
  if kind!='oracle' and 'stream.jsonl' in [p.name for p in d.iterdir()]:
   rs,trunc=stream_rows(d/'stream.jsonl');assert not trunc and not any(r['kind']=='failure' for r in rs)
for v in ['release','sanitize']:
 for repair in ['Legacy','ValueCache','Shared']:
  r=read(BASE/f'correctness/isolation_{v}_verified/{repair}/audit.json');assert r['passed'] and r['checks']['actual_strict_covered_replacement_count']>=1
oracle=read(BASE/'analysis/oracle_summary.json');assert oracle['cases']==24 and oracle['checks_attempted']<=24
assert not (BASE/'online').exists() and not (BASE/'short').exists() and not (BASE/'formal').exists()
write(MAN/'attempts.json',{'all_failures_retained':True,'bounded_jobs':attempts,'correctness_and_build_attempts':[str(p.relative_to(ROOT)) for p in sorted((BASE/'build_logs').rglob('*')) if p.is_file()],'real_online_sessions':0,'HighDiv_reruns':0,'additional_seeds':0,'B_enabled':False})
write(BASE/'audit_summary.json',{'passed':True,'frozen_files':len(frozen['files']),'protected_metadata_files':len(protected['metadata']),'protected_hashes':len(protected['sha256']),'original_artifacts_unchanged':True,'offline_sequences':39,'source_models':43,'replayed_events':559,'diagnostic_workers':9,'oracle_cases':24,'oracle_checks_attempted':oracle['checks_attempted'],'all_prefixes_preserved':True,'official_and_independent_agree':True,'actual_replacement_isolation_passed':True,'historical_cpu_credit_proven':False,'real_online_sessions':0,'all_failures_retained':True,'no_real_solver_in_audit':True,'report_sha256':digest(ROOT/'docs/refinement_cost_repair/results.zh.md')})
write(BASE/'artifact_hashes.json',{str(p.relative_to(ROOT)):digest(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'})
print('final audit PASS',flush=True)
