from common5 import *
from audit_capture_details import arithmetic
def clauses(state):
    sol=list(map(int,state['solution']));truth={};unsat=[]
    for i,v in enumerate(state['vars']):
        if v['is_lia']:assert int(v['low'])<=sol[i]<=int(v['upper'])
    for i,l in enumerate(state['lits']):
        if not l['index']:continue
        if l['lia']:
            d=int(l['key'])+sum(int(c)*sol[v] for c,v in zip(l['pos'],l['pos_var']))-sum(int(c)*sol[v] for c,v in zip(l['neg'],l['neg_var']))
            assert d==int(l['delta']);truth[i]=d==0 if l['equal'] else d<=0
        else:truth[i]=sol[int(l['delta'])]>0
    for i,c in enumerate(state['clauses']):
        count=sum(truth[abs(l)] if l>0 else not truth[abs(l)] for l in c['literals']);assert c['sat_count']==count
        if count==0:unsat.append(i)
    assert set(unsat)==set(state['unsat']);return len(unsat)
def main():
    details={};plan=read(ROOT/'manifests/round5_X_plan.json')
    for j in plan['rows']:
        if not j['execute']:continue
        id=j['id'];d=BASE/'replay'/id;ar=arithmetic(d,id);s=read(d/(id+'_R3.json'));initial=clauses(s);candidate=d/(id+'_solution.json');checked=False
        if candidate.exists():
            c=read(candidate);assert clauses(c['state'])==0 and c['native_check_solution'] and not c['overflow'];checked=True
        points=read(d/(id+'_progress.json'));assert points['dropped']==0
        best=float('inf');last=0;longest=0;first=None;global_improvements=[]
        for p in points['points']:
            longest=max(longest,p['step']-last)
            if p['best']<best:
                if first is None and p['best']<initial:first=p
                best=p['best'];last=p['step'];global_improvements.append(p)
        r1=read(d/(id+'_R1.json'));original=read(ROOT/j['recipe']);assert sha_text(r1['rng'])==sha_text(original['R0'])
        details[id]={'arithmetic':ar,'independent_initial_unsat':initial,'independent_reduced_candidate_validated':checked,'validation_scope':'reduced CCSS only; original converter recovery not validated','first_improvement':first,'best_global':best,'global_improvements':global_improvements,'longest_no_global_improvement_observed_steps_lower_bound':longest,'last_recorded_step':points['points'][-1]['step'],'exact_terminal_step':'not_recorded_on_cutoff','native_terminal':read(d/(id+'_terminal.json'))}
    same_h=[]
    for left,right in [('X_rr','X_rc'),('X_cr','X_cc'),('X_rr','X_r0'),('X_cc','X_c0')]:
        a=read(BASE/'replay'/left/(left+'_R1.json'));b=read(BASE/'replay'/right/(right+'_R1.json'));a.pop('consumed_map_copy');b.pop('consumed_map_copy');assert a==b
        same_h.append({'left':left,'right':right,'R1_nonmap_state_identical':True})
    recipes=[read(BASE/'capture'/k/'recipe.json') for k in ['ref','full']];keys=['seed','cutoff_seconds','R0','build_lits','make_lits_space','clause_vec','use_interval_move','literal_identity','compiler','stdlib'];equal={k:recipes[0][k]==recipes[1][k] for k in keys};assert all(equal.values())
    m1,m2=[r['exchange']['map'] for r in recipes];readkeys={r['name'] for r in read(BASE/'replay/X_rr/X_rr_intervals.json')['reads']};changed=[k for k in m1.keys()|m2.keys() if m1.get(k)!=m2.get(k)]
    write(BASE/'analysis/X_independent_arithmetic_audit.json',{'passed':True,'details':details,'same_H_controls':same_h,'two_H_nonmap_equality':equal,'different_map_keys':changed,'different_consumed_map_keys':[k for k in changed if k in readkeys],'new_solver_calls':0,'new_search_calls':0,'source_sha256':digest(pathlib.Path(__file__))})
    print('Independent exact arithmetic and native-clause audits passed for',len(details),'X attempts')
if __name__=='__main__':main()
