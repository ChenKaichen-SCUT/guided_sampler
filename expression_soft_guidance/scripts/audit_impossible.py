"""Re-prove exclusion certificates using unmodified upstream Z3, outside timing."""
import argparse,builtins,concurrent.futures,hashlib,json,pathlib,sys,time
from prepare import ROOT,WORKSPACE,write

def audit_bench(item):
    bench,paths=item
    base=WORKSPACE/'guided_sampler/deps/baseline'
    sys.path.insert(0,str(base/'lib/python3.10/site-packages'));builtins.Z3_LIB_DIRS=[str(base/'lib')]
    import z3
    root=z3.And(z3.parse_smt2_file(str(ROOT/'benchmarks'/bench)))
    nodes=[];seen=set();todo=[root];declarations={}
    while todo:
        e=todo.pop()
        if e.get_id() in seen:continue
        seen.add(e.get_id());nodes.append(e);todo.extend(reversed(e.children()))
        if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED:declarations[str(e.decl().name())]=e
    solver=z3.Solver();solver.add(root);solver.set(timeout=3000)
    cache={};errors=[];claims=proofs=targets=0;outcomes={}
    for path in paths:
        records=[json.loads(line) for line in path.read_text().splitlines()]
        byquery={}
        for row in records:
            byquery.setdefault(row['query'],[]).append(row)
            if row['kind']=='probe' and row['result']!='unsat':continue
            e=nodes[row['node']];key=json.dumps({k:v for k,v in row.items() if k not in ['query','wall']},sort_keys=True);claims+=1
            if key in cache:continue
            bad=[]
            if row['kind']=='static':
                k=row['modulo_bits'];r=row['residue'];mask=(1<<k)-1;value=r
                if z3.is_bool(e):
                    bad=[e!=bool(row['value'])];mask=1;value=row['value']
                else:
                    if k:bad.append(e%(1<<k)!=r)
                    lo=int(row['lower']) if 'lower' in row else None;hi=int(row['upper']) if 'upper' in row else None
                    if lo is not None:bad.append(e<lo)
                    if hi is not None:bad.append(e>hi)
                    if lo is not None and hi is not None and lo<=hi:
                        for bit in range(64):
                            if (lo>>bit)==(hi>>bit):
                                mask|=1<<bit
                                if (lo>>bit)&1:value|=1<<bit
                                else:value&=~(1<<bit)
                if mask!=row['mask'] or value!=row['value']:errors.append('certificate bit extraction mismatch')
            else:
                assert row['scope']=='original_F_and_Reach'
                reach=z3.parse_smt2_string('(assert '+row['reach']+')',decls=declarations)[0]
                bit=row['bit'];side=int(row['desired'])
                bit_goal=e==bool(side) if z3.is_bool(e) else (e/(1<<bit))%2==side
                bad=[z3.And(reach,bit_goal)]
            violation=z3.simplify(z3.Or(bad));result=z3.unsat
            if not z3.is_false(violation):
                solver.push();solver.add(violation);result=solver.check();solver.pop()
            proofs+=1;cache[key]=str(result);outcomes[str(result)]=outcomes.get(str(result),0)+1
            if result!=z3.unsat:errors.append(f'unverified exclusion: node {row["node"]} {row["kind"]} {result}')
        blocked={}
        for query in map(json.loads,(path.parent/'queries.jsonl').read_text().splitlines()):
            for row in byquery.get(query['query'],[]):
                no0,no1=blocked.get(row['node'],(0,0))
                if row['kind']=='static':no0|=row['mask']&row['value'];no1|=row['mask']&~row['value']
                elif row['result']=='unsat':
                    if row['desired']:no1|=1<<row['bit']
                    else:no0|=1<<row['bit']
                blocked[row['node']]=(no0,no1)
            if 'target' in query:
                t=query['target'];no0,no1=blocked.get(t['node'],(0,0));targets+=1
                if t['mask']&((no1&t['desired'])|(no0&~t['desired'])):errors.append('proven-impossible side was selected again')
    return dict(bench=bench,logged_claims=claims,unique_proofs=proofs,outcomes=outcomes,target_filter_checks=targets,errors=sorted(set(errors)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    folder=ROOT/'results'/args.name;groups={};start=time.monotonic()
    for p in folder.glob('*/impossible.jsonl'):
        bench=json.loads((p.parent/'run.json').read_text())['bench'];groups.setdefault(bench,[]).append(p)
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:results=list(executor.map(audit_bench,sorted(groups.items())))
    report=dict(all_passed=all(not r['errors'] for r in results),benches=results,wall=time.monotonic()-start)
    write(folder/'impossible_audit.json',json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
    if not report['all_passed']:raise SystemExit(1)
if __name__=='__main__':main()
