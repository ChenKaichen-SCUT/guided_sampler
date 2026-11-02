"""Read-only arbitrary-precision and provenance audit; no solver/search calls."""
from common5 import *
import re
MIN128=-(1<<127);MAX128=(1<<127)-1;MIN64=-(1<<63);MAX64=(1<<63)-1
def number(raw):
    if raw is None:return None
    s=str(raw).strip()
    if re.fullmatch(r'\(-\s+\d+\)',s):s='-'+re.search(r'\d+',s).group()
    if not re.fullmatch(r'-?\d+',s):return None
    return int(s)
def bounded(v):return MIN128<=v<=MAX128
def arithmetic(directory,prefix):
    r1=read(directory/(prefix+'_R1.json'));r3=read(directory/(prefix+'_R3.json'));it=read(directory/(prefix+'_intervals.json'))
    counts=collections.Counter();model=[];known=[];mp=r1['consumed_map_copy']
    for rd in it['reads']:
        counts['reads']+=1
        if rd['name'] not in mp:assert rd['status']=='missing' and rd['raw'] is None;continue
        assert rd['raw']==mp[rd['name']];v=number(rd['raw'])
        expected='parse_error' if v is None else '128bit_overflow' if not bounded(v) else 'present'
        assert rd['status']==expected
        if expected=='present':assert int(rd['parsed'])==v
    assert len(it['variables'])==len(r1['vars'])==len(r3['intervals'])
    for i,v in enumerate(it['variables']):
        assert v['index']==i and v['name']==r1['vars'][i]['name']
        actual=None
        if v['is_lia']:
            name=v['name']
            if name.startswith('_new_var_'):
                x=name[len('_new_var_'):];xi=r1['name2tmp'].get(x)
                if xi in r1['pair_x']:
                    pi=r1['pair_x'].index(xi);y=r1['tmp_vars'][r1['pair_y'][pi]]['name'];a=number(mp.get(x));b=number(mp.get(y))
                    if a is not None and b is not None and bounded(a) and bounded(b) and bounded(a-b):actual=a-b
                counts['difference_variables']+=1
            else:
                a=number(mp.get(name));actual=a if a is not None and bounded(a) else None
            assert int(v['low'])<=int(r3['solution'][i])<=int(v['upper'])
        assert v['has_model_value']==(actual is not None)
        assert v['model_value']==(str(actual) if actual is not None else None)
        known.append(actual is not None);model.append(actual)
        counts['variables']+=1
    validity={}
    for e in it['inequalities']:
        l=r1['lits'][e['literal']];d=int(l['key']);valid=True
        for ids,cs,sign in [(l['pos_var'],l['pos'],1),(l['neg_var'],l['neg'],-1)]:
            for i,c in zip(ids,cs):
                if not known[i]:valid=False;continue
                term=sign*int(c)*model[i]
                if not bounded(term):valid=False;continue
                new=d+term
                if not bounded(new):valid=False
                # Native failed arithmetic leaves an implementation-defined wrapped intermediate;
                # compare computed_delta only for a fully valid inequality.
                d=new
        assert e['valid']==valid
        if valid:assert int(e['computed_delta'])==d
        validity[e['literal']]=valid;counts['valid_inequalities' if valid else 'invalid_inequalities']+=1
    for v in it['variables']:
        valid=sum(validity.get(abs(l),False) for l in v['literals'] if r1['lits'][abs(l)]['lia'] and not r1['lits'][abs(l)]['equal'])
        total=sum(r1['lits'][abs(l)]['lia'] and not r1['lits'][abs(l)]['equal'] for l in v['literals'])
        assert valid==v['valid_inequality_occurrences'] and total-valid==v['unknown_or_overflow_inequality_occurrences']
        ci={}
        for l in v['literal_intervals']:
            counts['literal_division_bounds']+=1;n=int(l['numerator']);c=int(l['coefficient']);s=l['signed_literal'];delta=int(l['delta']);assert n==c*int(v['model_value'])-delta
            if (s>0)==(c>0):
                b=n//c-(s<0 and n%c==0);expected=[1,0] if b<MIN64 else [MIN64,min(b,MAX64)]
            else:
                b=-((-n)//c)+(s<0 and n%c==0);expected=[1,0] if b>MAX64 else [max(b,MIN64),MAX64]
            assert list(map(int,l['interval']))==expected
            idx=l['clause'];old=ci.get(idx)
            if old is None or old[0]>old[1]:ci[idx]=expected
            elif expected[0]<=expected[1]:ci[idx]=[min(old[0],expected[0]),max(old[1],expected[1])]
        if 'domain' in v:
            domain=[max(int(v['low']),int(v['s_low'])),min(int(v['upper']),int(v['s_upper']))];assert list(map(int,v['domain']))==domain
            assert [[i,str(a),str(b)] for i,(a,b) in sorted(ci.items())]==v['clause_intervals']
            feasible=[max(a for a,b in ci.values()),min(b for a,b in ci.values())];assert feasible==list(map(int,v['feasible']))
            result=list(map(int,v['result']));assert result==list(map(int,r3['intervals'][v['index']]))
            if result[0]<=result[1]:
                assert domain[0]<=result[0]<=result[1]<=domain[1]
                if v['branch']=='feasible':assert result==[max(domain[0],feasible[0]),min(domain[1],feasible[1])]
                elif feasible[0]<=feasible[1]:assert result[1]<feasible[0] or result[0]>feasible[1]
    return {'passed':True,'counts':dict(counts),'new_solver_calls':0,'new_search_steps':0,'files':{str((directory/(prefix+'_'+x+'.json')).relative_to(ROOT)):digest(directory/(prefix+'_'+x+'.json')) for x in ['R1','R3','intervals']}}
def qrow(d,n):return next((q for q in rows(d/'queries.jsonl') if q['query']==n),None)
def inputrow(d,n):return next((q for q in rows(d/'query_inputs.jsonl') if q['query_id']==n),None)
def receipt(d,n):return next((q for q in rows(d/'formal_receipts.jsonl') if q['query']==n),None)
def main():
    result={};history=[];source=[]
    for mode,oldmode in [('S_ref','S_ref'),('S_full','S_cov'),('S_support',None)]:
        d=BASE/'W'/('convert_'+mode);r=read(d/'ccss_2_recipe.json');ex=r['exchange'];events=rows(d/'exchange_events.jsonl');last={}
        assert not any(e['kind']=='trace_overflow' for e in events)
        for e in events:
            if e['kind']=='exchange_write' and e['manager']==ex['manager'] and e['batch']<=ex['latest_batch']:
                z=dict(e);z.pop('external_query');last[e['name']]=z
        assert last==ex['producers'];assert {k:v['raw'] for k,v in last.items()}==ex['map'];assert set(ex['iteration'])==set(ex['map'])
        it=read(d/'ccss_2_intervals.json');consumed={x['name'] for x in it['reads']};formal=receipt(d,3);values={x['name']:number(x['value']) for x in formal['typed']}
        for k,v in ex['map'].items():
            p=ex['producers'][k];source.append({'mode':mode,'name':k,'consumed':k in consumed,'latest_batch':p['batch']==ex['latest_batch'],'producer_query':p['query'],'original_formal_variable':k in values,'formal_numeric_equal':number(v)==values[k] if k in values else None,'sort':p['identity']['sort'],'producer_event_verified':True})
        result[mode]={'provenance_passed':True,'map_entries':len(ex['map']),'read_keys':len(consumed),'current_generation':sum(x['batch']==ex['latest_batch'] for x in last.values()),'prior_generation_consumed':sum(k in consumed and x['batch']!=ex['latest_batch'] for k,x in last.items()),'numeric_formal_disagreements':sum(number(v)!=values[k] for k,v in ex['map'].items() if k in values),'original_variables_missing_from_map':len(set(values)-set(ex['map'])),'arithmetic':arithmetic(d,'ccss_2'),'exchange_events_sha256':digest(d/'exchange_events.jsonl')}
        if oldmode:
            od=OLD/'runs'/('convert_'+oldmode);oq=qrow(od,4);nq=qrow(d,4);oi=inputrow(od,3);ni=inputrow(d,3);of=receipt(od,3)
            history.append({'new_mode':mode,'old_mode':oldmode,'q3_model_hash_equal':formal['model_hash']==of['model_hash'],'old_q3_hash':of['model_hash'],'new_q3_hash':formal['model_hash'],'q3_reference_equal':oi['reference']==ni['reference'],'q3_reference_hash_equal':oi['reference_hash']==ni['reference_hash'],'q3_host_rng_before_equal':oi['rng_before']==ni['rng_before'],'q3_host_rng_after_equal':oi['rng_after']==ni['rng_after'],'q4_seed_equal':oq['highdiv_ls_seed']==nq['highdiv_ls_seed'],'old_q4_seed':oq['highdiv_ls_seed'],'new_q4_seed':nq['highdiv_ls_seed'],'old_q4_result':oq['result'],'new_q4_result':nq['result'],'old_q4_seconds':oq['check_seconds'],'new_q4_seconds':nq['check_seconds'],'old_q4_cutoff':oq['granted_timeout'],'new_q4_cutoff':nq['granted_timeout'],'historical_internal_map_or_RNG_available':False,'raw_hashes':{str((x/f).relative_to(ROOT)):digest(x/f) for x in [od,d] for f in ['formal_receipts.jsonl','queries.jsonl','query_inputs.jsonl']}})
    write(BASE/'analysis/X_capture_details.json',{'passed':True,'sources':result,'history':history,'arbitrary_precision':True,'solver_calls':0});csvwrite(BASE/'analysis/X_producer_identity_audit.csv',source)
    print({k:{a:v[a] for a in ['map_entries','read_keys','prior_generation_consumed','numeric_formal_disagreements']} for k,v in result.items()})
if __name__=='__main__':main()
