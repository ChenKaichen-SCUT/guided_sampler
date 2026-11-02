from common6 import *
import difflib
assert not (BASE/'G1_STARTED.json').exists();sources={};validation={};patch=[]
out=ROOT/'patches/round6';assert not out.exists()
for v in ['release','sanitize']:
    tree=ROOT/f'worktrees/round6_{v}';old=ROOT/f'worktrees/round5_{v}';inherit=read(BASE/'correctness'/f'{v}_{"02" if v=="release" else "01"}/summary.json');guard=read(BASE/'correctness'/f'guard_{v}_{"03" if v=="release" else "02"}/summary.json');exception=read(BASE/'correctness'/f'exception_{v}_01/summary.json');assert inherit['passed'] and guard['passed'] and exception['passed']
    host=tree/'HighDiv/highdiv';library=ROOT/f'deps/round6_{v}/lib/libz3.so';replay=ROOT/f'build/round6-ccss-replay-{v}'
    assert read(BASE/'correctness'/f'disabled_{v}_verified.json')['passed']
    assert digest(host)==inherit['binary_sha256']==guard['host_sha256'];assert digest(library)==inherit['library_sha256']==guard['library_sha256'];assert digest(replay)==inherit['replay_sha256']==guard['replay_sha256']==exception['replay_sha256']
    ldd=subprocess.check_output(['ldd',str(host)],text=True);assert str(ROOT/f'deps/round6_{v}/lib/libz3.so') in ldd
    modified={}
    paths=[p for part in ['z3/src','HighDiv/src','round6_include'] for p in (tree/part).rglob('*') if p.is_file() and p.suffix not in ['.o','.a','.so','.pyc']]+[tree/'HighDiv/makefile']
    for p in paths:
        rel=str(p.relative_to(tree));before=old/rel.replace('round6_include/','round5_include/');data=p.read_bytes();previous=before.read_bytes() if before.exists() else b''
        if data==previous:continue
        normalized=data.replace(str(tree).encode(),b'@ROUND6_TREE@');modified[rel]={'sha256':digest(p),'normalized_sha256':hashlib.sha256(normalized).hexdigest(),'base_relative':str(before.relative_to(old)),'base_sha256':digest(before) if before.exists() else None}
        if v=='release':
            lines=difflib.unified_diff(previous.decode().splitlines(True),data.decode().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel);patch.extend(lines)
    sources[v]=modified
    validation[v]={'passed':True,'inherited_checks':len(inherit['checks']),'guard_checks':len(guard['checks']),'generic_exception':exception,'binary_sha256':digest(host),'library_sha256':digest(library),'replay_sha256':digest(replay),'sampler_archive_sha256':digest(tree/'z3/build/sampler/sampler.a'),'build_config_sha256':digest(tree/'z3/build/config.mk'),'ldd':ldd,'sole_leak_suppression_sha256':digest(ROOT/'tests/lsan-upstream.supp')}
assert set(sources['release'])==set(sources['sanitize'])
for p,r in sources['release'].items():assert r['normalized_sha256']==sources['sanitize'][p]['normalized_sha256'],p
out.mkdir();(out/'round5_to_round6.patch').write_text(''.join(patch));write(out/'files.json',sources)
code={str(p.relative_to(ROOT)):digest(p) for part in ['include/round6','src/round6'] for p in (ROOT/part).glob('*') if p.is_file()}
for rel in ['scripts/round6/patch_sources.py','scripts/round6/run_guard_replay.py','scripts/round6/run_short.py']:code[rel]=digest(ROOT/rel)
exclusive(ROOT/'manifests/round6_implementation.json',{'base_commit':'ae85956068154207a442c0e2c8387c573dc32411','parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'config_sha256':digest(ROOT/'configs/round6_guard.json'),'guide_sha256':digest(ROOT/'docs/round6/execution_guide.zh.md'),'sources':sources,'code_files':code,'validation':validation,'patch_sha256':digest(out/'round5_to_round6.patch'),'guard_limit':65536,'G1_and_G2_not_started':True});print('Frozen Round6 production guard:',len(sources['release']),'modified files per build')
