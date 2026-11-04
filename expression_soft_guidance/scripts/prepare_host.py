"""Common measurement host built from verified HighDiv, no older guidance code."""
import pathlib,shutil,hashlib,json
from prepare import ROOT,WORKSPACE,replace,write
source=WORKSPACE/'HighDiv-master/HighDiv/src';dest=ROOT/'src'
for p in source.rglob('*'):
    if p.is_file():
        q=dest/p.relative_to(source);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
p=dest/'sampler/liasampler.h';s=p.read_text();s=replace(s,'#define VERBOSE\n#define DEBUG','#include "session.hpp"')
s=replace(s,'    std::mt19937 mt;','    std::unique_ptr<esg::Session> expr_session;\n    std::string sample_source;\n    std::mt19937 mt;');write(p,s)
p=dest/'sampler/liasampler.cpp';s=p.read_text()
s=replace(s,'                res = cdcl_solver.check(assertions_vector);\n            } else {\n                res = cdcl_solver.check();\n            }','            }\n            res = expr_session->check(cdcl_solver, assertions_vector);')
s=replace(s,'                record_model(cdcl_m, samplesFile);','                sample_source="CDCL";\n                record_model(cdcl_m, samplesFile);')
s=replace(s,'            record_model(m_ls, samplesFile);','            sample_source="CCSS";\n            record_model(m_ls, samplesFile);')
s=replace(s,'                if (res == z3::unsat && assertions_vector.empty()) return;','                if (res == z3::unsat && assertions_vector.empty()) { expr_session->end_query(); return; }')
s=replace(s,'            // cdcl_solver.pop();','            expr_session->end_query();')
s=replace(s,'            // ls sampling','            if (!expr_session->ccss_enabled()) continue;\n            if (!expr_session->ccss_bounded() && maxTimeLimit-TimeElapsed()<1.0) break; // native integral timeout\n            // ls sampling')
s=replace(s,'            z3::check_result check_res = ls_solver.check();','            expr_session->begin_ccss(ls_solver);\n            z3::check_result check_res = ls_solver.check();\n            expr_session->checked_ccss(check_res);')
s=replace(s,'                std::cout << "Unsat or unknown case form LS!\\n";','                expr_session->end_ccss();\n                std::cout << "Unsat or unknown case form LS!\\n";')
s=replace(s,'            record_model(m_ls, samplesFile);','            record_model(m_ls, samplesFile);\n            expr_session->end_ccss();')
a=s.index('    // Evaluate in the model,',s.index('void LiaSampler::record_model'))
b=s.index('\n}\n',a)
s=s[:a]+'    if (expr_session->commit(model,sample_source)) ++num_samples;'+s[b:]
s=replace(s,'    parseSmtFile();','    parseSmtFile();\n    expr_session=std::make_unique<esg::Session>(original_formula,samplesFileDir,maxTimeLimit,time_sampling_start);')
s=replace(s,'    hybrid_sampling(samplesFile);','    hybrid_sampling(samplesFile);\n    expr_session->finish();')
write(p,s)
write(ROOT/'build/host_sources.json',json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2))
print('Host prepared from frozen HighDiv')
