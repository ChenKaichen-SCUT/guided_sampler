"""Reconcile final implementation, binary provenance, semantic checks and audits."""
import json,subprocess
from prepare import ROOT,WORKSPACE,sha,write
names=['comparison_v4_t30','comparison_v4_n20'];reports=[]
for name in names:
    folder=ROOT/'results'/name;manifest=json.loads((folder/'manifest.json').read_text());audit=json.loads((folder/'audit.json').read_text());assert audit['all_passed']
    exclusions=json.loads((folder/'impossible_audit.json').read_text());assert exclusions['all_passed']
    for binary,digest in manifest['binaries'].items():assert sha(ROOT/'bin'/binary)==digest,(name,binary)
    for mode,digest in manifest['library_sha256'].items():assert sha(ROOT/'deps'/mode/'lib/libz3.so')==digest,(name,mode)
    count=0
    for section in ['include','kernel','src','tests']:
        for p in (folder/'source'/section).rglob('*'):
            if p.is_file():assert sha(p)==sha(ROOT/p.relative_to(folder/'source'));count+=1
    reports.append(dict(name=name,runs=len(audit['runs']),models=sum(r['models'] for r in audit['runs']),matching_implementation_files=count,exclusion_certificates=sum(b['unique_proofs'] for b in exclusions['benches'])))
upstream=json.loads((WORKSPACE/'guided_sampler/manifests/upstream.json').read_text())
for e in upstream['files']:assert sha(WORKSPACE/'HighDiv-master'/e['path'])==e['sha256']
symbols={}
for mode in ['baseline','soft']:
    out=subprocess.check_output(['nm','-D','--defined-only',str(ROOT/'deps'/mode/'lib/libz3.so')],text=True)
    symbols[mode]=sorted(line.split()[-1] for line in out.splitlines() if 'Z3_expr_soft_' in line)
assert not symbols['baseline'] and len(symbols['soft'])==3
prefix=json.loads((ROOT/'results/comparison_v4_n20/prefix_equivalence.json').read_text());assert len(prefix)==48 and all(r['identical'] for r in prefix)
units={name:json.loads((ROOT/'results/verification'/(name+'.json')).read_text()) for name in ['pattern_test','kernel_test','impossible_test']};assert all(r['passed'] for r in units.values())
result=dict(passed=True,runs=reports,upstream_verified_files=len(upstream['files']),upstream_commit=upstream['commit'],guidance_exports=symbols,prefix_comparisons=len(prefix),unit_checks=units,implementation={str(p.relative_to(ROOT)):sha(p) for section in ['include','kernel','src','tests'] for p in (ROOT/section).rglob('*') if p.is_file()})
write(ROOT/'results/v4_final_verification.json',json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['unit_checks','implementation']},indent=2))
