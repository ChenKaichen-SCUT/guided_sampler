from common_r import *
from independent import evaluate,observations,covered,metric_module
import collections
out=BASE/'offline/frozen_v1';summary=[];funnel=collections.Counter();loss_examples=[];allpassed=True;partitions=[]
for d in sorted(out.iterdir()):
    if not d.is_dir():continue
    req=read(d/'request.json');data=read(d/'result.json')['result'];ast=req['ast'];history=set();native_history=set();output_keys=set();replacement=0;covered_replacement=0;unprotected_better=0;protected_rejections=0
    positions=[]
    for row,m in zip(data['events'],req['models']):
        legal,native=observations(ast,m);assert legal;protected=native-history;native_base=(covered(history|native)-covered(history),len(native-history));best=None
        for candidate in row['candidates']:
            if candidate['kind']!='candidate':continue
            funnel[candidate.get('reason','incomplete')]+=1
            if candidate.get('reason','').startswith('incomplete') or candidate['reason']=='candidate_duplicate':continue
            q=candidate['assignment'];ql,obs=observations(ast,q);assert ql;missing=protected-obs
            assert sorted(map(tuple,candidate['missing_observations']))==sorted(missing)
            assert candidate['gain_covered']==covered(history|obs)-covered(history);assert candidate['gain_observed']==len(obs-history)
            assert {i:int(v) for i,z,o,v in candidate['actual_observations']}=={i:v for i,(bits,v) in evaluate(ast,q)[1].items()}
            if candidate['reason']=='eligible_strict_improvement':assert not missing and (candidate['gain_covered'],candidate['gain_observed'])>native_base
            if missing and (candidate['gain_covered'],candidate['gain_observed'])>native_base:
                protected_rejections+=1
                if len(loss_examples)<50:loss_examples.append({'sequence':d.name,'position':row['native_event_id'],'direction':candidate['direction_id'],'t':candidate['t'],'missing':candidate['missing_observations']})
        if row['unprotected_chosen'] and not row['chosen']:unprotected_better+=1
        chosen=row['chosen'];q=m if chosen is None else chosen['assignment'];ql,qo=observations(ast,q);assert ql
        if chosen:
            assert protected<=qo;assert (covered(history|qo)-covered(history),len(qo-history))>native_base;replacement+=1
            if covered(history|qo)>covered(history|native):covered_replacement+=1
        native_history|=native
        actual=m if req['layer']=='L1' else q;actualobs=native if req['layer']=='L1' else qo;key=tuple(actual)
        if key not in output_keys:history|=actualobs;output_keys.add(key)
        assert native_history<=history;assert row['prefix_contains_native'];assert covered(history)==row['output_covered'];assert covered(native_history)==row['native_covered'];assert len(output_keys)==row['output_count']
        positions.append({'position':row['native_event_id'],'replacement':bool(chosen),'native_covered':covered(native_history),'output_covered':covered(history),'extra':covered(history)-covered(native_history),'reason':row['reason'],'cancellation':row['cancellation'],'event_cpu':row.get('event_cpu',0),'event_wall':row.get('event_wall',0),'event_cpu_overrun':max(0,row.get('event_cpu',0)-row.get('cpu_cap',0)),'event_wall_overrun':max(0,row.get('event_wall',0)-row.get('wall_cap',0))})
    files=[]
    for kind,models in [('native',req['models']),('output',[r['output_assignment'] for r in data['events']])]:
        path=d/(kind+'.samples');seen=set()
        with open(path,'w') as f:
            for m in models:
                if tuple(m) in seen:continue
                seen.add(tuple(m));f.write(str(len(seen)-1)+': '+''.join(v['name']+':'+val+';' for v,val in zip(ast['variables'],m))+'\n')
        name=d.name.rsplit('_L',1)[0];source=read(BASE/'offline/inputs_v1'/f'{name}.json');cmd=[python(),metric_path(),'-s',path,'-f',source['input'],'-m','wire_coverage'];r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120);(d/(kind+'.official.stdout')).write_text(r.stdout);(d/(kind+'.official.stderr')).write_text(r.stderr);write(d/(kind+'.official.command.json'),{'command':list(map(str,cmd)),'returncode':r.returncode,'metric_sha256':digest(metric_path()),'samples_sha256':digest(path),'input_sha256':ast['input_sha']});assert r.returncode==0;expected=covered(native_history) if kind=='native' else covered(history);total=sum(1 if n['sort']=='Bool' else 64 for n in ast['nodes']);assert r.stdout.strip()==str(round(expected/total*100,2))+'%';files.append(kind)
    write(d/'audit.json',{'passed':True,'positions':positions,'candidate_checks':'independent Python arbitrary precision + independent observed-set preservation','official_metric':files})
    first=observations(ast,req['models'][0])[1];first_bits={(i,b) for i,b,v in first};known=set();name=d.name.rsplit('_L',1)[0]
    for entry in rows(ROOT/'results/round5/W'/f'{name}_S_ref'/'a_atom_catalog.jsonl'):
        for rule in entry['rules']:
            mask=int(rule['known_zero'])|int(rule['known_one']);known.update((rule['node'],bit) for bit in range(64) if mask>>bit&1)
    universe={(i,b) for i,n in enumerate(ast['nodes']) for b in range(1 if n['sort']=='Bool' else 64)};groups={'G1':known&first_bits,'G2':first_bits-known,'G3':universe-first_bits};native_covered={(i,b) for i,b,v in native_history if (i,b,1-v) in native_history};output_covered={(i,b) for i,b,v in history if (i,b,1-v) in history};assert sum(len(g) for g in groups.values())==len(universe)
    for g,mask in groups.items():partitions.append({'sequence':d.name,'group':g,'size':len(mask),'gain':len((output_covered-native_covered)&mask),'loss':len((native_covered-output_covered)&mask),'net':len(output_covered&mask)-len(native_covered&mask)})
    assert sum(r['net'] for r in partitions if r['sequence']==d.name)==covered(history)-covered(native_history)
    summary.append({'sequence':d.name,'models':len(req['models']),'output_count':len(output_keys),'preprocessing_reason':data['preprocessing_reason'],'preprocess_wall':data['preprocess_wall'],'preprocess_cpu':data['preprocess_cpu'],'optional_wall':data['optional_wall'],'optional_cpu':data['optional_cpu'],'replacements':replacement,'strict_covered_replacements':covered_replacement,'native_covered':covered(native_history),'output_covered':covered(history),'extra':covered(history)-covered(native_history),'protected_rejected_higher_score_candidates':protected_rejections,'only_unprotected_chosen_positions':unprotected_better,'valid_online_cpu_credit':False})
csvwrite(out/'partitions.csv',partitions);csvwrite(out/'summary.csv',summary);write(out/'summary.json',summary);write(out/'candidate_funnel.json',dict(funnel));write(out/'protected_loss_examples.json',loss_examples)
main=[s for s in summary if s['sequence'].endswith('_L2_main')];positive=sum(s['extra']>0 for s in main);write(out/'gate.json',{'correctness_audit_passed':True,'positive_L2_instances':positive,'all_endpoints_preserved':True,'valid_frozen_past_CPU_credit':False,'offline_gate_passed':False,'decision':'No-Go','short_sessions_authorized_by_gate':False,'reason':'Historical per-model native CPU credit is unavailable; fixed-cap opportunity results cannot prove the mandatory online CPU AND wall budget gate. '+('Fewer than two L2 endpoints improved.' if positive<2 else ''),'short_sessions_run':0,'formal_sessions_run':0})
print('offline independent audit complete; gate No-Go',positive,flush=True)
