#!/usr/bin/env python3
"""Separate D3 library; never changes the frozen D1 trees/prefixes."""
from common import *
import shutil
assert not (ROOT/'results/round3_semantics/micro/STARTED.json').exists(), 'D3 implementation is frozen after execution starts'
assert read(ROOT/'results/round3_semantics/oracle/summary.json')['calls']<=96
assert read(ROOT/'results/round3_semantics/analysis/chain_summary.json')['conditional_checkpoints']>0
base=ROOT/'worktrees/round3_release';tree=ROOT/'worktrees/round3_micro';prefix=ROOT/'deps/round3_micro'
def run(cmd,**kw):print('+',' '.join(map(str,cmd)),flush=True);subprocess.run(list(map(str,cmd)),check=True,**kw)
if not tree.exists():
 physical=pathlib.Path('/tmp/guided_sampler_round3_worktrees/micro');physical.mkdir(exist_ok=False);tree.symlink_to(physical,target_is_directory=True);run(['cp','-a','--reflink=auto',base/'z3',tree/'z3'])
z=tree/'z3/src';ctx=(base/'z3/src/smt/smt_context.cpp').read_text();a=(base/'z3/src/smt/a_context.inc').read_text()
ctx=ctx.replace('#include "model/semantic_trace.h"','#include "model/semantic_trace.h"\n#include <dirent.h>')
ctx=ctx.replace('#include "smt/a_context.inc"','#include "smt/semantic_intervention.inc"\n#include "smt/a_context.inc"')
needle='        apply_A_phase_hint(native_var,native_phase,is_pos);';assert needle in ctx
ctx=ctx.replace(needle,needle+'\n        if(d3::state().enabled&&d3::state().handoff){d3::state().handoff=false;if(get_assignment(var)==l_undef)m_case_split_queue->unassign_var_eh(var);return true;}')
needle='bool context::apply_A_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase) {';assert needle in a;a=a.replace(needle,needle+'\n'+(ROOT/'src/round3/semantic_intervention_phase.inc').read_text())
for p,s in [(z/'smt/smt_context.cpp',ctx),(z/'smt/a_context.inc',a)]:
 if p.read_text()!=s:p.write_text(s)
helper=ROOT/'src/round3/semantic_intervention.inc';dest=z/'smt/semantic_intervention.inc'
if not dest.exists() or helper.read_bytes()!=dest.read_bytes():shutil.copyfile(helper,dest)
prefix.mkdir(exist_ok=True);env=os.environ.copy();env['CXXFLAGS']='-O3 -DNDEBUG'
if not (tree/'z3/build/.round3_micro_configured').exists():
 run([sys.executable,'scripts/mk_make.py',f'--prefix={prefix}'],cwd=tree/'z3',env=env);(tree/'z3/build/.round3_micro_configured').touch()
run(['make','-C',tree/'z3/build','-j','12'],env=env);run(['make','-C',tree/'z3/build','install'],env=env)
run(['g++','-std=c++20','-O3','-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),ROOT/'tests/round3/micro.cpp','-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',ROOT/'build/round3-micro'])
