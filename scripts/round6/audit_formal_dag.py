"""Original DAG identity for all F target logs, without any solver check."""
from common6 import *
from semantic_oracle import metric,z3,dag
assert (BASE/'F_FINISHED.json').exists();records=[];plan=read(ROOT/'manifests/round6_formal_plan.json')
for i,entry in enumerate(read(ROOT/'manifests/inputs.json')):
    formula=ROOT.parent/entry['path'];m=metric.ManualSatisfiesMetric(formula.read_text());nodes,ids=dag(z3.And(m._solver.assertions()))
    for j in [j for j in plan['jobs'] if j['input_index']==i]:
        p=BASE/'formal'/j['id']/'original_nodes.json';stored=read(p);assert len(stored)==len(nodes)
        for n,s in zip(nodes,stored):
            assert s['sort']==str(n.sort()) and s['operator']==n.decl().kind() and s['children']==[ids[c.get_id()] for c in n.children()]
            if not n.children():assert s['expr'] in [n.sexpr(),str(n)]
        records.append({'run':j['id'],'node_count':len(nodes),'original_nodes_sha256':digest(p),'input_sha256':digest(formula),'passed':True})
write(BASE/'formal_analysis/dag_identity_audit.json',{'passed':True,'rows':records,'solver_checks_added':0,'metric_sha256':digest(metric_path())});print('Verified32 original DAGs for target interpretation')
