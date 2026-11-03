from common_r import *
import resource
freeze=read(MAN/'implementation.json');exe=ROOT/'build/refinement_cli';assert digest(exe)==freeze['artifacts']['cli_release']['sha256'];cfg=read(ROOT/'configs/refinement.json');
for name,sha in freeze['files'].items():assert digest(ROOT/name)==sha,name
out=attempt('offline','frozen_v1');exclusive(out/'STARTED.json',{'freeze_sha256':digest(MAN/'implementation.json'),'input_summary_sha256':digest(BASE/'offline/inputs_v1/summary.json'),'no_retry':True,'fixed_caps_only':True,'historical_cpu_credit_missing':True})
for name in cfg['offline_inputs']:
    data=read(BASE/'offline/inputs_v1'/f'{name}.json')
    for layer,component in [('L1',False),('L2',False),('L2',True)]:
        key=name+'_'+layer+('_component_only' if component else '_main');d=out/key;d.mkdir();request={'op':'sequence','ast':data['ast'],'models':data['models'],'layer':layer,'component_only':component,'bounded':True}
        write(d/'request.json',request);started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        with open(d/'stderr.log','w') as e,open(d/'result.json','w') as f:r=subprocess.run([exe],input=json.dumps(request)+'\n',text=True,stdout=f,stderr=e,timeout=120)
        after=resource.getrusage(resource.RUSAGE_CHILDREN);write(d/'execution.json',{'returncode':r.returncode,'wall':time.monotonic()-started,'cpu':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'binary_sha256':digest(exe),'request_sha256':digest(d/'request.json'),'no_retry':True,'performance_score':False,'past_native_cpu_credit_proven':False});assert r.returncode==0
        result=read(d/'result.json');assert result['ok'],result;print(key,result['result']['preprocessing_reason'],flush=True)
write(out/'FINISHED.json',{'sequences':9,'source_models':43,'L1_positions':40,'no_online_sessions':True})
