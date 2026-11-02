"""Exact frozen official observations, stable original-DAG bit partitions; no checks."""
from common5 import *
from semantic_oracle import Witness,metric,z3,dag
import functools

def replay_official_observations(formula, directory):
    text=pathlib.Path(formula).read_text();stat=Witness();manual=metric.ManualSatisfiesMetric(text,stat)
    nodes,ids=dag(z3.And(manual._solver.assertions()));width=[1 if z3.is_bool(n) else 64 for n in nodes]
    universe={64*i+b for i,n in enumerate(nodes) if n.get_id() in stat._storage for b in range(width[i])}
    catalog=rows(directory/'a_atom_catalog.jsonl');known=collections.defaultdict(int)
    for e in catalog:
        for r in e['rules']:known[r['node']]|=int(r['known_one'])|int(r['known_zero'])
    stored=read(directory/'original_nodes.json');assert len(nodes)==len(stored)
    for i,n in enumerate(nodes):
        assert stored[i]['sort']==str(n.sort()) and stored[i]['children']==[ids[c.get_id()] for c in n.children()]
        if not n.children():assert stored[i]['expr']==n.sexpr() or stored[i]['expr']==str(n)
    fingerprints=[sha_text(n.sexpr()) for n in nodes]
    receipts=rows(directory/'formal_receipts.jsonl');prefix=[];seen=[set(),set()];first={};observations=[];samples=[]
    with (directory/'samples.formal').open() as f:
        for i,sample in enumerate(metric.parse_samples(f)):
            stat.current={};assert manual.count_sample(sample),'Invalid formal model'
            samples.append(dict(sample));obs={ids[n]:int(v) for n,v in stat.current.items()};observations.append(obs)
            for n,v in obs.items():
                for b in range(width[n]):
                    bit=64*n+b;d=(v>>b)&1
                    if bit not in seen[d]:first[bit,d]=(i+1,receipts[i]['source'])
                    seen[d].add(bit)
            covered=seen[0]&seen[1]
            assert len(covered)==receipts[i]['covered']
            prefix.append({'seen':[seen[0].copy(),seen[1].copy()],'covered':covered.copy(),'receipt':receipts[i]})
    assert len(receipts)==len(prefix)
    return dict(nodes=nodes,ids=ids,width=width,universe=universe,known=known,fingerprints=fingerprints,first=first,prefix=prefix,observations=observations,samples=samples,receipts=receipts,formula=text,sha=digest(formula),source_hashes={f:digest(directory/f) for f in ['samples.formal','formal_receipts.jsonl','a_atom_catalog.jsonl','original_nodes.json']})

def partition_from_first_model(left,right):
    assert left['universe']==right['universe'];groups={}
    common=set()
    for r in [left,right]:
        a=r['prefix'][0]['seen'];pool={64*n+b for n,mask in r['known'].items() for b in range(r['width'][n]) if mask>>b&1 and (64*n+b in a[0])!=(64*n+b in a[1])}
        if r is left:common=pool
        else:common&=pool
    L=left['prefix'][0]['seen'];R=right['prefix'][0]['seen']
    for bit in left['universe']:
        ls=(bit in L[0],bit in L[1]);rs=(bit in R[0],bit in R[1])
        groups[bit]='G4_initial_difference' if ls!=rs else 'G0' if all(ls) else 'G3' if not any(ls) else 'G1' if bit in common else 'G2'
    assert len(groups)==len(left['universe'])
    return groups,common

def aggregate(r,indices):
    seen=[set(),set()];first={}
    for i in indices:
        for n,v in r['observations'][i].items():
            for b in range(r['width'][n]):
                d=(v>>b)&1;bit=64*n+b
                if bit not in seen[d]:first[bit,d]=(i+1,r['receipts'][i]['source'])
                seen[d].add(bit)
    return seen,first

