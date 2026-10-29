import sys,json,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from evaluate_exact import load_metric,totals
m=load_metric();formula=pathlib.Path(sys.argv[1]).read_text();rows=json.loads(pathlib.Path(sys.argv[2]).read_text());cpp=json.loads(pathlib.Path(sys.argv[3]).read_text())
s=m.WireCoverageStatistics();e=m.ManualSatisfiesMetric(formula,s);root=m.z3.And(e._solver.assertions());stack=[root];nodes=[];seen=set()
while stack:
    node=stack.pop()
    if node.get_id() in seen:continue
    seen.add(node.get_id());nodes.append(node);stack.extend(reversed(node.children()))
previous=(0,0,0)
for row,actual in zip(rows,cpp['prefixes']):
    fresh=m.WireCoverageStatistics();fresh_eval=m.ManualSatisfiesMetric(formula,fresh)
    sample=[(k,int(v)) for k,v in row.items()];fresh_eval.count_sample(sample);e.count_sample(sample);c,t,o=totals(s)
    assert (c,t,o)==(actual['covered'],actual['total'],actual['observed'])
    assert c-previous[0]==actual['new_covered'] and o-previous[2]==actual['new_observed']
    assert len(nodes)==len(actual['nodes'])
    for node,entry in zip(nodes,actual['nodes']):
        one,zero,sort=s._storage[node.get_id()];f1,f0,_=fresh._storage[node.get_id()]
        assert int(one)==int(entry['seen1']) and int(zero)==int(entry['seen0']),entry
        assert bool(f1 or f0)==entry['visited'],entry
    previous=c,t,o
print(json.dumps({'passed':True,'prefixes':len(rows),'nodes':len(nodes),'target_checks':sum(cpp['targets_checked']),'hints':cpp['hints_checked']}))
