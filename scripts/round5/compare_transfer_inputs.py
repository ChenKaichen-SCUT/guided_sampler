"""Freeze actual captured inputs, validate native reconstruction before any X search."""
from common5 import *
def main():
    assert (BASE/'W_FINISHED.json').exists();dest=BASE/'capture';dest.mkdir(exist_ok=False);freeze=read(ROOT/'manifests/round5_implementation.json');replay=ROOT/'build/round5-ccss-replay-release';assert digest(replay)==freeze['validation']['release']['replay_sha256']
    results={};files={};diff=[]
    for mode,label in [('S_ref','ref'),('S_full','full')]:
        d=BASE/'W'/('convert_'+mode);recipe_path=d/'ccss_2_recipe.json';needed=['recipe','R1','R2','R3','intervals']
        missing=[x for x in needed if not (d/f'ccss_2_{x}.json').exists()]
        if missing:results[label]={'passed':False,'status':'capture_missing','missing':missing};continue
        r=read(recipe_path);ccss=[q for q in rows(d/'queries.jsonl') if q['source']=='CCSS'];assert len(ccss)>=2 and r['query']==ccss[1]['query'];assert r['seed']==ccss[1]['highdiv_ls_seed'] and r['cutoff_seconds']==ccss[1]['granted_timeout'];rd=dest/label;rd.mkdir();mp=rd/'map.json';write(mp,r['exchange']['map']);write(rd/'recipe.json',r);write(rd/'empty_map.json',{})
        original={x['name']:x for x in rows(d/'formal_receipts.jsonl')[0]['typed']};formal=next((x for x in rows(d/'formal_receipts.jsonl') if x['query']==3),None)
        host_values={x['name']:x['value'] for x in formal['typed']} if formal else {}
        read_names={x['name'] for x in read(d/'ccss_2_intervals.json')['reads']};prod=r['exchange']['producers'];map_=r['exchange']['map']
        for key,value in map_.items():
            source=prod.get(key);diff.append({'recipe':label,'name':key,'raw':value,'consumed':key in read_names,'producer_known':source is not None,'producer_query':source['query'] if source else None,'producer_batch':source['batch'] if source else None,'latest_batch':r['exchange']['latest_batch'],'previous_generation':source['batch']!=r['exchange']['latest_batch'] if source else None,'original_variable':key in original,'formal_q3_value':host_values.get(key),'raw_equals_formal_string':value==host_values.get(key) if key in host_values else None})
            if source:assert source['raw']==value and source['name']==key
        cmd=[str(replay),str(rd/'recipe.json'),str(mp),str(rd),'X1','1'];exclusive(rd/'attempt.json',{'command':cmd,'search_loop':False,'solver_calls':0})
        with (rd/'stdout.log').open('x') as stdout,(rd/'stderr.log').open('x') as stderr:
            try:run=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=65);rc=run.returncode
            except subprocess.TimeoutExpired:rc='parent_cutoff'
        mismatches=[]
        for b in ['R1','R2','R3','intervals']:
            p=rd/f'X1_{b}.json'
            if not p.exists() or read(p)!=read(d/f'ccss_2_{b}.json'):mismatches.append(b)
        passed=rc==0 and not mismatches
        results[label]={'passed':passed,'status':'validated' if passed else 'reconstruction_not_validated','exit_code':rc,'mismatched_boundaries':mismatches,'capture_directory':str(d.relative_to(ROOT)),'recipe_sha256':digest(rd/'recipe.json'),'map_sha256':digest(mp),'map_entries':len(map_),'read_keys':sorted(read_names),'unknown_producer_keys':[k for k,v in prod.items() if v is None],'original_names':sorted(original),'R0':sha_text(r['R0'])}
        for p in d.glob('ccss_[12]_*.json'):files[str(p.relative_to(ROOT))]=digest(p)
        for p in rd.iterdir():
            if p.is_file():files[str(p.relative_to(ROOT))]=digest(p)
    csvwrite(BASE/'analysis/X_producer_consumer_diff.csv',diff)
    compatibility={}
    for h,m in [('ref','full'),('full','ref')]:
        if not results.get(h,{}).get('passed') or not results.get(m,{}).get('passed'):compatibility[h+'_'+m]={'passed':False,'reason':'reconstruction_not_validated'};continue
        hr=read(dest/h/'recipe.json');mr=read(dest/m/'recipe.json');consumed=set(results[h]['read_keys']);original=set(results[h]['original_names']);unverified=[k for k in mr['exchange']['map'] if k in consumed and k not in original]
        # Do not discard or rename auxiliary keys to force compatibility.
        compatibility[h+'_'+m]={'passed':not unverified,'unverified_consumed_auxiliary':unverified,'unconsumed_extra_keys_preserved':sorted(set(mr['exchange']['map'])-consumed),'reason':'original declarations of identical frozen F' if not unverified else 'incompatible_recipe_map'}
    write(BASE/'analysis/X_capture_fidelity.json',{'sources':results,'compatibility':compatibility,'nonmap_fields':['seed','cutoff_seconds','R0','build_lits','make_lits_space','clause_vec','use_interval_move'],'no_historical_map_claim':True,'new_SMT_checks':0,'files':files})
    exclusive(ROOT/'manifests/round5_capture.json',{'files':files,'audit_sha256':digest(BASE/'analysis/X_capture_fidelity.json'),'parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    print({k:(v['status'],v.get('mismatched_boundaries')) for k,v in results.items()})
if __name__=='__main__':main()
