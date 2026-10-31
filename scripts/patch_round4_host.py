#!/usr/bin/env python3
from common import *
root=pathlib.Path(sys.argv[2]);stage=sys.argv[1];assert stage in ('M','S')
subprocess.run([sys.executable,ROOT/'scripts/patch_round3_host.py',root],check=True)
p=root/'HighDiv/makefile';s=p.read_text().replace(f'-I{ROOT}/include/round3',f'-I{ROOT}/include/round4');p.write_text(s)
p=root/'HighDiv/src/main/main.cpp';s=p.read_text().replace('mode=="observe_trace"','mode=="M_observe"||mode=="observe_trace"').replace('mode=="apply_trace"','mode=="M_apply"||mode=="apply_trace"');p.write_text(s)

if stage=='S':
 p=root/'HighDiv/makefile';s=p.read_text().replace(f'-I{ROOT}/include/round4',f'-I{ROOT}/include/round4/soft_reference -I{ROOT}/include/round4');p.write_text(s)
 p=root/'HighDiv/src/main/main.cpp';s=p.read_text();s=s.replace('if(mode=="a_off_test")', 'if(mode=="S_ref")argp->guidance_mode=3; else if(mode=="S_cov")argp->guidance_mode=4; else if(mode=="a_off_test")');p.write_text(s)
 p=root/'HighDiv/src/sampler/liasampler.cpp';s=p.read_text();begin=s.index('            if (num_samples != 0) {',s.index('void LiaSampler::hybrid_sampling'));end=s.index('            double prepare_start=',begin);old=s[begin:end]
 s=s[:begin]+"""            double inputs_start=session->elapsed();
            if(session->soft_reference()) {
                guided::QueryInputs inputs(c);
                inputs.reference=guided::collect_inherited_reference(m_ls,session->original_expressions,mt,fixed_var_pct,dist,num_samples!=0);
                // Only inputs.user_hard is passed to check. Currently the CLI has
                // no external assumptions. Never infer origin from syntax.
                assertions_vector=inputs.user_hard;
                session->register_inputs(inputs);
                if(session->guidance)session->guidance->charge("reference_collection_and_inputs_log_seconds",session->elapsed()-inputs_start);
            } else {
"""+old+'            }\n'+s[end:]
 s=s.replace('m_ls = subgoal.convert_model(m_ls);  // test','m_ls = subgoal.convert_model(m_ls);  // test\n            session->ls_reference_source(m_ls);');p.write_text(s)
