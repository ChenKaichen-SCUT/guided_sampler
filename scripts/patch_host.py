#!/usr/bin/env python3
import pathlib,sys,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1];tree=pathlib.Path(sys.argv[1]);variant=sys.argv[2]
host=tree/'HighDiv'
# Idempotent: regenerate host ONLY from the verified upstream, then apply common
# measurement edits, and the single guided feature compile switch.
for rel in ['src/main/main.cpp','src/sampler/liasampler.cpp','src/sampler/liasampler.h','makefile']:
    shutil.copy(ROOT.parent/'HighDiv-master/HighDiv'/rel,host/rel)
def edit(p,a,b,n=1):
    f=host/p;s=f.read_text();assert s.count(a)>=n,(p,a);f.write_text(s.replace(a,b,n))
edit('src/sampler/liasampler.h','#include "sampler.h"','#include "sampler.h"\n#include "session.hpp"')
edit('src/sampler/liasampler.h','#define VERBOSE','// Routine progress stays in structured session logs.')
edit('src/sampler/liasampler.h','    double TimeElapsed();','    std::unique_ptr<guided::Session> session;\n    bool unlimited=false; unsigned guidance_mode=0;\n    double TimeElapsed();')
edit('src/sampler/liasampler.h','    z3::tactic mk_preamble_tactic','    void configure(bool u,unsigned m){unlimited=u;guidance_mode=m;}\n    z3::tactic mk_preamble_tactic')
edit('src/sampler/liasampler.cpp','    std::chrono::steady_clock::time_point finish =','    if(session)return session->elapsed();\n    std::chrono::steady_clock::time_point finish =')
edit('src/sampler/liasampler.cpp','if (maxNumSamples == 0 || TimeElapsed() >= maxTimeLimit) return;','if (session->stop()) return;')
edit('src/sampler/liasampler.cpp','while (num_samples < maxNumSamples && TimeElapsed() < maxTimeLimit)','while (!session->stop())')
edit('src/sampler/liasampler.cpp','if (TimeElapsed() >= maxTimeLimit) break;','if (session->stop()) break;')
edit('src/sampler/liasampler.cpp','''            cdcl_solver.set("timeout", static_cast<unsigned>(std::max(1.0,
                std::min(50000.0, (maxTimeLimit - TimeElapsed()) * 1000.0))));''','')
edit('src/sampler/liasampler.cpp','if (m_ls[j].is_const() &&','if (session->original_decls.count(m_ls[j].id()) && m_ls[j].is_const() &&')
edit('src/sampler/liasampler.cpp','''                res = cdcl_solver.check(assertions_vector);
            } else {
                res = cdcl_solver.check();
            }''','''            }
            double prepare_start=session->elapsed();
            if(session->guidance)session->guidance->prepare(cdcl_solver,session->query+1);
            session->prepare_seconds=session->elapsed()-prepare_start;
            if(session->stop())break;
            unsigned grant=static_cast<unsigned>(std::max(1.0,std::min(50000.0,session->remaining()*1000.0)));
            cdcl_solver.set("timeout",grant);
            session->begin_query("CDCL",assertions_vector,50000,grant);
            // Preserve native empty vs nonempty assumptions calls and RNG order.
            res = num_samples ? cdcl_solver.check(assertions_vector) : cdcl_solver.check();
            double check_end=session->elapsed();
            auto guidance_stats=session->guidance?session->guidance->end_check(cdcl_solver):guided::Json::object();
            session->end_query(cdcl_solver,res,guidance_stats,check_end);''')
edit('src/sampler/liasampler.cpp','if (num_samples < maxNumSamples && TimeElapsed() < maxTimeLimit)','if (!session->stop() && session->remaining() >= 1.0)')
edit('src/sampler/liasampler.cpp','''            ls_solver.set("ls_timeout", static_cast<unsigned>(
                std::max(0.0, std::min(60.0, maxTimeLimit - TimeElapsed()))));
            z3::check_result check_res = ls_solver.check();''','''            unsigned grant=static_cast<unsigned>(std::min(60.0,session->remaining()));
            ls_solver.set("ls_timeout",grant);
            ls_solver.set("timeout",static_cast<unsigned>(std::max(1.0,session->remaining()*1000.0)));
            z3::expr_vector empty(c);
            session->prepare_seconds=0;
            session->begin_query("CCSS",empty,60,grant);
            z3::check_result check_res = ls_solver.check();
            session->end_query(ls_solver,check_res);''')
