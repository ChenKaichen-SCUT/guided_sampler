from common_bd import *
assert read(BASE/'audit_summary.json')['passed']
assert not (BASE/'artifact_hashes.json').exists()
# Run only after every evidence writer has exited; its own stdout must be outside BASE.
inventory={str(p.relative_to(ROOT)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(BASE.rglob('*')) if p.is_file()}
exclusive(BASE/'artifact_hashes.json',{'files':inventory,'excluding_self':True,'sealed_after_all_writers':True})
print('sealed',len(inventory),'files',flush=True)