def compare_prefixes(left,right,groups,alignment,li,ri,instance):
    ls,lf=aggregate(left,li);rs,rf=aggregate(right,ri);lc=ls[0]&ls[1];rc=rs[0]&rs[1];out=[];details=[]
    for g in sorted(set(groups.values())):
        lo={b for b in lc-rc if groups[b]==g};ro={b for b in rc-lc if groups[b]==g}
        out.append(dict(instance=instance,alignment=alignment,group=g,left_models=len(li),right_models=len(ri),left_covered=len(lc),right_covered=len(rc),ref_only=len(lo),cov_only=len(ro),net=len(ro)-len(lo),partition_size=sum(v==g for v in groups.values())))
    assert sum(x['net'] for x in out)==len(rc)-len(lc)
    # Pure values only explain the unobserved counterpart, never update observations.
    pure={}
    for side,own,other,os,of,other_indices,bits in [('ref',left,right,rs,rf,ri,lc-rc),('cov',right,left,ls,lf,li,rc-lc)]:
        evaluator=metric.ManualSatisfiesMetric(other['formula'])
        for bit in sorted(bits):
            n,b=divmod(bit,64);known=[int(bit in os[d]) for d in range(2)];missing=[d for d in range(2) if not known[d]]
            value_possible=[]
            for d in missing:
                key=(side,n)
                if key not in pure:
                    expr=other['nodes'][n];fn=evaluator._build_bool(expr) if z3.is_bool(expr) else evaluator._build_int(expr)
                    pure[key]=[int(fn(other['samples'][i])) for i in other_indices]
                value_possible.append(any((v>>b)&1==d for v in pure[key]))
            own_first=lf if side=='ref' else rf
            details.append(dict(instance=instance,alignment=alignment,input_sha=left['sha'],node=n,node_fingerprint=left['fingerprints'][n],bit=b,group=groups[bit],covered_only=side,other_visited=any(known),other_seen0=known[0],other_seen1=known[1],missing_desired=str(missing),missing_value_available_without_reach=str(value_possible),first0_model=own_first[bit,0][0],first0_source=own_first[bit,0][1],first1_model=own_first[bit,1][0],first1_source=own_first[bit,1][1],covered_source=max(own_first[bit,0],own_first[bit,1])[1]))
    return out,details

def compare_pair(left,right,instance,outdir,label=''):
    groups,pool=partition_from_first_model(left,right);summary=[];details=[]
    n=min(len(left['prefix']),len(right['prefix']))
    align=[('formal_prefix_'+str(k),list(range(k)),list(range(k))) for k in range(1,n+1)]
    align.append(('full_session',list(range(len(left['prefix']))),list(range(len(right['prefix'])))))
    lc=[i for i,r in enumerate(left['receipts']) if r['source']=='CDCL'];rc=[i for i,r in enumerate(right['receipts']) if r['source']=='CDCL']
    if instance=='convert':align.append(('CDCL_first4_mixed_trajectory_not_equal',lc[:4],rc[:4]))
    # Only observed common time, never extend a finished query-limited run.
    tmax=min(left.get('elapsed',left['receipts'][-1]['output_complete']),right.get('elapsed',right['receipts'][-1]['output_complete']))
    for t in [1,5,10,20,30,60]:
        if t<=tmax:align.append(('wall_'+str(t),[i for i,r in enumerate(left['receipts']) if r['output_complete']<=t],[i for i,r in enumerate(right['receipts']) if r['output_complete']<=t]))
    for name,li,ri in align:
        s,d=compare_prefixes(left,right,groups,name,li,ri,instance);summary+=s;details+=d
    return summary,details,[dict(instance=instance,input_sha=left['sha'],node=bit//64,node_fingerprint=left['fingerprints'][bit//64],bit=bit%64,group=g) for bit,g in sorted(groups.items())]

def main():
    out=BASE/'readonly';summaries=[];diffs=[];partition=[];meta=[]
    for inst in ['convert','SMT_random','SMT_real']:
        data=[]
        for mode in ['S_ref','S_cov']:
            j=next(j for j in read(ROOT/'manifests/round4_short_plan.json')['jobs'] if j['id']==inst+'_'+mode)
            d=OLD/'runs'/j['id'];r=replay_official_observations(ROOT/j['input'],d);r['elapsed']=read(d/'summary.json')['elapsed'];data.append(r)
            meta.append({'run':j['id'],'source_hashes':r['source_hashes'],'models':len(r['prefix']),'covered':len(r['prefix'][-1]['covered']),'input_sha':r['sha']})
        s,d,p=compare_pair(*data,inst,out);summaries+=s;diffs+=d;partition+=p
        print(inst,[(r['group'],r['net']) for r in s if r['alignment']=='full_session'],flush=True)
    for inst,net,g1 in [('SMT_random',-94,78),('SMT_real',-264,-37)]:
        s=[r for r in summaries if r['instance']==inst and r['alignment']=='formal_prefix_8'];assert sum(r['net'] for r in s)==net;assert next(r['net'] for r in s if r['group']=='G1')==g1
    csvwrite(out/'coverage_bit_partition.csv',partition);csvwrite(out/'coverage_bit_differences.csv',diffs);csvwrite(out/'coverage_prefix_comparisons.csv',summaries)
    write(out/'coverage_summary.json',{'passed':True,'sources':meta,'solver_calls':0,'semantics':'frozen official visitor; pure unvisited values diagnostic only','cross_run_identity':'input SHA + stable original DAG and expression SHA256; AST IDs not compared','rows':summaries})
if __name__=='__main__':main()
