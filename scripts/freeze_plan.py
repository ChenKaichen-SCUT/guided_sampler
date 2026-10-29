#!/usr/bin/env python3
import shlex,subprocess
from common import *

def main():
    checks=read(ROOT/'results/correctness/summary.json');assert checks['passed']
    assert not (ROOT/'manifests/plan.json').exists(),'Refusing to replace a frozen plan'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),'Commit implementation and correctness evidence first'
    artifacts=artifact_manifest();write(ROOT/'manifests/builds.json',artifacts)
    code=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    inputs=read(ROOT/'manifests/inputs.json');assert len(inputs)==8
    allowed=sorted(os.sched_getaffinity(0));assert len(allowed)>=16
    topology=[]
    for line in subprocess.check_output(['lscpu','-p=CPU,CORE,SOCKET'],text=True).splitlines():
        if not line.startswith('#'):
            cpu,core,socket=map(int,line.split(','));
            if cpu in allowed:topology.append((socket,core,cpu))
    groups={}
    for socket,core,cpu in topology:groups.setdefault((socket,core),[]).append(cpu)
    cores=[sorted(g)[:2] for _,g in sorted(groups.items()) if len(g)>=2][:8]
    assert len(cores)==8,'Protocol requires eight SMT cores / sixteen logical workers'
    workers=sorted(cpu for group in cores for cpu in group)
    runs=[]
    for config in ['highdiv','a_only','b_only','a_plus_b']:
        for mode,limit in [('time900',None),('n100_t900',100)]:
            for i,entry in enumerate(inputs):
                variant='baseline' if config=='highdiv' else 'guided';idx=len(runs)
                out=pathlib.Path('results')/('baseline_seed0_v1' if config=='highdiv' else 'round1')/config/mode/f'{i:02d}'
                binary=artifacts[variant]['binary']['path'];inp='../'+entry['path']
                cmd=[binary,'-i',inp,'-o',str(out),'-t','900','-s','0','--guidance','off' if config=='highdiv' else config]
                cmd+=['--unlimited-samples'] if limit is None else ['-n','100']
                runs.append({'order':idx,'id':f'{config}_{mode}_{i:02d}','config':config,'mode':mode,'seed':0,'input':inp,'input_sha256':entry['sha256'],'input_name':pathlib.Path(entry['path']).name,'variant':variant,'wall':900,'limit':limit,'preferred_cpu':cores[i][0 if limit is None else 1],'allowed_cpus':workers,'command':cmd,'output':str(out)})
    plan={'source_commit':code,'artifacts':artifacts,'config':read(ROOT/'configs/round1.json'),'workers':workers,'runs':runs,
        'dispatch':'first sixteen synchronous barrier; thereafter frozen queue, vacant workers sorted by actual CPU; no batch barrier',
        'correctness_sha256':digest(ROOT/'results/correctness/summary.json')}
    exclusive(ROOT/'manifests/plan.json',plan)
    print('Frozen 64 independent sessions; baseline starts are irreversible attempt records.')
if __name__=='__main__':main()
