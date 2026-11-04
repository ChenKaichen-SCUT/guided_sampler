"""Freeze the approved runtime, provenance and compact evidence before V2 edits."""
import hashlib,json,pathlib,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1];WORKSPACE=ROOT.parent
dest=ROOT/'releases/V1';dest.mkdir(parents=True,exist_ok=False)
for name in ['bin','deps','include','kernel','src','tests','scripts','build','benchmarks','README.zh.md','REPORT_v5.zh.md','VERSION.json']:
    source=ROOT/name;target=dest/name
    if source.is_dir():shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__'))
    else:shutil.copyfile(source,target)
results=dest/'results';results.mkdir()
for p in (ROOT/'results').glob('v5_*.json'):shutil.copyfile(p,results/p.name)
shutil.copytree(ROOT/'results/verification',results/'verification')
for name in ['comparison_v5_t30','comparison_v5_n20','confirmation_v5_t60','pilot_v5_t10']:
    src=ROOT/'results'/name;out=results/name;out.mkdir()
    for p in src.glob('*.json'):shutil.copyfile(p,out/p.name)
    for run in src.glob('*/run.json'):
        folder=out/run.parent.name;folder.mkdir()
        for name2 in ['run.json','summary.json','metadata.json']:
            if (run.parent/name2).exists():shutil.copyfile(run.parent/name2,folder/name2)
manifest={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}
(dest/'FREEZE_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
# A standalone Git snapshot: no old working-tree changes and no large runtime
# dependencies. Full tested binaries remain in the local frozen release.
backup=WORKSPACE/'expression_soft_guidance_backup';backup.mkdir(exist_ok=False)
project=backup/'expression_soft_guidance';project.mkdir()
for name in ['include','kernel','src','tests','scripts','benchmarks','README.zh.md','REPORT_v5.zh.md','VERSION.json','FREEZE_SHA256.json','results']:
    source=dest/name;target=project/name
    if source.is_dir():shutil.copytree(source,target)
    else:shutil.copyfile(source,target)
(project/'build').mkdir()
for name in ['prepare.json','host_build.json','kernel_build.json','baseline_build.json']:
    shutil.copyfile(dest/'build'/name,project/'build'/name)
# Include the precise frozen source baseline and manifests, not merely a link.
up=json.loads((WORKSPACE/'guided_sampler/manifests/upstream.json').read_text())
for e in up['files']:
    source=WORKSPACE/'HighDiv-master'/e['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==e['sha256']
    target=backup/'HighDiv-master'/e['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for name in ['upstream.json','inputs.json']:
    target=backup/'guided_sampler/manifests'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(WORKSPACE/'guided_sampler/manifests'/name,target)
shutil.copytree(ROOT/'benchmarks',backup/'benchmarks')
print(json.dumps(dict(frozen=str(dest),files=len(manifest),backup=str(backup)),indent=2))
