from common5 import *
import difflib
assert not (BASE/'W_STARTED.json').exists();sources={};patches=ROOT/'patches/round5';patches.mkdir(exist_ok=False)
tree=ROOT/'worktrees/round5_release';old=ROOT/'worktrees/round4_S_release'
lines=[]
for part in ['z3/src','HighDiv/src','round5_include']:
    for p in sorted((tree/part).rglob('*')):
        if not p.is_file() or p.suffix not in ['.cpp','.h','.hpp','.inc']:continue
        rel=p.relative_to(tree);base=(ROOT/'include/round4/soft_reference'/p.name) if part=='round5_include' else old/rel
        if base.exists() and p.read_bytes()==base.read_bytes():continue
        assert p.read_bytes()==(ROOT/'worktrees/round5_sanitize'/rel).read_bytes(),rel
        sources[str(rel)]={'sha256':digest(p),'base_sha256':digest(base) if base.exists() else None}
        lines+=list(difflib.unified_diff(base.read_text().splitlines(True) if base.exists() else [],p.read_text().splitlines(True),fromfile='a/'+str(rel) if base.exists() else '/dev/null',tofile='b/'+str(rel)))
(patches/'round4_to_round5.patch').write_text(''.join(lines));write(patches/'files.json',sources)
validation={}
for v in ['release','sanitize']:
    checks=[read(p) for p in sorted((BASE/'correctness').glob(v+'_*/summary.json')) if read(p).get('passed')];assert checks,v
    c=checks[-1];assert c['library_sha256']==digest(ROOT/f'deps/round5_{v}/lib/libz3.so');assert c['binary_sha256']==digest(ROOT/f'worktrees/round5_{v}/HighDiv/highdiv')
    edges=[read(p) for p in sorted((BASE/'correctness').glob('exchange_edges_'+v+'_*/summary.json')) if read(p).get('passed')];assert edges and edges[-1]['library_sha256']==c['library_sha256'] and edges[-1]['replay_sha256']==c['replay_sha256'];c['exchange_edges']=edges[-1]
    c['ldd']=subprocess.check_output(['ldd',ROOT/f'worktrees/round5_{v}/HighDiv/highdiv'],text=True);assert str(ROOT/f'deps/round5_{v}/lib/libz3.so') in c['ldd'];c['config_sha256']=digest(ROOT/f'worktrees/round5_{v}/z3/build/config.mk');c['sampler_archive_sha256']=digest(ROOT/f'worktrees/round5_{v}/z3/build/sampler/sampler.a');validation[v]=c
exclusive(ROOT/'manifests/round5_implementation.json',{'sources':sources,'validation':validation,'config_sha256':digest(ROOT/'configs/round5_diagnosis.json'),'parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sampler_changes':'SupportOnly is the sole scoring ablation; R5 instrumentation only elsewhere','code_files':{str(p.relative_to(ROOT)):digest(p) for directory in ['include/round5','src/round5'] for p in (ROOT/directory).rglob('*') if p.is_file()}})
print('R5 implementation frozen',len(sources))
