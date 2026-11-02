"""Frozen P1 synthetic input groups 6--9: construction only, no SMT/search."""
from common5 import *
variant,attempt=sys.argv[1:3];out=BASE/'correctness'/f'exchange_edges_{variant}_{attempt}';out.mkdir(exist_ok=False)
checks=sorted((BASE/'correctness').glob(variant+'_*/summary.json'));assert checks;parent=checks[-1].parent;source=read(parent/'S_full_on/ccss_2_recipe.json')
recipe={**source,'make_lits_space':3,'build_lits':['0 true','1 ( <= ( + x ( * -1 y ) ) 10 )','2 ( >= ( + x ( * -1 y ) ) -10 )'],'clause_vec':[[1],[2]],'literal_identity':[],'synthetic_fixture':True}
write(out/'recipe.json',recipe);exe=ROOT/f'build/round5-ccss-replay-{variant}';env=os.environ.copy()
if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
cases={'negative':{'x':'(- 17)','y':'-19'},'empty':{},'missing_y':{'x':'-17'},'parse_error':{'x':'not-an-int','y':'-19'},'overflow128':{'x':str(1<<127),'y':'0'},'difference_overflow':{'x':str((1<<127)-1),'y':str(-(1<<127))}}
results={}
for name,map_ in cases.items():
    d=out/name;d.mkdir();write(d/'map.json',map_);cmd=[str(exe),str(out/'recipe.json'),str(d/'map.json'),str(d),'edge','1'];r=subprocess.run(cmd,cwd=d,env=env,capture_output=True,text=True,timeout=30);(d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr);write(d/'attempt.json',{'command':cmd,'exit_code':r.returncode,'search_steps':0});assert r.returncode==0,(name,r.stderr[-1000:])
    state=read(d/'edge_R3.json');ints=read(d/'edge_intervals.json');assert state['pair_x'] and state['pair_y'];assert len(state['vars'])==len(state['solution'])-10 or len(state['vars'])<=len(state['solution'])
    variable=next(v for v in ints['variables'] if v['name'].startswith('_new_var_'));assert variable['has_model_value']==(name=='negative'),(name,variable)
    if name=='negative':assert int(variable['model_value'])==2
    for i,v in enumerate(state['vars']):
        if v['is_lia']:assert int(v['low'])<=int(state['solution'][i])<=int(v['upper'])
    statuses=[r['status'] for r in ints['reads']]
    if name=='overflow128':assert '128bit_overflow' in statuses
    if name=='parse_error':assert 'parse_error' in statuses
    if name in ['empty','missing_y']:assert 'missing' in statuses
    assert read(d/'edge_terminal.json')['search_started']==False
    results[name]={'read_statuses':statuses,'difference_model_valid':variable['has_model_value'],'initialization_in_hard_bounds':True,'search_steps':0}
write(out/'summary.json',{'passed':True,'cases':results,'replay_sha256':digest(exe),'library_sha256':digest(ROOT/f'deps/round5_{variant}/lib/libz3.so'),'synthetic_only':True,'SMT_calls':0})
print('Exchange edges passed',variant)
