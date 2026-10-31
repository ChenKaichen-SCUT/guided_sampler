#!/usr/bin/env python3
from common import *
import difflib
stage=sys.argv[1];assert stage in ('M','S');BASE=ROOT/'results/round4';out=ROOT/'patches/round4'/stage;out.mkdir(exist_ok=False);source=ROOT/f'worktrees/round4_{stage}_release';files={}
for part in ['HighDiv','z3']:
 lines=[]
 for p in sorted((source/part/'src').rglob('*')):
  if not p.is_file() or p.suffix not in ('.cpp','.h','.hpp','.inc'):continue
  rel=p.relative_to(source);old=UP/rel
  if not old.exists() and p.name not in ['a_shared.hpp','a_state.h','a_context.inc','a_internal_view.h','z3_a_guidance.h','semantic_trace.h','semantic_context.inc','semantic_correspondence.hpp','preference_types.hpp','reference_evaluation.hpp','phase_evidence.hpp','declaration_identity.hpp']:continue
  if old.exists() and old.read_bytes()==p.read_bytes():continue
  san=ROOT/f'worktrees/round4_{stage}_sanitize'/rel;assert san.read_bytes()==p.read_bytes(),rel
  files[str(rel)]={'new_sha256':digest(p),'upstream_sha256':digest(old) if old.exists() else None};lines.extend(difflib.unified_diff(old.read_text().splitlines(True) if old.exists() else [],p.read_text().splitlines(True),fromfile='a/'+str(rel) if old.exists() else '/dev/null',tofile='b/'+str(rel)))
 (out/(part+'.patch')).write_text(''.join(lines))
write(out/'files.json',files)
validation={}
for v in ['release','sanitize']:
 lib=ROOT/f'deps/round4_{stage}_{v}/lib/libz3.so';checks=[read(p) for p in (BASE/'correctness').glob(stage+'_'+v+'_*/summary.json') if read(p).get('passed') and read(p)['library_sha256']==digest(lib)];assert checks,v;validation[v]=checks[-1];completion=read(BASE/f'correctness/completion_{stage}_{v}/summary.json');assert completion['passed'] and completion['library_sha256']==digest(lib);validation[v]['completion']=completion
header=ROOT/'include/round4' if stage=='M' else ROOT/'include/round4/soft_reference'
exclusive(ROOT/f'manifests/round4_{stage}_implementation.json',{'stage':stage,'binary_sha256':digest(source/'HighDiv/highdiv'),'library_sha256':digest(ROOT/f'deps/round4_{stage}_release/lib/libz3.so'),'validation':validation,'sources':files,'header_hashes':{str(p.relative_to(ROOT)):digest(p) for p in header.glob('*.hpp')},'short_plan_sha256':digest(ROOT/'manifests/round4_short_plan.json'),'config_sha256':digest(ROOT/'configs/round4.json'),'parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
(ROOT/'src/round4'/('mapping_a_context.inc' if stage=='M' else 'a_context.inc')).write_bytes((source/'z3/src/smt/a_context.inc').read_bytes())
print('Frozen R4',stage,len(files),'source files')
