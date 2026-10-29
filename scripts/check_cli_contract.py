#!/usr/bin/env python3
import os,subprocess
from common import *
def main():
    out=ROOT/'results/correctness/cli';out.mkdir(exist_ok=False);formula=out/'input.smt2';formula.write_text('(declare-const x Int)(assert (or (= x 0) (= x 10)))')
    results=[]
    for variant in ['baseline','guided']:
        for name,args,want in [('zero_count',['-n','0','-t','2'],0),('zero_time',['--unlimited-samples','-t','0'],0),('unlimited',['-n','0','--unlimited-samples','-t','2'],None),('one_model',['-n','1','-t','2'],1)]:
            d=out/(variant+'-'+name);d.mkdir();env=os.environ.copy();env['HIGHDIV_TEST_MAX_QUERIES']='4';cmd=[str(ROOT/f'worktrees/{variant}/HighDiv/highdiv'),'-i',str(formula),'-o',str(d),'-s','0','--guidance','off']+args
            p=subprocess.run(cmd,cwd=d,env=env,capture_output=True,text=True,timeout=10);(d/'stdout.log').write_text(p.stdout);(d/'stderr.log').write_text(p.stderr);assert p.returncode==0,p.stderr
            s=read(d/'summary.json');assert s['formal_count']==want if want is not None else s['formal_count']>0
            if name=='one_model':assert s['queries']==1
            results.append({'variant':variant,'case':name,'summary':s})
    write(out/'summary.json',{'passed':True,'tests':results});print('CLI count, unlimited, zero-time and immediate count stop passed')
if __name__=='__main__':main()
