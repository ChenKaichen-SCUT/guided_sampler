"""Seal only after all evidence-writing processes have exited; log outside BASE."""
from common_cr import *
import shutil
assert read(BASE/'audit_summary.json')['passed']
old=ROOT/'archives/refinement_cost_repair';saved=ROOT/'build/refinement-cost-repair-archive-preseal';assert not saved.exists();old.rename(saved)
shutil.copy2(BASE/'artifact_hashes.json',BASE/'build_logs/inventory_before_seal.json')
write(BASE/'build_logs/inventory_seal_note.json',{'reason':'The audit wrote its own final stdout after enumerating artifact hashes; a zero-byte upstream trace was subsequently preserved. Seal after all writers exit, without changing any experiment, result or report.','old_archive_manifest_sha256':digest(saved/'manifest.json'),'old_archive_verification':read(saved/'verification.json'),'changed_before_seal':['build_logs/final_audit.log'],'new_before_seal':['build_logs/post_audit_root.z3-trace'],'old_inventory_preserved':'build_logs/inventory_before_seal.json','all_raw_experiments_unchanged':True})
files={str(p.relative_to(ROOT)):digest(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'}
write(BASE/'artifact_hashes.json',files)
for rel,sha in files.items():assert digest(ROOT/rel)==sha,rel
print('sealed',len(files),'evidence files; excludes inventory itself',flush=True)
