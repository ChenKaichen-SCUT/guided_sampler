"""Two equivalent cold encodings. Only Shared reuses prefixes and bit predicates."""
import z3,time,contextlib
from independent import export,observations
from oracle_encoder import EncodingTimeout,bit_condition
# This module is loaded under cost_oracle_encoder by tests/worker; legacy import
# above resolves to the frozen refinement module, not this file.
def problem(root,models,position,deadline,mode,stage=None):
    shared=mode=='OracleShared';stats={'prefix_argument_references':0,'bit_requests':0,'bit_cache_hits':0,'encoded_nodes':0,'encoded_observations':0}
    def check():
        if time.monotonic()>=deadline:raise EncodingTimeout()
    def phase(name):return stage(name,stats) if stage else contextlib.nullcontext()
    with phase('export_ast'):ast,nodes,vs=export(root);stats['original_nodes']=len(nodes);stats['original_edges']=sum(len(n['children']) for n in ast['nodes'])
    with phase('reach_build'):
        reach=reach_conditions(root,deadline,shared,(ast,nodes,vs),stats)
    with phase('prefix_observations'):
        history=set()
        for m in models[:position-1]:check();history |= observations(ast,m)[1]
        check();legal,seen=observations(ast,models[position-1]);assert legal
        protected=seen-history;targets=[(i,b,1-v) for i,b,v in sorted(history) if (i,b,1-v) not in history and (i,b,1-v) not in seen]
        stats.update(protected_count=len(protected),target_count=len(targets));check()
    meta={**stats,'actual_hard_conditions':[]}
    if not targets:return None,{**meta,'status':'no_strict_covered_target'},(ast,nodes,vs,reach,history,seen)
    bits={}
    def bit(i,b,v):
        check();stats['bit_requests']+=1
        if not shared:return bit_condition(nodes[i],b,v)
        key=(i,b)
        if key in bits:stats['bit_cache_hits']+=1
        else:bits[key]=bit_condition(nodes[i],b,True)
        return bits[key] if v else z3.Not(bits[key])
    with phase('protected_build'):
        by_node={}
        for i,b,v in sorted(protected):by_node.setdefault(i,[]).append(bit(i,b,v));stats['encoded_observations']+=1
        clauses=[z3.And(reach[i],*cs) for i,cs in by_node.items()];check()
    with phase('extra_build'):
        if shared:
            by_node={}
            for i,b,v in targets:by_node.setdefault(i,[]).append(bit(i,b,v));stats['encoded_observations']+=1
            extra=[z3.And(reach[i],z3.Or(cs)) for i,cs in by_node.items()]
        else:
            extra=[]
            for i,b,v in targets:extra.append(z3.And(reach[i],bit(i,b,v)));stats['encoded_observations']+=1
        formula=z3.And(root,*clauses,z3.Or(extra));check()
        # Exact unique expression-DAG size, charged equally for both encodings.
        todo=[formula];visited=set();edges=0
        while todo:
            check();e=todo.pop();i=e.get_id()
            if i in visited:continue
            visited.add(i);cs=e.children();edges+=len(cs);todo.extend(cs)
        stats.update(problem_nodes=len(visited),problem_edges=edges)
    return formula,dict(stats),(ast,nodes,vs,reach,history,seen)

def reach_conditions(root,deadline,shared,exported=None,stats=None):
    ast,nodes,vs=exported or export(root);stats=stats if stats is not None else {'prefix_argument_references':0,'encoded_nodes':0}
    incoming=[[] for _ in nodes];incoming[0]=[z3.BoolVal(True,ctx=root.ctx)];post=[];seen=set();todo=[(0,False)]
    while todo:
        i,done=todo.pop()
        if done:post.append(i);continue
        if i in seen:continue
        seen.add(i);todo.append((i,True));todo.extend((c,False) for c in reversed(ast['nodes'][i]['children']))
    reach=[None]*len(nodes)
    for i in reversed(post):
        if time.monotonic()>=deadline:raise EncodingTimeout()
        n=ast['nodes'][i];cs=n['children'];r=z3.Or(incoming[i]);reach[i]=r;stats['encoded_nodes']+=1
        if n['op'] in ['unknown','div','mod','distinct','implies','xor'] or (n['op']=='ite' and n['sort']=='Bool'):raise NotImplementedError('frozen official visitor unsupported operator')
        guard=r
        for k,c in enumerate(cs):
            cond=r
            if n['op'] in ('and','or'):
                if shared:
                    cond=guard;guard=z3.And(guard,nodes[c] if n['op']=='and' else z3.Not(nodes[c]));stats['prefix_argument_references']+=2
                else:
                    cond=z3.And(r,*[nodes[z] if n['op']=='and' else z3.Not(nodes[z]) for z in cs[:k]]);stats['prefix_argument_references']+=k+1
            elif n['op']=='ite' and k:cond=z3.And(r,nodes[cs[0]] if k==1 else z3.Not(nodes[cs[0]]))
            incoming[c].append(cond)
    return reach
