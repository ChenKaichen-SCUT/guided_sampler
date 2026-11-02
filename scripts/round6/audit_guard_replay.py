from common6 import *
from audit_X_details import clauses
from audit_capture_details import arithmetic
def main():
    out=BASE/'guard_analysis';out.mkdir(exist_ok=True);results=[];passed=True;cfg=read(ROOT/'configs/round6_guard.json')
    for j in cfg['G1']:
        id=j['id'];oldid='X_'+id[2:];d=BASE/'replay_guard'/id;old=OLD5/'replay'/oldid;t=read(d/'terminal.json');native=rows(d/'ccss_guard.jsonl');errors=[]
        if t['exit_code']!=0:errors.append('nonzero_process_exit')
        if len(native)!=1:errors.append('missing_or_multiple_native_call')
        if errors:results.append({'id':id,'passed':False,'errors':errors});passed=False;continue
        n=native[0];state=read(d/(id+'_R3.json'));initial=clauses(state);ar=arithmetic(d,id)
        for k in ['R1','R2','R3','intervals']:
            if read(d/(id+'_'+k+'.json'))!=read(old/(oldid+'_'+k+'.json')):errors.append('state_mismatch_'+k)
        actual=read(d/(id+'_progress.json'));previous=read(old/(oldid+'_progress.json'));strip=lambda p:{k:v for k,v in p.items() if k!='elapsed'}
        expected=[strip(p) for p in previous['points'] if p['step']<=n['exit_step_exact']];observed=[strip(p) for p in actual['points']]
        if expected!=observed:errors.append('deterministic_progress_prefix_mismatch')
        assert n['guard_enabled'] and n['stagnation_limit']==65536
        if j['M']=='ref':
            sol=read(d/(id+'_solution.json')) if (d/(id+'_solution.json')).exists() else None
            if not sol or n['exit_reason']!='sat_ccss_solution_only' or n['exit_step_exact']!=219 or clauses(sol['state'])!=0:errors.append('fast_solution_not_preserved')
        else:
            if n['exit_reason']!='ccss_stagnation_yield' or n['model_produced'] or n['last_global_best']<=0 or n['exit_step_exact']-n['last_improvement_step']!=65536:errors.append('slow_state_not_safely_yielded')
        good=not errors;passed &= good;oldterm=read(old/(oldid+'_terminal.json'));oldsearch=oldterm['phase_seconds']['ls_sampling_inclusive'];results.append({'id':id,'H':j['H'],'M':j['M'],'passed':good,'errors':errors,'reason':n['exit_reason'],'initial_unsat':initial,'best':n['last_global_best'],'last_improvement_step':n['last_improvement_step'],'exit_step_exact':n['exit_step_exact'],'search_wall':n['search_wall_seconds'],'search_cpu':n['search_cpu_seconds'],'process_wall':t['wall_from_batch_release'],'initialization_count':n['initialization_count'],'R0_R3_match':not any(x.startswith('state_mismatch') for x in errors),'progress_match':'deterministic_progress_prefix_mismatch' not in errors,'old_recorded_search_wall':oldsearch,'local_wall_difference_not_end_to_end':oldsearch-n['search_wall_seconds'],'trace_dropped':actual['dropped'],'arithmetic_audit':ar,'files':{str(p.relative_to(ROOT)):digest(p) for p in d.iterdir() if p.is_file()}})
    write(out/'G1_audit.json',{'passed':passed,'G_PASS_LOCAL':passed,'local_time_halved':passed and all(r['search_wall']<26 for r in results if r.get('M')!='ref'),'rows':results,'formal_models_added':0,'scope':'reduced CCSS only','new_solver_checks':0});csvwrite(out/'G1_replays.csv',[{k:v for k,v in r.items() if k not in ['arithmetic_audit','files']} for r in results]);print('G1 audit',passed);assert passed,'No-Go: G1 correctness/local validation failed; no G2 allowed'
if __name__=='__main__':main()
