#!/usr/bin/env python3
"""Apply A-only metadata/phase patch to a NEW verified upstream copy. No B patch."""
import pathlib,shutil,sys,subprocess,tempfile
from common import ROOT,UP
root=pathlib.Path(sys.argv[1]);target_z=root/'z3/src';staging=tempfile.TemporaryDirectory(prefix='round2-patch-');stage=pathlib.Path(staging.name);z=stage/'z3/src'
paths=['solver/solver.h','solver/combined_solver.cpp','solver/tactic2solver.cpp','tactic/goal.h','tactic/goal.cpp','tactic/tactic.h','tactic/tactic.cpp','tactic/tactical.cpp','smt/smt_context.h','smt/smt_context.cpp','smt/smt_solver.cpp','smt/tactic/smt_tactic_core.cpp','sat/tactic/sat_tactic.cpp','api/api_solver.cpp']
for p in paths:
 (z/p).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(UP/'z3/src'/p,z/p)
def edit(p,a,b,count=1):
 f=z/p;s=f.read_text();assert s.count(a)>=count,(p,a);f.write_text(s.replace(a,b,count))
for p,d in [('include/round2/a_shared.hpp','util/a_shared.hpp'),('include/round2/z3_a_guidance.h','api/z3_a_guidance.h'),('src/round2/a_state.h','util/a_state.h'),('src/round2/a_internal_view.h','smt/a_internal_view.h'),('src/round2/a_context.inc','smt/a_context.inc')]:
 (z/d).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,z/d)
