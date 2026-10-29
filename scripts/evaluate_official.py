#!/usr/bin/env python3
import argparse,subprocess,time
from common import *

def evaluate(run,formula):
    run=pathlib.Path(run)
    cmd=[str(python()),str(metric_path()),'-f',str(formula),'-s',str(run/'samples.formal'),'-m','wire_coverage']
    with open(run/'wire_coverage.stdout','x') as out,open(run/'wire_coverage.stderr','x') as err:
        start=time.monotonic();p=subprocess.run(cmd,stdout=out,stderr=err)
    write(run/'wire_coverage.command.json',{'command':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-start,'metric_sha256':digest(metric_path()),'input_sha256':digest(formula),'samples_sha256':digest(run/'samples.formal')})
    exact=[str(python()),str(ROOT/'scripts/evaluate_exact.py'),'-f',str(formula),'-s',str(run/'samples.formal'),'--receipts',str(run/'formal_receipts.jsonl'),'-o',str(run/'exact.json')]
    with open(run/'exact.stdout','x') as out,open(run/'exact.stderr','x') as err:q=subprocess.run(exact,stdout=out,stderr=err)
    return {'official_exit':p.returncode,'exact_exit':q.returncode}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('formula');a=p.parse_args();print(evaluate(a.run,a.formula))
