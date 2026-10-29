"""Exercise the exactly-once queue against fake workers, never real benchmarks."""
import hashlib,json,os,pathlib,shutil,sys,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import run_experiments as runner
from common import digest,write,ROOT
with tempfile.TemporaryDirectory(prefix='guided-queue-test-') as temp:
    p=pathlib.Path(temp);(p/'results').mkdir();(p/'scripts').mkdir();(p/'manifests').mkdir()
    shutil.copy(ROOT/'scripts/launch_worker.py',p/'scripts/launch_worker.py')
    binary=p/'fake.py';binary.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(0.03)\n');binary.chmod(0o755)
    (p/'input.smt2').write_text('(assert true)')
    cpus=sorted(os.sched_getaffinity(0))[:16];assert len(cpus)==16
    artifact={'binary':{'path':'fake.py','sha256':digest(binary)},'library':{'path':'fake.py','sha256':digest(binary)}}
    runs=[{'id':f'fake_{i:02d}','order':i,'config':'highdiv' if i<16 else 'guided','input':'input.smt2','input_sha256':digest(p/'input.smt2'),'output':f'results/run{i:02d}','preferred_cpu':cpus[i%16],'command':['fake.py']} for i in range(64)]
    write(p/'manifests/plan.json',{'runs':runs,'workers':cpus,'artifacts':{'baseline':artifact,'guided':artifact}})
    runner.ROOT=p;runner.main();events=[json.loads(l) for l in (p/'results/dispatch.jsonl').read_text().splitlines()]
    launches=[e for e in events if e['event']=='launch'];assert [e['id'] for e in launches]==[r['id'] for r in runs];assert all(e['barrier']==(i<16) for i,e in enumerate(launches))
    active={}
    for e in events:
        if e['event']=='launch':assert e['cpu'] not in active;active[e['cpu']]=e['id']
        else:assert active.pop(e['cpu'])==e['id'];assert e['cpu_seconds_exact']>=0 and e['peak_rss_kib_exact']>0
    assert not active
    try:runner.main();raise AssertionError('Exactly-once ledger was overwritten')
    except FileExistsError:pass
    evidence={'passed':True,'fake_runs':64,'real_benchmarks_executed':0,'events':events}
    out=ROOT/'results/correctness/scheduler.json';write(out,evidence);print('Fixed queue / 16 slots / barrier / exactly-once ledger passed')