edit('src/sampler/liasampler.cpp','if (TimeElapsed() > maxTimeLimit || num_samples >= maxNumSamples)','if (session->stop())')
f=host/'src/sampler/liasampler.cpp';s=f.read_text();a=s.index('void LiaSampler::record_model(');b=s.index('unsigned LiaSampler::gen_random_seed()',a)
s=s[:a]+'''void LiaSampler::record_model(z3::model model, std::ofstream& samplesFile) {
    if(session->commit(model,original_formula,samplesFile)) {
        num_samples=session->formal;
        if(session->source=="CDCL")++num_cdcl_samples;else ++num_ls_samples;
    }
}
void LiaSampler::print_unique_sample(std::ofstream&) {}

'''+s[b:]
a=s.index('void LiaSampler::sampling()');s=s[:a]+'''void LiaSampler::sampling() {
    session=std::make_unique<guided::Session>(c,maxTimeLimit,
        unlimited?std::nullopt:std::optional<size_t>(maxNumSamples),samplesFileDir);
    try {
        parseSmtFile();
        session->load(original_formula,guidance_mode);
        std::ofstream samplesFile(samplesFileDir+"/samples.raw");
        if(!samplesFile)throw std::runtime_error("Cannot create samples.raw");
        hybrid_sampling(samplesFile);
        samplesFile.close();
        session->finish();
        print_statistic();
    } catch(z3::exception const&) {
        if(session->elapsed()>=maxTimeLimit||guided::interrupted)session->status="deadline";
        else session->status="error";
        session->finish();
        if(session->status=="error")throw;
    } catch(...) {session->status="error";session->finish();throw;}
}
} // namespace sampler
''';f.write_text(s)
edit('src/main/main.cpp','#include "../sampler/liasampler.h"','#include "../sampler/liasampler.h"\n#include <filesystem>')
edit('src/main/main.cpp','std::string outputDir{getcwd(NULL, 0)};','std::string outputDir{std::filesystem::current_path().string()};\n    bool unlimited=false; unsigned guidance_mode=0;')
edit('src/main/main.cpp','        if (arg == "-h") {','''        if (arg == "--unlimited-samples") { argp->unlimited=true;
        } else if (arg == "--guidance" && i+1<argc) {
            std::string mode=argv[++i];
            if(mode=="off")argp->guidance_mode=0;
#ifdef GUIDED_BUILD
            else if(mode=="a_only")argp->guidance_mode=1;
            else if(mode=="b_only")argp->guidance_mode=2;
            else if(mode=="a_plus_b")argp->guidance_mode=3;
#endif
            else {std::cerr<<"Unsupported guidance mode\\n";return false;}
        } else if (arg == "-h") {''')
edit('src/main/main.cpp','    try {\n        mySampler.sampling();','    mySampler.configure(arg.unlimited,arg.guidance_mode);\n    try {\n        mySampler.sampling();')
edit('makefile','CPPFLAGS += -I$(Z3_PREFIX)/include',f'CPPFLAGS += -I$(Z3_PREFIX)/include -I{ROOT}/include'+(' -DGUIDED_BUILD' if variant!='baseline' else ''))
# Link sanitizer flags, needed for the host as well as libz3.
edit('makefile','$(CXX) $(OBJECTS) $(LDFLAGS)','$(CXX) $(CXXFLAGS) $(OBJECTS) $(LDFLAGS)')
print('Prepared',variant,'host (common measurement + optional metadata bridge)')

edit('src/sampler/liasampler.cpp','                z3::model cdcl_m = cdcl_solver.get_model();','                double extract_start=session->elapsed();\n                z3::model cdcl_m = cdcl_solver.get_model();\n                session->extract_seconds=session->elapsed()-extract_start;')
edit('src/sampler/liasampler.cpp','            m_ls = ls_solver.get_model();','            double extract_start=session->elapsed();\n            m_ls = ls_solver.get_model();')
edit('src/sampler/liasampler.cpp','            record_model(m_ls, samplesFile);','            session->extract_seconds=session->elapsed()-extract_start;\n            record_model(m_ls, samplesFile);')

edit('src/sampler/liasampler.cpp','            ls_solver.set("random_seed", gen_random_seed());','            session->highdiv_seed=gen_random_seed();\n            ls_solver.set("random_seed", session->highdiv_seed);')