forward='#include <memory>\nnamespace a2 { struct Run; struct ContextCache; }\n'
edit('solver/solver.h','#include "util/params.h"','#include "util/params.h"\n'+forward)
edit('solver/solver.h','    solver(ast_manager& m):','    std::shared_ptr<a2::Run> m_A;\n    virtual void set_A_guidance(std::shared_ptr<a2::Run> r) { m_A=std::move(r); }\n    solver(ast_manager& m):')
edit('solver/combined_solver.cpp','#include "solver/solver.h"','#include "solver/solver.h"\n#include "util/a_state.h"')
edit('solver/combined_solver.cpp','    void set_phase(expr* e) override','    void set_A_guidance(std::shared_ptr<a2::Run> r) override { solver::set_A_guidance(r);m_solver1->set_A_guidance(r);m_solver2->set_A_guidance(r); }\n    void set_phase(expr* e) override')
edit('solver/combined_solver.cpp','        m_check_sat_executed  = true;','        if(m_A)m_A->start();\n        m_check_sat_executed  = true;')
edit('solver/combined_solver.cpp','            // must use incremental solver','            if(m_A){m_A->route="solver2";m_A->route_reason="native_assumptions_or_ignore_solver1";}\n            // must use incremental solver')
edit('solver/combined_solver.cpp','        if (m_inc_mode) {','        if (m_inc_mode) {\n            if(m_A){m_A->route="solver2";m_A->route_reason="native_incremental_mode";}')
edit('solver/combined_solver.cpp','                if (r != l_undef ||','                if(m_A&&m_A->expired()){set_reason_unknown("guidance_exposure_limit");m_A->event({{"kind","skip_combined_fallback"}});return l_undef;}\n                if (r != l_undef ||')
edit('solver/combined_solver.cpp','                if ((r != l_undef ||','                if(m_A&&m_A->expired()){set_reason_unknown("guidance_exposure_limit");m_A->event({{"kind","skip_combined_fallback"}});return l_undef;}\n                if ((r != l_undef ||')
edit('solver/combined_solver.cpp','        m_use_solver1_results = true;\n        return m_solver1->check_sat_core','        if(m_A){if(m_A->expired()){set_reason_unknown("guidance_exposure_limit");return l_undef;}m_A->route="solver1";m_A->route_reason=m_inc_mode?"native_fallback":"native_nonincremental";}\n        m_use_solver1_results = true;\n        return m_solver1->check_sat_core')
edit('tactic/goal.h','#pragma once','#pragma once\n'+forward)
edit('tactic/goal.h','    goal(ast_manager & m, bool models_enabled','    std::shared_ptr<a2::Run> m_A; // query-owned nonlogical sidecar; no AST pointers\n    goal(ast_manager & m, bool models_enabled')
edit('tactic/goal.cpp','    m_mc = src.m_mc.get();','    m_A = src.m_A;\n    m_mc = src.m_mc.get();')
edit('tactic/goal.cpp','    target.m_depth                =','    target.m_A                    = m_A;\n    target.m_depth                =')
edit('tactic/goal.cpp','    res->m_inconsistent = m_inconsistent;','    res->m_A = m_A; // canonical IR is manager-independent\n    res->m_inconsistent = m_inconsistent;')
# reset/reset_all preserve the active query sidecar; close() revokes it at outer ownership boundary.
edit('solver/tactic2solver.cpp','#include "solver/tactic2solver.h"','#include "solver/tactic2solver.h"\n#include "util/a_state.h"')
edit('solver/tactic2solver.cpp','    for (expr* e : m_assertions) {','    g->m_A=m_A;if(m_A)m_A->start();\n    for (expr* e : m_assertions) {')
edit('solver/tactic2solver.cpp','    return m_result->status();','    if(m_A&&m_A->expired()){m_result->set_status(l_undef);m_result->m_unknown="guidance_exposure_limit";}\n    return m_result->status();')
edit('tactic/tactic.h','    imp *  m_imp;','    imp *  m_imp;\n    std::shared_ptr<a2::Run> m_A;unsigned m_A_stage=0;')
edit('tactic/tactic.cpp','#include "tactic/tactic.h"','#include "tactic/tactic.h"\n#include "util/a_state.h"')
edit('tactic/tactic.cpp','tactic_report::tactic_report(char const * id, goal const & g) {','tactic_report::tactic_report(char const * id, goal const & g) {\n    m_A=g.m_A;if(m_A&&!m_A->closed){if(m_A->expired())throw tactic_exception("guidance_exposure_limit");m_A_stage=m_A->stage_begin(id);}')
edit('tactic/tactic.cpp','tactic_report::~tactic_report() {','tactic_report::~tactic_report() {\n    if(m_A_stage)m_A->stage_end(m_A_stage);')
edit('tactic/tactical.cpp','#include "tactic/tactical.h"','#include "tactic/tactical.h"\n#include "util/a_state.h"')
edit('tactic/tactical.cpp','            tactic * t = m_ts[i];','            if(in->m_A&&in->m_A->expired()){in->m_A->event({{"kind","skip_tactic_fallback"},{"next_stage",i}});throw tactic_exception("guidance_exposure_limit");}\n            tactic * t = m_ts[i];')
edit('tactic/tactical.cpp','                catch (tactic_exception &) {','                catch (tactic_exception &) {\n                    if(in->m_A&&in->m_A->expired()){in->m_A->event({{"kind","skip_tactic_fallback"},{"next_stage",i+1}});throw;}')
edit('smt/smt_context.h','#pragma once','#pragma once\n'+forward)
edit('smt/smt_context.h','        theory_user_propagator*          m_user_propagator;', '''        std::shared_ptr<a2::Run> m_A;
        std::unique_ptr<a2::ContextCache> m_A_data;
        unsigned m_A_generation=0,m_A_call=0;uint64_t m_A_assignment_serial=0;
        bool m_A_local_disabled=false,m_A_snapshot_done=false;
        void prepare_A_search_epoch(char const*);
        void A_binding_snapshot();
        bool apply_A_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase);
        void A_assignment(literal,bool);
        void A_finalize(lbool);
        theory_user_propagator*          m_user_propagator;''')
edit('smt/smt_context.h','        bool b_internalized(expr const * n) const {','        void attach_A_guidance(std::shared_ptr<a2::Run>,char const*);\n        void detach_A_guidance();\n        bool b_internalized(expr const * n) const {')
edit('smt/smt_context.cpp','#include "smt/smt_context.h"','#include "smt/smt_context.h"\n#include "util/a_state.h"\n#include "smt/a_internal_view.h"')
edit('smt/smt_context.cpp','bool context::get_cancel_flag() {','bool context::get_cancel_flag() {\n    if(m_A&&m_A->expired()){m_last_search_failure=CANCELED;return true;}')
edit('smt/smt_context.cpp','bool context::decide() {','#include "smt/a_context.inc"\n\nbool context::decide() {')
edit('smt/smt_context.cpp','    bool used_queue = false;','    bool used_queue = false;\n    bool a_ordinary_phase = false;')
edit('smt/smt_context.cpp','        is_pos = guess(var, phase);','        a_ordinary_phase=phase==l_undef&&!get_bdata(var).try_true_first()&&!get_bdata(var).is_quantifier();\n        is_pos = guess(var, phase);')
edit('smt/smt_context.cpp','''        l = literal(var, false);
    }

    if (!is_pos) l.neg();''','''        l = literal(var, false);
        if(m_A)m_A->count(m_A_call,"user_propagator_skipped");
    }
    else if(used_queue&&a_ordinary_phase&&!m_user_propagator){
        const bool_var native_var=var;const bool native_phase=is_pos;
        apply_A_phase_hint(native_var,native_phase,is_pos);
        SASSERT(var==native_var);
    }
    else if(m_A)m_A->count(m_A_call,"special_decision_skipped");

    if (!is_pos) l.neg();''')
