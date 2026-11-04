import argparse,concurrent.futures,json,subprocess,time
from prepare import ROOT,write
ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();folder=ROOT/'results'/args.name
benches=sorted(set(json.loads(p.read_text())['bench'] for p in folder.glob('*/run.json')));start=time.monotonic()
def audit(item):
    i,bench=item;output=f'audit_part_{i}.json'
    with (folder/f'audit_part_{i}.log').open('w') as log:
        p=subprocess.run(['python3',str(ROOT/'scripts/audit.py'),args.name,'--bench',bench,'--output',output],stdout=log,stderr=subprocess.STDOUT)
    print(json.dumps(dict(bench=bench,exit_code=p.returncode)),flush=True)
    if p.returncode:raise RuntimeError(str(folder/f'audit_part_{i}.log'))
    return json.loads((folder/output).read_text())
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:parts=list(pool.map(audit,enumerate(benches)))
combined=dict(runs=sum([p['runs'] for p in parts],[]),all_passed=all(p['all_passed'] for p in parts),wall=time.monotonic()-start,oracle_library_sha256=parts[0]['oracle_library_sha256'])
write(folder/'audit.json',json.dumps(combined,indent=2)+'\n');print(json.dumps(dict(all_passed=combined['all_passed'],runs=len(combined['runs']),wall=combined['wall'])))
