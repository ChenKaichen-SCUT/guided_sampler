#!/usr/bin/env python3
"""Read-only adapter: imports the unmodified frozen metric and its exact classes."""
import argparse,importlib.util,json,pathlib,sys
from common import ROOT,metric_path,write,digest

def load_metric():
    spec=importlib.util.spec_from_file_location('frozen_highdiv_metric',metric_path());m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def totals(stat):
    covered=sum(stat.node_count(t,f,s) for t,f,s in stat._storage.values())
    total=sum(stat.node_total(i,s) for i,(t,f,s) in stat._storage.items())
    observed=sum((int(t).bit_count()+int(f).bit_count()) for t,f,s in stat._storage.values())
    return covered,total,observed

def evaluate(formula,samples,receipts=None,out=None):
    metric=load_metric();stat=metric.WireCoverageStatistics();manual=metric.ManualSatisfiesMetric(pathlib.Path(formula).read_text(),stat)
    receipt_rows=[json.loads(l) for l in pathlib.Path(receipts).read_text().splitlines()] if receipts else []
    trace=[];previous=(0,0,0);legal=True;identities=set();all_vars={}
    z3=metric.z3;root=z3.And(manual._solver.assertions());stack=[root];seen=set()
    while stack:
        e=stack.pop()
        if e.get_id() in seen:continue
        seen.add(e.get_id())
        if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED:all_vars[str(e.decl().name())]=e
        stack.extend(e.children())
    with open(samples) as f:
        for i,sample in enumerate(metric.parse_samples(f)):
            mapping=dict(sample)
            if set(mapping)!=set(all_vars):raise RuntimeError('Incomplete original-variable projection')
            key=tuple(sorted(sample))
            if key in identities:raise RuntimeError('Duplicate formal sample')
            identities.add(key)
            manual_ok=bool(manual.count_sample(sample))
            # Independent exact substitution and Z3 simplification, no additional
            # constraints/solver check needed for fully assigned quantifier-free F.
            pairs=[(e,z3.IntVal(mapping[n],ctx=metric.CTX) if z3.is_int(e) else z3.BoolVal(bool(mapping[n]),ctx=metric.CTX)) for n,e in all_vars.items()]
            direct=z3.simplify(z3.substitute(root,*pairs))
            direct_ok=z3.is_true(direct)
            legal=legal and manual_ok and direct_ok
            c,t,o=totals(stat);r=receipt_rows[i] if receipt_rows else {}
            row={'index':i,'covered':c,'total':t,'observed':o,'new_covered':c-previous[0],'new_observed':o-previous[2],
                 'legal_manual':manual_ok,'legal_substitution':direct_ok,'commit_complete':r.get('commit_complete'),'source':r.get('source')}
            if r.get('new_covered') is not None and (r['new_covered']!=row['new_covered'] or r['new_observed']!=row['new_observed']):raise RuntimeError('Online/offline coverage mismatch')
            trace.append(row);previous=(c,t,o)
    c,t,o=totals(stat);result={'covered':c,'total':t,'observed':o,'models':len(trace),'legal':legal,'official_class_result':stat.result,'prefixes':trace,
        'metric_sha256':digest(metric_path()),'formula_sha256':digest(formula),'samples_sha256':digest(samples),
        'seen':{str(i):{'seen1':str(int(a)),'seen0':str(int(b)),'sort':s} for i,(a,b,s) in stat._storage.items()}}
    if out:write(out,result)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('-f',required=True);p.add_argument('-s',required=True);p.add_argument('--receipts');p.add_argument('-o',required=True);a=p.parse_args();r=evaluate(a.f,a.s,a.receipts,a.o);print(json.dumps({k:v for k,v in r.items() if k not in ['prefixes','seen']}));sys.exit(0 if r['legal'] else 1)
