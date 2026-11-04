"""Recreate every kernel patch from frozen upstream and compare compiled sources."""
import json,pathlib,subprocess,tempfile
from prepare import ROOT,sha,write
p=ROOT/'build/prepare.json';original=p.read_bytes();manifest=json.loads(original)
compiled=pathlib.Path(manifest['destination'])/'z3'
dest=pathlib.Path(tempfile.mkdtemp(prefix='expr_v5_patch_replay_'))
try:
    manifest['destination']=str(dest);write(p,json.dumps(manifest))
    subprocess.run(['python3',str(ROOT/'scripts/prepare.py'),'--destination',str(dest),'--repatch'],check=True)
    replay=json.loads(p.read_text());files=replay['changed_z3_files']
    for name in files:assert sha(compiled/name)==sha(dest/'z3'/name),name
    write(ROOT/'results/v5_patch_replay.json',json.dumps(dict(passed=True,compared=len(files),replay=str(dest),compiled=str(compiled),sha256={name:sha(compiled/name) for name in files}),indent=2)+'\n')
    print('Replayed kernel files match:',len(files))
finally:p.write_bytes(original)
