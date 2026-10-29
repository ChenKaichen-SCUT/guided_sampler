#!/usr/bin/env python3
import pathlib,sys,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
tree=pathlib.Path(sys.argv[1]);z=tree/'z3/src'
def edit(p,a,b,count=1):
    f=z/p;s=f.read_text();assert s.count(a)>=count,(p,a);f.write_text(s.replace(a,b,count))
shutil.copy(ROOT/'src/coverage_guidance.h',z/'solver/coverage_guidance.h')
shutil.copy(ROOT/'src/z3_broker.inc',z/'smt/z3_broker.inc')
shutil.copy(ROOT/'include/z3_guidance.h',z/'api/z3_guidance.h')
edit(pathlib.Path('solver/solver.h'),'#include "util/params.h"','#include "util/params.h"\n#include "solver/coverage_guidance.h"')
edit(pathlib.Path('solver/solver.h'),'    solver(ast_manager& m):','    std::shared_ptr<coverage_guidance> m_coverage;\n    virtual void set_coverage(std::shared_ptr<coverage_guidance> p) { m_coverage=std::move(p); }\n    solver(ast_manager& m):')
edit(pathlib.Path('solver/combined_solver.cpp'),'    void set_phase(expr* e) override', '    void set_coverage(std::shared_ptr<coverage_guidance> p) override {\n        solver::set_coverage(p); m_solver2->set_coverage(p);\n    }\n    void set_phase(expr* e) override')
edit(pathlib.Path('solver/combined_solver.cpp'),'        m_use_solver1_results = true;\n        return m_solver1->check_sat_core', '        m_use_solver1_results = true;\n        if(m_coverage) { m_coverage->unsupported++; m_coverage->fallback += m_coverage->backend==2; m_coverage->backend=1; }\n        return m_solver1->check_sat_core')
edit(pathlib.Path('smt/smt_context.h'),'#pragma once','#pragma once\n#include "solver/coverage_guidance.h"')
# Registry references follow ast manager lifetime (declared after m).
edit(pathlib.Path('smt/smt_context.h'),'        theory_user_propagator*          m_user_propagator;', '''        std::shared_ptr<coverage_guidance> m_coverage;
        expr_ref_vector m_coverage_registry{m};
        expr_ref_vector m_coverage_proxies{m};
        std::unordered_set<expr*> m_coverage_proxy_set;
        void prepare_coverage_targets();
        bool coverage_decide(bool_var& var, bool& is_pos, bool ordinary);
        theory_user_propagator*          m_user_propagator;''')
edit(pathlib.Path('smt/smt_context.h'),'        bool b_internalized(expr const * n) const {','        void set_coverage(std::shared_ptr<coverage_guidance> p) { m_coverage=std::move(p); }\n        bool b_internalized(expr const * n) const {')
edit(pathlib.Path('smt/smt_context.cpp'),'bool context::decide() {','#include "smt/z3_broker.inc"\n\nbool context::decide() {')
# Empty native queue still gives B its ordinary opportunity. No guess on null.
edit(pathlib.Path('smt/smt_context.cpp'),'''        if (var == null_bool_var) {
            push_trail(value_trail(m_has_case_split, false));
            return false;
        }''','''        if (var == null_bool_var) {
            is_pos=true;
            coverage_decide(var,is_pos,true);
            if (var == null_bool_var) {
                push_trail(value_trail(m_has_case_split, false));
                return false;
            }
            used_queue=false; // already arbitrated, no native queue entry removed
        }''')
# Need distinguish B empty queue from special; used_queue=false suppresses second broker.
edit(pathlib.Path('smt/smt_context.cpp'),'        is_pos = guess(var, phase);','        if (used_queue) is_pos = guess(var, phase);')
edit(pathlib.Path('smt/smt_context.cpp'),'''    if (decide_user_interference(var, is_pos)) {
        if (used_queue)
            m_case_split_queue->unassign_var_eh(original_choice);
        l = literal(var, false);
    }

    if (!is_pos) l.neg();''','''    if (decide_user_interference(var, is_pos)) {
        if (used_queue)
            m_case_split_queue->unassign_var_eh(original_choice);
        l = literal(var, false);
    }
    else if (used_queue) {
        if (coverage_decide(var, is_pos, true))
            m_case_split_queue->unassign_var_eh(original_choice);
        l = literal(var, false);
    }

    if (!is_pos) l.neg();''')
# Internalize after ordinary assertions and before assumptions: base-level definitions
# survive assumptions pop; init_assumptions/normal search perform propagation.
edit(pathlib.Path('smt/smt_context.cpp'),'            internalize_assertions();\n            add_theory_assumptions(asms);','            internalize_assertions();\n            prepare_coverage_targets();\n            add_theory_assumptions(asms);',2)
edit(pathlib.Path('smt/smt_solver.cpp'),'#include "smt/smt_kernel.h"','#include "smt/smt_kernel.h"\n#include "smt/smt_context.h"')
edit(pathlib.Path('smt/smt_solver.cpp'),'            return m_context.check(num_assumptions, assumptions);','''            m_context.get_context().set_coverage(m_coverage);
            struct clear_on_exit { smt::context& c; ~clear_on_exit(){c.set_coverage(nullptr);} } guard{m_context.get_context()};
            if(m_coverage) m_coverage->backend=2;
            return m_context.check(num_assumptions, assumptions);''')
edit(pathlib.Path('api/api_solver.cpp'),'#include<thread>','#include<thread>\n#include "api/z3_guidance.h"')
src=(ROOT/'src/z3_api.inc').read_text()
edit(pathlib.Path('api/api_solver.cpp'),'    static void init_solver_log(',src+'\n    static void init_solver_log(')
print('Patched solver metadata, SMT safe point and decision broker:',tree)

edit(pathlib.Path('smt/smt_context.cpp'),'    bool used_queue = false;\n','    bool used_queue = false;\n    bool coverage_arbitrated = false;\n')
edit(pathlib.Path('smt/smt_context.cpp'),'            coverage_decide(var,is_pos,true);','            coverage_decide(var,is_pos,true);\n            coverage_arbitrated=true;')
edit(pathlib.Path('smt/smt_context.cpp'),'    m_stats.m_num_decisions++;\n\n    push_scope();','    if(m_coverage && !used_queue && !coverage_arbitrated)++m_coverage->special;\n    m_stats.m_num_decisions++;\n\n    push_scope();')
edit(pathlib.Path('smt/smt_context.cpp'),'    if (decide_user_interference(var, is_pos)) {','    if (decide_user_interference(var, is_pos)) {\n        if(m_coverage)++m_coverage->special;')
