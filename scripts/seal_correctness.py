#!/usr/bin/env python3
import shutil
from common import *
def main():
    root=ROOT/'results/correctness';required=['release/summary.json','sanitize/summary.json','release/upstream.json','sanitize/upstream.json','scheduler.json','cli/summary.json','input_preflight/summary.json']
    for p in required:assert read(root/p)['passed'],p
    for variant,label in [('guided','release'),('sanitize','sanitize')]:assert read(root/label/'summary.json')['library_sha256']==digest(ROOT/f'deps/{variant}/lib/libz3.so')
    for e in read(ROOT/'manifests/upstream.json')['files']:assert digest(UP/e['path'])==e['sha256'],e['path']
    for e in read(ROOT/'manifests/inputs.json'):assert digest(ROOT.parent/e['path'])==e['sha256']
    logs=root/'build_logs';logs.mkdir(exist_ok=True)
    for p in (ROOT/'build').glob('*.log'):shutil.copyfile(p,logs/p.name)
    summary={'passed':True,'checks':{p:digest(root/p) for p in required},'original_source_and_inputs_unchanged':True,
        'upstream_leak_exception':{'description':'Native no-guidance reproducer leaks 32 bytes in upstream undo_fixed_column copy constructor; only this frame is suppressed. ASan/UBSan and detect_leaks stay enabled.','suppression_sha256':digest(ROOT/'tests/lsan-upstream.supp'),'evidence':'results/correctness/upstream-leak/'},
        'formal_runs_started':0,'no_performance_promotion_gate':True}
    exclusive(root/'summary.json',summary);print('Correctness sealed; original sources/inputs verified; no formal baseline attempts consumed.')
if __name__=='__main__':main()
