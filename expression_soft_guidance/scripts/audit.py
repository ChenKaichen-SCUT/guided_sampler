"""Post-run audit with unchanged upstream metric and unmodified baseline Z3."""
import argparse,builtins,hashlib,importlib.util,json,pathlib,sys,time
from prepare import ROOT,WORKSPACE,write
base=WORKSPACE/'guided_sampler/deps/baseline'
sys.path.insert(0,str(base/'lib/python3.10/site-packages'));builtins.Z3_LIB_DIRS=[str(base/'lib')]
import z3
spec=importlib.util.spec_from_file_location('official_metric',WORKSPACE/'HighDiv-master/HighDiv/my_scripts/calc_metric.py');metric=importlib.util.module_from_spec(spec);spec.loader.exec_module(metric)
ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('--bench');ap.add_argument('--output',default='audit.json');args=ap.parse_args();folder=ROOT/'results'/args.name
class AuditStatistics(metric.WireCoverageStatistics):
    def __init__(self):super().__init__();self.visits={}
    def evaluate_node(self,node,value):self.visits[node]=value;super().evaluate_node(node,value)
reports=[];started=time.monotonic()
for runpath in sorted(folder.glob('*/run.json')):
    run=json.loads(runpath.read_text());directory=runpath.parent
    if args.bench and run['bench']!=args.bench:continue
    stats=AuditStatistics();evaluator=metric.ManualSatisfiesMetric(pathlib.Path(run['input']).read_text(),stats)
    root=z3.And(evaluator._solver.assertions());variables={};todo=[root];seen=set();nodes=[]
    while todo:
        e=todo.pop()
        if e.get_id() in seen:continue
        seen.add(e.get_id())
        nodes.append(e)
        if z3.is_const(e) and e.decl().kind()==z3.Z3_OP_UNINTERPRETED:variables[str(e.decl().name())]=e
        todo.extend(reversed(e.children()))
    def count():return sum(int(bool(a and b)) if kind=='bool' else (a&b).bit_count() for a,b,kind in stats._storage.values())
    total=sum(1 if kind=='bool' else 64 for a,b,kind in stats._storage.values());models=0;keys=set();checkpoints={};last=0.;source_counts={};errors=[]
    time_checkpoints={};cutoffs=[t for t in [1,5,10,20,29,30,60,120] if t<=run['limit']];source_gains={}
    queryrows=[json.loads(s) for s in (directory/'queries.jsonl').read_text().splitlines()] if (directory/'queries.jsonl').exists() else []
    byquery={r['query']:r for r in queryrows};events=iter(queryrows);event=next(events,None);formal_cdcl=set();history_checks=0;goal_checks=0
    def check_history(event):
        global history_checks
        if 'target' not in event:return
        t=event['target'];node=nodes[t['node']];one,zero,kind=stats._storage[node.get_id()];mask=t['mask'];width=1 if kind=='bool' else (1<<64)-1
        if mask&~((int(one)^int(zero))&width):errors.append('target bit was not single-side observed before query')
        if t['desired']!=(int(zero)&~int(one)&mask):errors.append('target direction was not opposite of observed side')
        history_checks+=1
    receipts=directory/'receipts.jsonl';formal_lines=[]
    if receipts.exists():
        for line in receipts.read_text().splitlines():
            row=json.loads(line)
            if not row.get('accepted'):continue
            before=count()
            for t in cutoffs:
                if row['time']>t and str(t) not in time_checkpoints:time_checkpoints[str(t)]=before
            while event and event['start']<=row['time']:check_history(event);event=next(events,None)
            assignment={k:int(v) for k,v in row['assignment'].items()};sample=list(assignment.items())
            if set(assignment)!=set(variables):errors.append('projected variable set')
            key=tuple(sorted(sample))
            if key in keys:errors.append('duplicate assignment')
            keys.add(key)
            if row['time']>run['limit']:errors.append('late receipt')
            stats.visits.clear()
            if not evaluator.count_sample(sample):errors.append('official evaluator illegal model')
            substitutions=[(v,z3.BoolVal(bool(assignment[k]),ctx=v.ctx) if z3.is_bool(v) else z3.IntVal(assignment[k],ctx=v.ctx)) for k,v in variables.items()]
            if not z3.is_true(z3.simplify(z3.substitute(root,*substitutions))):errors.append('unmodified Z3 ground substitution rejected model')
            covered=count()
            source_gains[row['source']]=source_gains.get(row['source'],0)+covered-before
            if run['mode'] not in ['baseline','native'] and row['covered']!=covered:errors.append('online/offline coverage mismatch')
            if row['source']=='CDCL':
                formal_cdcl.add(row['query']);q=byquery[row['query']]
                if 'target' in q:
                    original_id=nodes[q['target']['node']].get_id();visited=original_id in stats.visits;value=int(stats.visits.get(original_id,0));hits_in_model=0
                    for bit in q.get('formal_target_observations',[]):
                        hit=visited and ((value>>bit['bit'])&1)==bit['desired']
                        if hit!=bit['solver_goal'] or visited!=bit['visited']:errors.append('official original-bit/Reach differs from solver target')
                        hits_in_model+=hit;goal_checks+=1
                    if hits_in_model>row['gain']:errors.append('target hit did not produce matching new coverage')
            models+=1;source_counts[row['source']]=source_counts.get(row['source'],0)+1;last=row['time']
            formal_lines.append(str(models-1)+': '+''.join(k+':'+str(v)+';' for k,v in sorted(sample))+'\n')
            if models in [1,2,5,10,20,50,100,200,500,1000]:checkpoints[models]=covered
    while event:check_history(event);event=next(events,None)
    for t in cutoffs:time_checkpoints.setdefault(str(t),count())
    write(directory/'accepted.samples',''.join(formal_lines))
    targets=hits=chosen=prepared=auxskip=unprepared=0;preparation=checkwall=0.;target_queries=0
    for row in queryrows:
        preparation+=row.get('preparation_wall',0);checkwall+=row.get('check_complete',row['start'])-row['start']-row.get('preparation_wall',0)
        if 'target' in row:target_queries+=1
        k=row.get('kernel',{});chosen+=k.get('chosen',0);prepared+=k.get('prepared',0);auxskip+=k.get('auxiliary_exchange_skips',0)
        if run['mode'].startswith('soft') and 'target' in row and row.get('result')=='sat' and not k.get('prepared',0):unprepared+=1
        if k.get('mapping_failures',0):errors.append('unsupported goal model-converter transport')
        for bit in row.get('formal_target_observations',[]):
            if row['query'] not in formal_cdcl:continue
            targets+=1;hits+=bit['value_hit']
            if bit['solver_goal']!=bit['value_hit']:errors.append('goal/expression mismatch')
    if run.get('summary',{}).get('models')!=models:errors.append('summary/receipt count mismatch')
    report={k:run[k] for k in ['bench','mode','seed','exit_code','outer_wall','limit']};report.update(models=models,covered=count(),total=total,coverage=count()/total,last_sample=last,sources=source_counts,source_gains=source_gains,time_checkpoints=time_checkpoints,checkpoints=checkpoints,targets_observed=targets,target_hits=hits,target_queries=target_queries,preferred_decisions=chosen,prepared_goals=prepared,excluded_auxiliaries=auxskip,preparation_wall=preparation,cdcl_wall=checkwall,errors=sorted(set(errors)))
    report.update(history_checks=history_checks,independent_goal_checks=goal_checks,sampling_wall=run.get('summary',{}).get('wall'),unprepared_sat_queries=unprepared,filter=run.get('summary',{}).get('filter',{}))
    write(directory/'audit.json',json.dumps(report,indent=2)+'\n');reports.append(report)
    print(json.dumps({k:report[k] for k in ['bench','mode','seed','models','covered','target_hits','preferred_decisions','errors']}),flush=True)
write(folder/args.output,json.dumps({'runs':reports,'all_passed':all(not r['errors'] and not r['exit_code'] for r in reports),'wall':time.monotonic()-started,'oracle_library_sha256':hashlib.sha256((base/'lib/libz3.so').read_bytes()).hexdigest()},indent=2)+'\n')
if any(r['errors'] or r['exit_code'] for r in reports):raise SystemExit(1)
