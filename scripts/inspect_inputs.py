#!/usr/bin/env python3
import collections,sys,time,re
from common import *
from evaluate_exact import load_metric

def main():
    m=load_metric();data=[]
    for entry in read(ROOT/'manifests/inputs.json'):
        p=ROOT.parent/entry['path'];t=time.monotonic();stat=m.WireCoverageStatistics();manual=m.ManualSatisfiesMetric(p.read_text(),stat)
        stack=list(manual._solver.assertions());seen=set();vars={};ops=collections.Counter();depths={}
        while stack:
            e=stack.pop()
            if e.get_id() in seen:continue
            seen.add(e.get_id());ops[str(e.decl().kind())]+=1
            if m.z3.is_const(e) and e.decl().kind()==m.z3.Z3_OP_UNINTERPRETED:
                name=str(e.decl().name());assert all(x not in name for x in ':;\n\r');assert name not in vars or vars[name]==str(e.sort());vars[name]=str(e.sort())
            stack.extend(e.children())
        logic=re.search(r'\(set-logic\s+([^\s)]+)',p.read_text())
        data.append({**entry,'logic':logic.group(1) if logic else 'unspecified','metric_nodes':len(stat._storage),'total':sum(stat.node_total(i,s) for i,(a,b,s) in stat._storage.items()),'variables':len(vars),'sorts':dict(collections.Counter(vars.values())),'operations':dict(ops),'compatibility':'passed','inspect_seconds':time.monotonic()-t})
        print(p.name,len(vars),len(stat._storage),flush=True)
    write(ROOT/'manifests/input_ast.json',data)
if __name__=='__main__':main()