edit('smt/smt_context.cpp','    m_case_split_queue->assign_lit_eh(l);','    if(m_A)A_assignment(l,false);\n    m_case_split_queue->assign_lit_eh(l);')
edit('smt/smt_context.cpp','        m_assignment[l.index()] = l_undef;','        if(m_A)A_assignment(l,true);\n        m_assignment[l.index()] = l_undef;')
edit('smt/smt_context.cpp','lbool context::setup_and_check(bool reset_cancel) {','lbool context::setup_and_check(bool reset_cancel) {\n    if(m_A)prepare_A_search_epoch("setup_and_check");')
edit('smt/smt_context.cpp','lbool context::check(unsigned num_assumptions, expr* const* assumptions, bool reset_cancel) {','lbool context::check(unsigned num_assumptions, expr* const* assumptions, bool reset_cancel) {\n    if(m_A)prepare_A_search_epoch("check");')
edit('smt/smt_context.cpp','void context::init_search() {','void context::init_search() {\n    if(m_A)A_binding_snapshot();')
edit('smt/smt_context.cpp','    m_internal_completed = l_false;\n    if (r == l_true','    if(m_A)A_finalize(r);\n    m_internal_completed = l_false;\n    if (r == l_true')
edit('smt/smt_solver.cpp','#include "smt/smt_kernel.h"','#include "smt/smt_kernel.h"\n#include "smt/smt_context.h"\n#include "util/a_state.h"')
edit('smt/smt_solver.cpp','            return m_context.check(num_assumptions, assumptions);','''            if(m_A)m_A->start();
            auto& ctx=m_context.get_context();ctx.attach_A_guidance(m_A,"smt_solver");
            struct cleanup {smt::context& c;~cleanup(){c.detach_A_guidance();}} guard{ctx};
            lbool r=m_context.check(num_assumptions, assumptions);
            if(m_A&&m_A->expired()){set_reason_unknown("guidance_exposure_limit");return l_undef;}return r;''')
edit('smt/tactic/smt_tactic_core.cpp','#include "smt/smt_kernel.h"','#include "smt/smt_kernel.h"\n#include "smt/smt_context.h"\n#include "util/a_state.h"')
edit('smt/tactic/smt_tactic_core.cpp','            if (d)\n                dealloc(d);','            if (d) {d->get_context().detach_A_guidance();dealloc(d);}')
edit('smt/tactic/smt_tactic_core.cpp','            SASSERT(m_ctx);','            SASSERT(m_ctx);\n            m_ctx->get_context().attach_A_guidance(in->m_A,"smt_tactic");')
edit('smt/tactic/smt_tactic_core.cpp','            m_ctx->collect_statistics(m_stats);\n            proof_ref','            if(in->m_A&&in->m_A->expired())throw tactic_exception("guidance_exposure_limit");\n            m_ctx->collect_statistics(m_stats);\n            proof_ref')
edit('sat/tactic/sat_tactic.cpp','        imp proc(g->m(), m_params, m_var2value);','        tactic_report A_leaf_report("sat.non_smt_leaf",*g);\n        imp proc(g->m(), m_params, m_var2value);')
edit('api/api_solver.cpp','#include<thread>','#include<thread>\n#include "api/z3_a_guidance.h"\n#include "util/a_state.h"')
edit('api/api_solver.cpp','    static void init_solver_log(',(ROOT/'src/round2/a_api.inc').read_text()+'\n    static void init_solver_log(')
subprocess.run([sys.executable,str(ROOT/'scripts/patch_common_z3.py'),str(stage)],check=True)
for f in z.rglob('*'):
 if f.is_file():
  dest=target_z/f.relative_to(z);dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists() or f.read_bytes()!=dest.read_bytes():shutil.copyfile(f,dest)
print('A-only patch applied; old B patch was never applied:',root)
