from common5 import *
def jread(p):return read(p) if p.exists() else None
def deterministic_points(points):return [{k:v for k,v in p.items() if k!='elapsed'} for p in points]
def main():
    plan=read(ROOT/'manifests/round5_X_plan.json');results=[];initial=[];progress=[];states={};raw={}
    for job in plan['rows']:
        id=job['id'];d=BASE/'replay'/id
        if not job['execute']:results.append({**job,'result':job['skip_reason'],'SAT':None,'time_to_first_solution':None});continue
        proc=read(d/'terminal.json');term=jread(d/(id+'_terminal.json'));state=jread(d/(id+'_R3.json'));r1=jread(d/(id+'_R1.json'));r2=jread(d/(id+'_R2.json'));interval=jread(d/(id+'_intervals.json'));trace=jread(d/(id+'_progress.json'));solution=jread(d/(id+'_solution.json'));raw[id]={'term':term,'state':state,'trace':trace,'interval':interval};states[id]=state
        if state:
            assert len(state['solution'])>=len(state['vars'])
            for i,var in enumerate(state['vars']):
                if var['is_lia']:assert int(var['low'])<=int(state['solution'][i])<=int(var['upper']),('initial_value_outside_hard_bounds',id,i)
        for p in trace['points'] if trace else []:progress.append({'run':id,**p})
        phase=term['phase_seconds'] if term else {};first=next((p for p in trace['points'] if p['kind']=='first_solution_before_reconstruction'),None) if trace else None
        search=phase.get('ls_sampling_inclusive');init=phase.get('initialize_nested_in_search',0);reconstruct=phase.get('reconstruction_nested_in_search',0)
        row={**{k:v for k,v in job.items() if k not in ['recipe','map']},'result':term['exit'] if term else 'parent_cutoff_or_missing_terminal','process_exit':proc['exit_code'],'wall':proc['wall_from_batch_release'],'user_cpu':proc['user_cpu'],'system_cpu':proc['system_cpu'],'SAT':bool(solution) if term else None,'validation':'ccss_solution_only' if solution else None,'native_check_solution':solution['native_check_solution'] if solution else None,'native_unsat_count':solution['unsat_count'] if solution else None,'time_to_first_solution':first['elapsed'] if first else None,'steps_to_first_solution':first['step'] if first else None,'initial_unsat':len(state['unsat']) if state else None,'initial_best_cost':state['best_cost'] if state else None,'best_final':min((p['best'] for p in trace['points']),default=None) if trace else None,'last_recorded_step':trace['points'][-1]['step'] if trace and trace['points'] else None,'initialize_count':term['initialize_count'] if term else None,'construction_without_intervals':phase.get('build_instance_inclusive',0)-phase.get('calc_var_intervals_nested_in_build',0) if term else None,'interval_seconds':phase.get('calc_var_intervals_nested_in_build') if term else None,'initialize_seconds':init if term else None,'search_excluding_init_reconstruct':search-init-reconstruct if search is not None else None,'reconstruction_seconds':reconstruct if term else None,'nested_log_seconds_not_additive':phase.get('log_output') if term else None,'read_present':sum(r['status']=='present' for r in interval['reads']) if interval else None,'read_missing':sum(r['status']=='missing' for r in interval['reads']) if interval else None,'read_conversion_failure':sum(r['status'] not in ['present','missing'] for r in interval['reads']) if interval else None,'R1_rng_sha':sha_text(r1['rng']) if r1 else None,'R2_rng_sha':sha_text(r2['rng']) if r2 else None,'R3_rng_sha':sha_text(state['rng']) if state else None,'progress_overflow':trace['dropped'] if trace else None}
        results.append(row)
    pairs=[('X_rr','X_rc'),('X_cr','X_cc'),('X_rr','X_r0'),('X_cc','X_c0')];comparisons=[]
    for left,right in pairs:
        l=states.get(left);r=states.get(right)
        if not l or not r:comparisons.append({'left':left,'right':right,'status':'missing_initialized_state'});continue
        assert [v['name'] for v in l['vars']]==[v['name'] for v in r['vars']]
        different=0
        li=raw[left]['interval'];ri=raw[right]['interval']
        for i,(lv,rv) in enumerate(zip(l['vars'],r['vars'])):
            diff=l['solution'][i]!=r['solution'][i];different+=diff
            initial.append({'left':left,'right':right,'index':i,'name':lv['name'],'is_lia':lv['is_lia'],'left_value':l['solution'][i],'right_value':r['solution'][i],'value_changed':diff,'left_interval':str(l['intervals'][i]),'right_interval':str(r['intervals'][i]),'interval_changed':l['intervals'][i]!=r['intervals'][i],'left_model_value':li['variables'][i]['model_value'],'right_model_value':ri['variables'][i]['model_value'],'left_branch':li['variables'][i]['branch'],'right_branch':ri['variables'][i]['branch']})
        comparisons.append({'left':left,'right':right,'status':'compared','initial_values_changed':different,'unsat_symmetric_difference':len(set(l['unsat'])^set(r['unsat'])),'R3_rng_equal':l['rng']==r['rng']})
    repeats=[]
    for left,right in [('X_rr','X_rr_repeat'),('X_cc','X_cc_repeat')]:
        if not states.get(left) or not states.get(right):repeats.append({'left':left,'right':right,'status':'missing_state'});continue
        L=deterministic_points(raw[left]['trace']['points']) if raw[left]['trace'] else [];R=deterministic_points(raw[right]['trace']['points']) if raw[right]['trace'] else [];n=min(len(L),len(R));k=next((i for i in range(n) if L[i]!=R[i]),n)
        repeats.append({'left':left,'right':right,'initialized_state_equal':states[left]==states[right],'common_progress_points':n,'matching_prefix_points':k,'same_native_steps_prefix':k==n,'wall_determinism_not_claimed':True})
    csvwrite(BASE/'analysis/X_replay_results.csv',results);csvwrite(BASE/'analysis/X_initialization_diff.csv',initial)
    with (BASE/'analysis/X_search_progress.jsonl').open('w') as f:
        for r in progress:f.write(json.dumps(r)+'\n')
    write(BASE/'analysis/X_summary.json',{'passed':True,'results':results,'comparisons':comparisons,'diagonal_repeats':repeats,'formal_samples_added':0,'SMT_calls':0,'ccss_solution_only':'Saved native variables and reconstruction are retained; original model converter restoration must be validated separately before claiming a full F-model.'})
    print([{k:r.get(k) for k in ['id','result','initial_unsat','steps_to_first_solution','wall']} for r in results])
if __name__=='__main__':main()
