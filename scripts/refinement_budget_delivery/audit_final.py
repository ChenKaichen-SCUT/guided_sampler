from common_bd import *
from runner import stream_rows
cfg=read(ROOT/'configs/refinement_budget_delivery.json');frozen=read(MAN/'implementation.json');audit=read(BASE/'analysis/audit_v1/summary.json');assert audit['passed'] and audit['source_models']==43 and audit['sequences']==22 and audit['probes']==4 and audit['replayed_events']==518
for group in ['files','artifacts','libraries']:
 for rel,sha in frozen[group].items():assert digest(ROOT/rel)==sha,(group,rel)
protected=read(MAN/'protected.json')
for rel,rec in protected['metadata'].items():
 p=ROOT/rel;assert p.is_file() and p.stat().st_size==rec['bytes'] and p.stat().st_mtime_ns==rec['mtime_ns'],rel
for rel,sha in protected['hashes'].items():assert digest(ROOT/rel)==sha,rel
for variant in ['release','sanitize']:
 for kind in ['mechanisms','isolation','disabled','math','worker']:assert read(BASE/f'correctness/{kind}_{variant}_sealed/summary.json')['passed']
attempts={}
for stage,count in [('probes',4),('offline',22),('real_diagnosis',4)]:
 entries=sorted((BASE/stage).glob('*/**/attempt.json'));assert len(entries)==count,(stage,len(entries));attempts[stage]=[str(p.relative_to(ROOT)) for p in entries]
 for p in entries:
  j=read(p);assert j['native_sampling']==0 and j['real_solver_checks']==0;assert j['cpu_affinity']==[0];assert j['source_commit']==frozen['commit']
  assert j['binary_sha256']==digest(pathlib.Path(j['command'][0]));assert read(p.parent/'terminal.json')['no_retry']
assert not (BASE/'oracle').exists()
for doc in ['results.zh.md','real_blocking.zh.md']:assert (ROOT/'docs/refinement_budget_delivery'/doc).is_file()
write(MAN/'attempts.json',{'frozen_implementation_sha256':digest(MAN/'implementation.json'),'runs':attempts,'actual_new_native_sampling':0,'real_solver_checks':0,'registered_retries':0,'synthetic_attempts':[str(p.relative_to(ROOT)) for p in sorted((BASE/'correctness').glob('*')) if p.is_dir()],'build_attempts':[str(p.relative_to(ROOT)) for p in sorted((BASE/'build_logs').glob('*')) if p.is_dir()]})
write(BASE/'audit_summary.json',{'passed':True,'base':cfg['base'],'source_commit':frozen['commit'],'audit':audit,'frozen_files_verified':len(frozen['files']),'frozen_artifacts_verified':len(frozen['artifacts']),'old_files_metadata_verified':len(protected['metadata']),'old_hashes_verified':len(protected['hashes']),'attempt_counts':{s:len(v) for s,v in attempts.items()},'report_sha256':digest(ROOT/'docs/refinement_budget_delivery/results.zh.md'),'real_report_sha256':digest(ROOT/'docs/refinement_budget_delivery/real_blocking.zh.md'),'historical_cpu_credit_proven':False,'real_solver_checks':0,'new_native_sampling':0})
print('final audit PASS',flush=True)
