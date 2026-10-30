#!/usr/bin/env python3
"""Seal the sole 16-run A-only matrix and read-only historical references."""
from common import *
def historical_fingerprint():
 old=read(ROOT/'manifests/plan.json');frozen=read(ROOT/'results/baseline_seed0_v1/BASELINE_FROZEN.json');out={}
 for r in old['runs']:
  if r['config']!='highdiv':continue
  d=ROOT/r['output'];pin=frozen['runs'][r['id']];assert digest(d/'artifact_hashes.json')==pin['artifact_manifest_sha256']
  for name,h in pin['artifacts'].items():assert digest(d/name)==h,(r['id'],name)
  out[r['id']]={'attempt_sha256':digest(d/'attempt.json'),'attempt_mtime_ns':(d/'attempt.json').stat().st_mtime_ns,'artifact_manifest_sha256':digest(d/'artifact_hashes.json')}
 return out
def main():
 assert not (ROOT/'results/round2_a/QUEUE_STARTED.json').exists()
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),'Commit S4 before freezing'
 artifacts={};checks={}
 for v in ('release','sanitize'):
  d=ROOT/f'results/round2_a/correctness/{v}_final';check=read(d/'summary.json');assert check['passed'];checks[v]={'path':str((d/'summary.json').relative_to(ROOT)),'sha256':digest(d/'summary.json')}
  paths={'binary':ROOT/f'worktrees/round2_{v}/HighDiv/highdiv','library':ROOT/f'deps/round2_{v}/lib/libz3.so'};artifacts[v]={k:{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for k,p in paths.items()}
  assert check['binary_sha256']==artifacts[v]['binary']['sha256'] and check['library_sha256']==artifacts[v]['library']['sha256']
  artifacts[v]['ldd']=subprocess.check_output(['ldd',paths['binary']],text=True)
 old=read(ROOT/'manifests/plan.json');artifacts['metric']=old['artifacts']['metric'];assert digest(metric_path())==artifacts['metric']['sha256']
 micro=read(ROOT/'results/round2_a/micro/FINISHED.json');assert micro['calls']==36
 runs=[]
 for r in old['runs']:
  if r['config']!='highdiv':continue
  x=dict(r);i=int(r['id'].split('_')[-1]);x.update(order=len(runs),id=f'a_only_v2_{r["mode"]}_{i:02}',config='a_only_v2',variant='round2_release',output=f'results/round2_a/formal/{r["mode"]}/{i:02}')
  x['command']=[artifacts['release']['binary']['path'],'-i',x['input'],'-o',x['output'],'-t','900','-s','0','--guidance','a_only_v2']+(['--unlimited-samples'] if x['limit'] is None else ['-n','100']);runs.append(x)
 assert len(runs)==16 and len({r['preferred_cpu'] for r in runs})==16
 source={str(p.relative_to(ROOT)):digest(p) for pattern in ('include/round2/*','src/round2/*','scripts/*round2*.py','tests/round2/*','configs/round2_a.json') for p in ROOT.glob(pattern) if p.is_file()}
 plan={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'base_commit':'fc19bd22609295ed405e1ac96bf35d695c42832a','artifacts':artifacts,'correctness':checks,'source_hashes':source,'config':read(ROOT/'configs/round2_a.json'),'workers':old['workers'],'runs':runs,'dispatch':'one synchronous barrier, sixteen independent sessions, no refill/retry','baseline_before':historical_fingerprint(),'baseline_executions':0,'micro_finished_sha256':digest(ROOT/'results/round2_a/micro/FINISHED.json')}
 exclusive(ROOT/'manifests/round2_a_plan.json',plan);print('Frozen exactly 16 new A-only runs; historical baseline verified unchanged')
if __name__=='__main__':main()
