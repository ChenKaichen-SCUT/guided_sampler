from common6 import *
from batch_runner import run_batch
def main():
    freeze=read(ROOT/'manifests/round6_implementation.json');assert freeze['validation']['release']['passed'] and freeze['validation']['sanitize']['passed'];exe=ROOT/'build/round6-ccss-replay-release';assert digest(exe)==freeze['validation']['release']['replay_sha256'];cfg=read(ROOT/'configs/round6_guard.json');jobs=[]
    for j in cfg['G1']:
        d=BASE/'replay_guard'/j['id'];recipe=OLD5/'capture'/j['H']/'recipe.json';mp=OLD5/'capture'/(j['H'] if j['M']=='empty' else j['M'])/('empty_map.json' if j['M']=='empty' else 'map.json');r=read(recipe);assert r['cutoff_seconds']==52
        ee={k:os.environ[k] for k in ['PATH','LANG','LC_ALL','TMPDIR'] if k in os.environ};ee['GUIDED_CCSS_STAGNATION_GUARD']='1';jobs.append({**j,'directory':str(d),'command':[str(exe),str(recipe),str(mp),str(d),j['id'],'0'],'environment':ee,'recipe':str(recipe.relative_to(ROOT)),'recipe_sha256':digest(recipe),'map':str(mp.relative_to(ROOT)),'map_sha256':digest(mp),'binary_sha256':digest(exe)})
    exclusive(BASE/'G1_STARTED.json',{'implementation_sha256':digest(ROOT/'manifests/round6_implementation.json'),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'count':6});r=run_batch(jobs,BASE/'replay_guard_batch',65);exclusive(BASE/'G1_FINISHED.json',{'count':6,'no_retries':True,'results':r});print('G1 completed6 once only')
if __name__=='__main__':main()
