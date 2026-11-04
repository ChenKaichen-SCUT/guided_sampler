"""Pinned parallel experiments. No audit or compilation overlaps sampling."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,random,subprocess,time
from prepare import ROOT,WORKSPACE,write
from profiles import PROFILES
BENCH=WORKSPACE/'HighDiv-master/HighDiv/LIA_bench'
ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--seconds',type=float,default=30)
ap.add_argument('--modes',default='baseline,soft,soft_budget,soft_complete,soft_hold,soft_off,base_budget,base_complete');ap.add_argument('--seeds',default='0')
ap.add_argument('--bench',default='');ap.add_argument('--workers',type=int,default=4);ap.add_argument('--samples',type=int,default=4294967295)
ap.add_argument('--suite',choices=['registered','bundled'],default='registered')
args=ap.parse_args();out=ROOT/'results'/args.name;out.mkdir(parents=True,exist_ok=False)
if args.suite=='registered':
    BENCH=ROOT/'benchmarks';BENCH.mkdir(exist_ok=True)
    import shutil
    for entry in json.loads((WORKSPACE/'guided_sampler/manifests/inputs.json').read_text()):
        p=WORKSPACE/entry['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'];shutil.copyfile(p,BENCH/p.name)
benches=[p for p in sorted(BENCH.glob('*.smt2')) if not args.bench or any(k in p.name for k in args.bench.split(','))]
tasks=[(b,m,int(seed)) for b in benches for m in args.modes.split(',') for seed in args.seeds.split(',')];random.Random(92137).shuffle(tasks)
cpus=sorted(os.sched_getaffinity(0));workers=min(args.workers,len(cpus));chosen=cpus[::max(1,len(cpus)//workers)][:workers]
manifest=dict(arguments=vars(args),cpus=chosen,benchmarks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in benches},binaries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'bin').glob('highdiv*')},library_sha256={mode:hashlib.sha256((ROOT/'deps'/mode/'lib/libz3.so').read_bytes()).hexdigest() for mode in ['baseline','soft']},task_order=[(b.name,m,s) for b,m,s in tasks])
write(out/'manifest.json',json.dumps(manifest,indent=2)+'\n')
import shutil
for section in ['include','kernel','src','tests','scripts']:
    for p in (ROOT/section).rglob('*'):
        if p.is_file() and '__pycache__' not in str(p):
            target=out/'source'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
def lane(lane_id):
    reports=[]
    for b,mode,seed in tasks[lane_id::workers]:
        dest=out/f'{b.stem}__{mode}__s{seed}';dest.mkdir();env=os.environ.copy()
        for key in list(env):
            if key.startswith('ESG_'):del env[key]
        config=PROFILES.get(mode,{'ESG_MODE':'native' if mode=='baseline' else mode});env.update(config)
        binary='highdiv_baseline' if mode=='baseline' else 'highdiv_soft'
        command=['taskset','-c',str(chosen[lane_id]),str(ROOT/'bin'/binary),'-i',str(b),'-o',str(dest),'-n',str(args.samples),'-t',str(args.seconds),'-s',str(seed)]
        started=time.monotonic();timed_out=False
        with (dest/'stdout.log').open('w') as log:
            try:p=subprocess.run(command,env=env,cwd=dest,stdout=log,stderr=subprocess.STDOUT,timeout=args.seconds+15);code=p.returncode
            except subprocess.TimeoutExpired:code=-999;timed_out=True
        report=dict(bench=b.name,input=str(b),mode=mode,effective_env=config,seed=seed,command=command,exit_code=code,outer_wall=time.monotonic()-started,hard_timeout=timed_out,limit=args.seconds)
        if (dest/'summary.json').exists():report['summary']=json.loads((dest/'summary.json').read_text())
        write(dest/'run.json',json.dumps(report,indent=2)+'\n');reports.append(report)
        print(json.dumps({k:v for k,v in report.items() if k in ['bench','mode','seed','exit_code','outer_wall','summary']}),flush=True)
    return reports
with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
    reports=sum(list(executor.map(lane,range(workers))),[])
write(out/'runs.json',json.dumps(reports,indent=2)+'\n')
if any(r['exit_code'] for r in reports):raise SystemExit(1)
