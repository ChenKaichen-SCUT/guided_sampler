from common_r import *
import shutil,argparse
p=argparse.ArgumentParser();p.add_argument('variant',choices=['release','sanitize']);p.add_argument('--attempt',required=True);a=p.parse_args()
out=attempt('build_logs',a.variant+'_'+a.attempt)
assert not (MAN/'implementation.json').exists(),'implementation frozen'
tree=ROOT/f'worktrees/refinement_{a.variant}';src=ROOT/f'worktrees/round6_{a.variant}';prefix=ROOT/f'deps/round6_{a.variant}'
if not tree.exists():
    tmp=pathlib.Path('/tmp/guided_sampler_refinement_worktrees')/a.variant;tmp.mkdir(parents=True,exist_ok=False);tree.symlink_to(tmp,target_is_directory=True)
    shutil.copytree(src/'HighDiv',tree/'HighDiv',ignore=shutil.ignore_patterns('build','highdiv'))
inc=tree/'refinement_include';inc.mkdir(exist_ok=True)
s=(src/'round6_include/session.hpp').read_text().replace('#include "inherited_reference.hpp"','#include "inherited_reference.hpp"\n#include "refinement/host_adapter.hpp"\n#include <random>\n#include "round6/sha256.hpp"')
s=s.replace('public:\n','public:\n'+(ROOT/'src/refinement/session_members.inc').read_text(),1)
s=s.replace('        if(semantic&&guidance){Json nodes=', '        if(!guidance)fallback_ast=std::make_unique<OriginalAst>(formula);\n        split=std::make_unique<refinement::NativeOutputSplit>(native_ast().nodes.size(),wall,refinement::mode_from(std::getenv("REFINEMENT_MODE")?std::getenv("REFINEMENT_MODE"):"off"));\n        split->budget.cancelled=[](){return bool(interrupted);};\n        if(semantic&&guidance){Json nodes=',1)
s=s.replace('        source=phase;', '        real_hard.clear();for(auto e:asms)real_hard.push_back(e);\n        source=phase;',1)
start=s.index('    bool commit(');end=s.index('    void finish()',start)
s=s[:start]+(ROOT/'src/refinement/session_commit.inc').read_text()+'\n'+s[end:]
s=s.replace('        done=true;if(watchdog.joinable())watchdog.join();\n        if(status', '        done=true;if(watchdog.joinable())watchdog.join();\n        if(split){std::ofstream f(dir+"/refinement_summary.json");f<<Json({{"native_count",split->native.accepted_count},{"output_count",split->output.committed_count},{"native_raw_count",split->native_raw_count},{"output_duplicates",split->output_duplicates},{"replacements",split->replacements},{"strict_covered_replacements",split->covered_replacements},{"deadline_missed_after_native_ready",split->deadline_missed_after_native_ready},{"budget",refinement::budget_json(split->budget)}}).dump(2)<<"\\n";}\n        if(status',1)
(inc/'session.hpp').write_text(s)
for header in (src/'round6_include').glob('*.hpp'):
    if header.name!='session.hpp':shutil.copy2(header,inc/header.name)
s=(src/'HighDiv/src/sampler/liasampler.cpp').read_text()
s=s.replace('            double inputs_start=', '            session->state_trace(mt,m_ls,"query_input_before");\n            double inputs_start=')
s=s.replace('            double prepare_start=', '            session->state_trace(mt,m_ls,"query_input_after");\n            double prepare_start=')
s=s.replace('            res = num_samples ?', '            session->native_begin();\n            res = num_samples ?').replace('            double check_end=', '            session->native_end();\n            double check_end=')
s=s.replace('                z3::model cdcl_m =', '                session->native_begin();\n                z3::model cdcl_m =').replace('                session->extract_seconds=', '                session->native_end();\n                session->extract_seconds=')
s=s.replace('                record_model(cdcl_m, samplesFile);','                session->state_trace(mt,m_ls,"delivery_before");\n                record_model(cdcl_m, samplesFile);\n                session->state_trace(mt,m_ls,"delivery_after");')
s=s.replace('            z3::check_result check_res =','            session->native_begin();\n            z3::check_result check_res =').replace('            session->end_query(ls_solver,check_res);','            session->native_end();\n            session->end_query(ls_solver,check_res);')
s=s.replace('            m_ls = ls_solver.get_model();','            session->native_begin();\n            m_ls = ls_solver.get_model();').replace('            session->ls_reference_source(m_ls);','            session->native_end();\n            session->ls_reference_source(m_ls);')
s=s.replace('            record_model(m_ls, samplesFile);','            session->state_trace(mt,m_ls,"delivery_before");\n            record_model(m_ls, samplesFile);\n            session->state_trace(mt,m_ls,"delivery_after");')
s=s.replace('        parseSmtFile();', '        {std::ifstream input(smtFilePath,std::ios::binary);if(!input)throw std::runtime_error("input hash read failed");std::string bytes((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());session->input_sha=r6::sha256(bytes); }\n        parseSmtFile();')
s=s.replace('num_samples=session->formal;','num_samples=session->split->native.accepted_count;')
(tree/'HighDiv/src/sampler/liasampler.cpp').write_text(s)
p=tree/'HighDiv/makefile';s=(src/'HighDiv/makefile').read_text().replace(str(src/'round6_include'),str(inc));p.write_text(s)
flags='-O3 -DNDEBUG -std=c++20 -Wall' if a.variant=='release' else '-O1 -g -std=c++20 -Wall -fsanitize=address,undefined -fno-omit-frame-pointer'
cmd=['make','-C',str(tree/'HighDiv'),'-j2',f'Z3_PREFIX={prefix}',f'CXXFLAGS={flags}']
with open(out/'compile.log','w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
write(out/'summary.json',{'returncode':r.returncode,'command':cmd,'library_sha256':digest(prefix/'lib/libz3.so'),'binary_sha256':digest(tree/'HighDiv/highdiv') if r.returncode==0 else None})
print(out,r.returncode);sys.exit(r.returncode)
