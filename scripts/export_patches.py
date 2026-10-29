#!/usr/bin/env python3
import difflib,pathlib,subprocess
from common import *

def patch(name,pairs):
    chunks=[]
    for relative,a,b in pairs:
        old=a.read_text().splitlines(True) if a.exists() else [];new=b.read_text().splitlines(True) if b.exists() else []
        if old!=new:chunks.extend(difflib.unified_diff(old,new,fromfile='a/'+relative,tofile='b/'+relative))
    (ROOT/'patches'/name).write_text(''.join(chunks))
def main():
    baseline=ROOT/'worktrees/baseline';guided=ROOT/'worktrees/guided'
    files=['HighDiv/src/main/main.cpp','HighDiv/src/sampler/liasampler.cpp','HighDiv/src/sampler/liasampler.h']
    patch('00_highdiv_common_measurement.patch',[(p,UP/p,baseline/p) for p in files])
    patch('01_common_diagnostic_trace.patch',[(r,UP/r,baseline/r) for r in ['z3/src/smt/smt_context.cpp','z3/src/solver/combined_solver.cpp']])
    files=['z3/src/solver/solver.h','z3/src/solver/combined_solver.cpp','z3/src/smt/smt_context.h','z3/src/smt/smt_context.cpp','z3/src/smt/smt_solver.cpp','z3/src/api/api_solver.cpp']
    patch('20_z3_guidance.patch',[(p,baseline/p,guided/p) for p in files])
    print('Exported patches; new headers/inc files remain first-class project sources.')
if __name__=='__main__':main()
