"""Exact Reach + values for the frozen official short-circuit visitor."""
import z3,time
from independent import export,observations
class EncodingTimeout(Exception):pass

def reach_conditions(root,deadline=None):
    ast,nodes,vs=export(root);incoming=[[] for _ in nodes];incoming[0]=[z3.BoolVal(True,ctx=root.ctx)]
    post=[];seen=set()
    def visit(i):
        if i in seen:return
        seen.add(i)
        for c in ast['nodes'][i]['children']:visit(c)
        post.append(i)
    visit(0);reach=[None]*len(nodes)
    for i in reversed(post):
        if deadline and time.monotonic()>=deadline:raise EncodingTimeout()
        n=ast['nodes'][i];cs=n['children'];r=z3.Or(incoming[i]);reach[i]=r
        if n['op'] in ['unknown','div','mod','distinct','implies','xor'] or (n['op']=='ite' and n['sort']=='Bool'):raise NotImplementedError('frozen official visitor unsupported operator')
        for k,c in enumerate(cs):
            cond=r
            if n['op']=='and':cond=z3.And(r,*[nodes[z] for z in cs[:k]])
            elif n['op']=='or':cond=z3.And(r,*[z3.Not(nodes[z]) for z in cs[:k]])
            elif n['op']=='ite' and k:cond=z3.And(r,nodes[cs[0]] if k==1 else z3.Not(nodes[cs[0]]))
            incoming[c].append(cond)
    return ast,nodes,vs,reach

def bit_condition(expr,bit,value):
    if z3.is_bool(expr):return expr if value else z3.Not(expr)
    high=expr%(1<<(bit+1)) >= (1<<bit)
    return high if value else z3.Not(high)

def improvement_problem(root,models,position,deadline):
    ast,nodes,vs,reach=reach_conditions(root,deadline);history=set()
    for m in models[:position-1]:history |= observations(ast,m)[1]
    m=models[position-1];legal,seen=observations(ast,m);assert legal;protected=seen-history
    targets=[]
    for i,b,v in sorted(history):
        if (i,b,1-v) not in history and (i,b,1-v) not in seen:targets.append((i,b,1-v))
    if not targets:return None,{'status':'no_strict_covered_target','protected_count':len(protected),'target_count':0}
    clauses=[];by_node={}
    for i,b,v in sorted(protected):
        if time.monotonic()>=deadline:raise EncodingTimeout()
        by_node.setdefault(i,[]).append(bit_condition(nodes[i],b,v))
    for i,cs in by_node.items():clauses.append(z3.And(reach[i],*cs))
    extra=[]
    for i,b,v in targets:
        if time.monotonic()>=deadline:raise EncodingTimeout()
        extra.append(z3.And(reach[i],bit_condition(nodes[i],b,v)))
    return z3.And(root,*clauses,z3.Or(extra)),{'protected_count':len(protected),'target_count':len(targets),'actual_hard_conditions':[]}
