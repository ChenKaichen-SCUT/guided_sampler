from common6 import *
v=sys.argv[1];new=BASE/'correctness'/f'{v}_{"02" if v=="release" else "01"}';old=OLD5/'correctness'/f'{v}_{"03" if v=="release" else "01"}';checks=[]
for mode in ['a_off_test','S_ref','S_full','S_support']:
    for trace in ['off','on']:
        n=new/(mode+'_'+trace);o=old/(mode+'_'+trace)
        for f in ['samples.formal','native_decisions.txt','rng.txt']+[f'ccss_{i}_{stage}.json' for i in [1,2] for stage in ['R1','R2','R3','intervals']]:
            np=n/f;op=o/f;assert np.exists()==op.exists(),(mode,trace,f)
            if np.exists():assert np.read_bytes()==op.read_bytes(),('disabled_vs_frozen_R5',mode,trace,f)
            checks.append({'mode':mode,'trace':trace,'file':f,'status':'identical' if np.exists() else 'not_generated_in_either','new_sha256':digest(np) if np.exists() else None,'frozen_sha256':digest(op) if op.exists() else None})
write(BASE/'correctness'/f'disabled_{v}_verified.json',{'passed':True,'checks':checks,'old_binary_executions':0,'new_solver_calls':0});print('Disabled mode matches frozen R5 native/RNG/initialization/model',v)
