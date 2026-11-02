from common6 import *
import shutil
def patch(tree,variant):
    old=ROOT/f'worktrees/round5_{variant}';z=tree/'z3/src';h=tree/'round6_include';h.mkdir(exist_ok=True)
    for p in (old/'round5_include').glob('*'):
        if p.is_file():shutil.copyfile(p,h/p.name)
    def edit(p,a,b,n=1):
        s=p.read_text();assert s.count(a)==n,(str(p),a[:80],s.count(a));p.write_text(s.replace(a,b))
    for rel in ['sampler/sampler.h','sampler/sampler.cpp','smt/smt_context.cpp']:shutil.copyfile(old/'z3/src'/rel,z/rel)
    for name in ['stagnation_guard','sha256','guard_trace']:shutil.copyfile(ROOT/f'include/round6/{name}.hpp',z/f'util/r6_{name}.hpp')
    shutil.copyfile(ROOT/'src/round6/guard_bridge.inc',z/'sampler/guard_bridge.inc')
    p=z/'sampler/sampler.h';p.write_text('#include "util/r6_guard_trace.hpp"\n'+p.read_text())
    edit(p,'    std::unique_ptr<r5::Probe> m_r5;','''    r6::GuardTrace m_r6;
    void r6_begin(std::unordered_map<std::string,std::string> const&);
    void r6_finish(std::string const&,bool);
    std::unique_ptr<r5::Probe> m_r5;''')
    edit(p,'        mt.seed(seed);','        mt.seed(seed);\n        m_r6.seed=seed;')
    p=z/'sampler/sampler.cpp';edit(p,'#include "ccss_probe.inc"','#include "ccss_probe.inc"\n#include "guard_bridge.inc"')
    edit(p,'    if(improve&&m_r5&&m_r5->active&&m_r5->first_initialized)', '    m_r6.guard.observe(_best_found_cost);\n    if(improve&&m_r5&&m_r5->active&&m_r5->first_initialized)')
    edit(p,'void ls_sampler::initialize() {','void ls_sampler::initialize() {\n    ++m_r6.guard.initialization_count;')
    edit(p,'bool ls_sampler::ls_sampling() {','bool ls_sampler::ls_sampling() {\n    r6::SearchTimer r6_search_timer(m_r6,mt);')
    edit(p,'            _best_found_cost = std::max(1, _best_found_cost);\n            return false;','            _best_found_cost = std::max(1, _best_found_cost);\n            m_r6.reason="arith_unknown";\n            return false;')
    edit(p,'    const bool found = search();','    const bool found = search();\n    if(found)m_r6.reason="sat";\n    else if(m_r6.reason=="unknown")m_r6.reason=is_overflow?"arith_unknown":"native_exhausted";')
    edit(p,'    for (_step = 1; _step < _max_step; ++_step) {','    for (_step = 1; _step < _max_step; ++_step) {\n        m_r6.guard.tick(_step);')
    edit(p,'{if(m_r5)m_r5->exit="native_cutoff";break;}', '{m_r6.reason="native_cutoff";if(m_r5)m_r5->exit="native_cutoff";break;}')
    guard='if(m_r6.guard.should_yield(_unsat_clauses->size())){m_r6.reason="ccss_stagnation_yield";if(m_r5)m_r5->exit=m_r6.reason;return false;}'
    edit(p,'            if (is_overflow) continue;','            if (is_overflow) {'+guard+'continue;}')
    edit(p,'        no_improve_cnt = (update_best_solution()) ? 0 : (no_improve_cnt + 1);','        no_improve_cnt = (update_best_solution()) ? 0 : (no_improve_cnt + 1);\n        '+guard)
    edit(p,'        auto found = last_cdcl_model.find(name);','        auto found = last_cdcl_model.find(name);\n        if(m_r6.active)m_r6.read(name,found==last_cdcl_model.end()?r6::J(nullptr):r6::J(found->second));')
    p=z/'smt/smt_context.cpp'
    edit(p,'            try {\n                if(m_ls_sampler->m_r5)', '            m_ls_sampler->r6_begin(m.last_CDCL_model);\n            try {\n                if(m_ls_sampler->m_r5)')
    edit(p,'                    return check_finalize(l_true);','                    m_ls_sampler->r6_finish("sat",true);\n                    return check_finalize(l_true);')
    edit(p,'            } catch (const std::exception& error) {','            } catch (const std::exception& error) {\n                m_ls_sampler->m_r6.error=error.what();\n                m_ls_sampler->r6_finish(dynamic_cast<std::out_of_range const*>(&error)?"arith_unknown":"exception",false);')
    edit(p,'            if(m_ls_sampler->m_r5)m_ls_sampler->m_r5->flush();\n            return check_finalize(l_undef);','            if(m_ls_sampler->m_r5)m_ls_sampler->m_r5->flush();\n            m_ls_sampler->r6_finish(m_ls_sampler->m_r6.reason,false);\n            return check_finalize(l_undef);')
    p=h/'session.hpp'
    edit(p,'        if(std::getenv("GUIDED_R5_EXCHANGE_DIR"))', '''        if(std::getenv("GUIDED_R6_TRACE_DIR")){setenv("GUIDED_R6_QUERY",std::to_string(query).c_str(),1);setenv("GUIDED_R6_LAST_REASON","not_entered",1);unsetenv("GUIDED_R6_LAST_CALL_ID");}
        if(std::getenv("GUIDED_R5_EXCHANGE_DIR"))''')
    edit(p,'        queries<<Json({', '''        std::string r6_raw=std::getenv("GUIDED_R6_LAST_REASON")?std::getenv("GUIDED_R6_LAST_REASON"):"not_recorded";
        std::string r6_reason=end>=wall?"host_deadline":interrupted?"host_cancelled":result==z3::sat?"sat":result==z3::unsat?"unsat":r6_raw;
        if(source=="CCSS"&&std::getenv("GUIDED_R6_TRACE_DIR")){std::ofstream f(dir+"/ccss_guard_host.jsonl",std::ios::app);f<<Json({{"source_query_id",query},{"native_call_id",std::getenv("GUIDED_R6_LAST_CALL_ID")?Json(std::stoull(std::getenv("GUIDED_R6_LAST_CALL_ID"))):Json(nullptr)},{"start",query_begin},{"host_end",end},{"whole_host_ccss_wall_seconds",end-query_begin},{"exit_reason",r6_reason},{"native_exit_reason",r6_raw},{"host_result",result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown"},{"host_deadline_reached",end>=wall},{"host_cancelled",bool(interrupted)},{"model_produced_by_check",result==z3::sat},{"guard_enabled",std::getenv("GUIDED_CCSS_STAGNATION_GUARD")&&std::string(std::getenv("GUIDED_CCSS_STAGNATION_GUARD"))=="1"}}).dump()<<'\\n';}
        queries<<Json({''')
    edit(p,'{"reason_unknown",result==z3::unknown?solver.reason_unknown():""}', '{"ccss_exit_reason",source=="CCSS"?Json(r6_reason):Json(nullptr)},{"ccss_native_exit_reason",source=="CCSS"?Json(r6_raw):Json(nullptr)},{"reason_unknown",result==z3::unknown?solver.reason_unknown():""}')
    for rel in ['HighDiv/makefile','HighDiv/src/sampler/liasampler.cpp']:shutil.copyfile(old/rel,tree/rel)
    p=tree/'HighDiv/makefile';s=p.read_text().replace(str(old/'round5_include'),str(h));p.write_text(s)
    print('Generated Round6 guard overlay',tree)
if __name__=='__main__':patch(pathlib.Path(sys.argv[1]),sys.argv[2])
