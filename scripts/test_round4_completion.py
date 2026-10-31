#!/usr/bin/env python3
from common import *
from finalize_samples import finalize
stage=sys.argv[1]
for variant in (sys.argv[2:] or ['release','sanitize']):
 assert variant in ['release','sanitize']
 prefix=ROOT/('deps/round4_'+stage+'_'+variant);out=ROOT/('results/round4/correctness/completion_'+stage+'_'+variant);out.mkdir(exist_ok=False);binary=ROOT/('build/round4-completion-'+stage+'_'+variant);cmd=['g++','-std=c++20','-O1','-g','-I'+str(ROOT/'include/round4'),'-I'+str(ROOT/'include/round2'),'-I'+str(ROOT/'include'),'-I'+str(prefix/'include'),str(ROOT/'tests/round3/completion.cpp'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lz3','-o',str(binary)]
 if variant=='sanitize':cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.stdout').write_text(r.stdout);(out/'compile.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr
 env=os.environ.copy();env.update(GUIDED_SEMANTIC_TRACE_DIR=str(out),GUIDED_SEMANTIC_RUN_ID='completion_'+variant)
 if variant=='sanitize':env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LSAN_OPTIONS='suppressions='+str(ROOT/'tests/lsan-upstream.supp')+':print_suppressions=1')
 r=subprocess.run([binary,out],cwd=out,env=env,capture_output=True,text=True);(out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr;finalize(out,10,1);layers=[json.loads(l) for l in (out/'semantic_host.jsonl').read_text().splitlines()];raw=next(x for x in layers if x['kind']=='M_original');assert all(not v['defined'] for v in raw['M_outer_variables']);assert len([x for x in layers if x['kind']=='M_formal'])==1;write(out/'summary.json',{'passed':True,'original_source_model_unchanged':True,'raw_undef_explicit':True,'formal_projection_completed':True,'solver_calls':0,'library_sha256':digest(prefix/'lib/libz3.so'),'command':cmd});print(variant,'completion passed',flush=True)
