#!/usr/bin/env python3
"""Format, AST denominator and route integration only; no performance selection."""
import concurrent.futures,os
from common import *
def main():
    out=ROOT/'results/correctness/input_preflight';out.mkdir(exist_ok=False)
    binary=ROOT/'build/inspect_ast';prefix=ROOT/'deps/guided'
    cmd=['g++','-O3','-std=c++20','-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(ROOT/'tests/inspect_ast.cpp'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(binary)]
    subprocess.run(cmd,check=True)
    inputs=read(ROOT/'manifests/input_ast.json');p=subprocess.run([binary]+[ROOT.parent/e['path'] for e in inputs],capture_output=True,text=True,check=True)
    rows=[json.loads(l) for l in p.stdout.splitlines()]
    for e,r in zip(inputs,rows):assert e['metric_nodes']==r['nodes'] and e['total']==r['total'] and e['variables']==r['variables'],(e,r)
    write(out/'ast_comparison.json',{'passed':True,'inputs':rows})
    def one(item):
        i,e=item;d=out/f'{i:02d}';d.mkdir();env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='3';env['HIGHDIV_ROUTE_LOG']=str(d/'routes.jsonl')
        cmd=[str(ROOT/'worktrees/guided/HighDiv/highdiv'),'-i',str(ROOT.parent/e['path']),'-o',str(d),'--unlimited-samples','-t','3','-s','0','--guidance','a_plus_b']
        p=subprocess.run(cmd,capture_output=True,text=True,env=env,cwd=d,timeout=70);(d/'stdout.log').write_text(p.stdout);(d/'stderr.log').write_text(p.stderr)
        assert p.returncode==0,p.stderr
        routes=[json.loads(l) for l in (d/'routes.jsonl').read_text().splitlines()] if (d/'routes.jsonl').exists() else []
        assert len({r['solver'] for r in routes})<=1
        return {'input':e['path'],'exit_code':p.returncode,'route_receipts':len(routes),'purpose':'AST/format/backend integration only; not a performance gate'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:checks=list(pool.map(one,enumerate(inputs)))
    write(out/'summary.json',{'passed':True,'checks':checks,'algorithm_parameters_changed':False});print('Eight AST denominators, original-variable projections and route integration checked')
if __name__=='__main__':main()
