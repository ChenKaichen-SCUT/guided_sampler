"""Check that reported binaries, implementation, and untouched upstream agree."""
import hashlib,json,pathlib,subprocess
from prepare import ROOT,WORKSPACE,sha,write
names=['comparison_v3_t30','comparison_v3_n20','comparison_v3_definitions_t30'];reports=[]
for name in names:
    folder=ROOT/'results'/name;manifest=json.loads((folder/'manifest.json').read_text());audit=json.loads((folder/'audit.json').read_text());assert audit['all_passed']
    for binary,digest in manifest['binaries'].items():assert sha(ROOT/'bin'/binary)==digest,(name,binary)
    for mode,digest in manifest['library_sha256'].items():assert sha(ROOT/'deps'/mode/'lib/libz3.so')==digest,(name,mode)
    count=0
    for section in ['include','kernel','src']:
        for p in (folder/'source'/section).rglob('*'):
            if p.is_file():assert sha(p)==sha(ROOT/p.relative_to(folder/'source'));count+=1
    reports.append(dict(name=name,runs=len(audit['runs']),models=sum(r['models'] for r in audit['runs']),matching_implementation_files=count))
upstream=json.loads((WORKSPACE/'guided_sampler/manifests/upstream.json').read_text())
for entry in upstream['files']:assert sha(WORKSPACE/'HighDiv-master'/entry['path'])==entry['sha256']
symbols={}
for mode in ['baseline','soft']:
    output=subprocess.check_output(['nm','-D','--defined-only',str(ROOT/'deps'/mode/'lib/libz3.so')],text=True)
    symbols[mode]=sorted(line.split()[-1] for line in output.splitlines() if 'Z3_expr_soft_' in line)
assert not symbols['baseline'];assert len(symbols['soft'])==3
metric=WORKSPACE/'HighDiv-master/HighDiv/my_scripts/calc_metric.py'
assert sha(metric)=='a51cdd069321cd32becf8eeb5e606cb71fbab16ae3e0231f68963eaadf493f04'
prefix=json.loads((ROOT/'results/comparison_v3_n20/prefix_equivalence.json').read_text());assert len(prefix)==32 and all(r['identical'] for r in prefix)
result=dict(passed=True,runs=reports,upstream_verified_files=len(upstream['files']),upstream_commit=upstream['commit'],guidance_exports=symbols,prefix_comparisons=len(prefix),audit_scripts={p.name:sha(p) for p in (ROOT/'scripts').glob('*.py')},implementation={str(p.relative_to(ROOT)):sha(p) for section in ['include','kernel','src'] for p in (ROOT/section).rglob('*') if p.is_file()})
write(ROOT/'results/final_verification.json',json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['audit_scripts','implementation']},indent=2))
