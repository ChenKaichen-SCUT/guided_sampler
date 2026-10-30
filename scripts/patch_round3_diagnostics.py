#!/usr/bin/env python3
"""Layer bounded semantic observations on a freshly applied round2 patch."""
import pathlib,sys,shutil,subprocess,tempfile
from common import ROOT,UP
target=pathlib.Path(sys.argv[1]);staging=tempfile.TemporaryDirectory(prefix='round3-patch-');root=pathlib.Path(staging.name);z=root/'z3/src'
subprocess.run([sys.executable,ROOT/'scripts/patch_round2_z3.py',root],check=True)
def edit(p,a,b,n=1):
 f=z/p;s=f.read_text();assert s.count(a)>=n,(p,a);f.write_text(s.replace(a,b,n))
(z/'model').mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/'src/round3/semantic_trace.h',z/'model/semantic_trace.h')
shutil.copyfile(ROOT/'src/round3/semantic_context.inc',z/'smt/semantic_context.inc')
edit('util/a_state.h','"final_atom_truth"','"final_internal_assignment"')
edit('util/a_state.h',' std::string route,route_reason;',' std::string route,route_reason;\n uintptr_t semantic_manager=0;unsigned semantic_provider=0;std::string semantic_chain;std::vector<std::shared_ptr<void>> semantic_snapshots;')
edit('solver/solver.h','    std::shared_ptr<a2::Run> m_A;','    std::shared_ptr<a2::Run> m_A,m_semantic_last;')
edit('solver/solver.h','{ m_A=std::move(r); }','{ if(r)m_semantic_last=r;m_A=std::move(r); }')
edit('smt/smt_context.h','namespace a2 { struct Run; struct ContextCache; }','namespace a2 { struct Run; struct ContextCache; }\nnamespace s3 { struct PendingSemanticSnapshot; }')
edit('smt/smt_context.h','        std::shared_ptr<a2::Run> m_A;','''        std::shared_ptr<s3::PendingSemanticSnapshot> m_S,m_S_pending;
        void S_watch(unsigned,a2::Json); // declaration replaced below
        void S_event(unsigned,char const*,int=-1);
        void S_assignment(literal,bool,bool=false);
        void S_sample(char const*);
        void S_cause(unsigned);
        void S_theory(unsigned,unsigned,unsigned,bool,bool);
        void S_model(model*);
        std::shared_ptr<a2::Run> m_A;''')
# The public context header need not import nlohmann or the complete Run.
edit('smt/smt_context.h','#pragma once','#pragma once\n#include <nlohmann/json_fwd.hpp>')
edit('smt/smt_context.h','a2::Json); // declaration replaced below','nlohmann::json);')
edit('smt/smt_context.h','        void detach_A_guidance();','        void detach_A_guidance();\n        unsigned semantic_backend_id() const;')
edit('smt/smt_context.cpp','#include "smt/a_internal_view.h"','#include "smt/a_internal_view.h"\n#include "model/semantic_trace.h"')
edit('smt/smt_context.cpp','#include "smt/a_context.inc"','#include "smt/a_context.inc"\n#include "smt/semantic_context.inc"')
edit('smt/a_context.inc','    detach_A_guidance();if(!run||run->closed)return;','    detach_A_guidance();m_S_pending.reset();if(!run||run->closed)return;')
edit('smt/a_context.inc','    auto& b=m_A->call(m_A_call);b["bool_vars_before_register"]','    if(s3::enabled()&&!m_fparams.m_ls_sampling)m_S=std::make_shared<s3::PendingSemanticSnapshot>(m,m_A,m_A_call,m_A_generation);\n    auto& b=m_A->call(m_A_call);b["bool_vars_before_register"]')
edit('smt/a_context.inc','    m_A_data->tracks.clear();','    if(m_S){S_sample("detach");m_S->flush();if(b["result"]=="sat")m_S_pending=m_S;m_S.reset();}\n    m_A_data->tracks.clear();')
edit('smt/a_context.inc','    unsigned encounter=0;','    if(m_S&&r.ordinal<=64)m_S->encounters.push_back({{"decision_id",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"complete",n.complete},{"reason",n.reason},{"ast_kind",is_app(e)?to_app(e)->get_decl_kind():0}});\n    unsigned encounter=0;')
edit('smt/a_context.inc','if(found==r.index->entries.end()){','if(found==r.index->entries.end()){if(m_S&&s3::select_unmapped(n.key))S_watch(native_var,{{"kind","unmapped"},{"canonical_key",n.key},{"normalization_kind",n.kind},{"canonical_negated",n.negated}});')
edit('smt/a_context.inc','    m_A_data->tracks.push_back({native_var,e,action,0,false});','    if(m_S){auto a=r.actions.back().json();a["kind"]="suggestion";S_watch(native_var,a);}\n    m_A_data->tracks.push_back({native_var,e,action,0,false});')
edit('smt/a_context.inc','void context::A_finalize(lbool result){','void context::A_finalize(lbool result){\n    S_sample("final_internal_assignment");')
edit('smt/smt_context.cpp','    d.m_scope_lvl = m_scope_lvl;','    d.m_scope_lvl = m_scope_lvl;\n    if(m_S)S_assignment(l,false,decision);')
edit('smt/smt_context.cpp','        m_atom_propagation_queue.push_back(l);','        m_atom_propagation_queue.push_back(l);\n        if(m_S)S_event(l.var(),"atom_queue_enqueued",!l.sign());')
edit('smt/smt_context.cpp','        if(m_A)A_assignment(l,true);','        if(m_S)S_assignment(l,true);\n        if(m_A)A_assignment(l,true);')
edit('smt/smt_context.cpp','        SASSERT(val != l_undef);\n        if (get_bdata(v).is_enode())','        SASSERT(val != l_undef);\n        if(m_S){S_event(v,"atom_queue_consumed",val==l_true);S_cause(v);}\n        if (get_bdata(v).is_enode())')
edit('smt/smt_context.cpp','                add_eq(get_enode(lhs), get_enode(rhs), eq_justification(l));','                if(m_S)S_event(v,"equality_merged",1);\n                add_eq(get_enode(lhs), get_enode(rhs), eq_justification(l));')
edit('smt/smt_context.cpp','                if (!add_diseq(get_enode(lhs), get_enode(rhs))','                if(m_S)S_event(v,"disequality_added",0);\n                if (!add_diseq(get_enode(lhs), get_enode(rhs))')
edit('smt/smt_context.cpp','            th->assign_eh(v, val == l_true);','            if(m_S)S_event(v,"theory_atom_assign_eh",val==l_true);\n            th->assign_eh(v, val == l_true);')
edit('smt/smt_context.cpp','void context::propagate_bool_var_enode(bool_var v) {','void context::propagate_bool_var_enode(bool_var v) {\n    if(m_S)S_event(v,"bool_enode_propagated",get_assignment(v)==l_true);')
edit('smt/smt_context.cpp','void context::relevant_eh(expr* n) {','void context::relevant_eh(expr* n) {\n    if(m_S&&b_internalized(n))S_event(get_bool_var(n),"relevance_changed");')
edit('smt/smt_context.cpp','''            if (val != l_undef)
                m_atom_propagation_queue.push_back(literal(v, val == l_false));''','''            if (val != l_undef) {
                m_atom_propagation_queue.push_back(literal(v, val == l_false));
                if(m_S)S_event(v,"atom_queue_enqueued_after_relevance",val==l_true);
            }''')
edit('smt/smt_context.cpp','    m_th_eq_propagation_queue.push_back(new_th_eq(th, lhs, rhs));','    if(m_S)S_theory(th,lhs,rhs,true,false);\n    m_th_eq_propagation_queue.push_back(new_th_eq(th, lhs, rhs));')
edit('smt/smt_context.cpp','    m_th_diseq_propagation_queue.push_back(new_th_eq(th, lhs, rhs));','    if(m_S)S_theory(th,lhs,rhs,false,false);\n    m_th_diseq_propagation_queue.push_back(new_th_eq(th, lhs, rhs));')
edit('smt/smt_context.cpp','        th->new_eq_eh(curr.m_lhs, curr.m_rhs);','        if(m_S)S_theory(curr.m_th_id,curr.m_lhs,curr.m_rhs,true,true);\n        th->new_eq_eh(curr.m_lhs, curr.m_rhs);')
edit('smt/smt_context.cpp','        th->new_diseq_eh(curr.m_lhs, curr.m_rhs);','        if(m_S)S_theory(curr.m_th_id,curr.m_lhs,curr.m_rhs,false,true);\n        th->new_diseq_eh(curr.m_lhs, curr.m_rhs);')
# Limit causal ownership to the synchronous propagate_atoms iteration.
edit('smt/smt_context.cpp','    m_atom_propagation_queue.reset();\n    return true;','    if(m_S)m_S->causal_watch=~0u;\n    m_atom_propagation_queue.reset();\n    return true;')
edit('smt/smt_context.cpp','    return num_bool_vars;','    if(m_S){m_S->theory_causes.clear();S_sample("after_backtrack");}\n    return num_bool_vars;')
edit('smt/smt_context.cpp','void context::pop(unsigned num_scopes) {','void context::pop(unsigned num_scopes) {\n    m_S_pending.reset();')
edit('smt/smt_context.cpp','context::~context() {','context::~context() {\n    if(m_S)m_S->flush();m_S.reset();m_S_pending.reset();')
edit('smt/smt_context.cpp','''        mdl = m_model.get();
    }
}

void context::get_levels''','''        mdl = m_model.get();
    }
    if(mdl)S_model(mdl.get());
}

void context::get_levels''')
edit('api/api_solver.cpp','#include "util/a_state.h"','#include "util/a_state.h"\n#include "model/semantic_trace.h"')
edit('api/api_solver.cpp','        run->solver_id=','        run->semantic_manager=reinterpret_cast<uintptr_t>(&mk_c(c)->m());\n        run->solver_id=')
edit('api/api_solver.cpp','        Z3_model_ref * m_ref = alloc(Z3_model_ref, *mk_c(c));','        s3::outer(to_solver_ref(s)->m_semantic_last,_m.get());\n        Z3_model_ref * m_ref = alloc(Z3_model_ref, *mk_c(c));')
# Goal copies preserve explicit winning-provider identity through tactical composition.
edit('tactic/goal.h','    std::shared_ptr<a2::Run> m_A;','    unsigned semantic_provider=0;\n    std::shared_ptr<a2::Run> m_A;')
edit('tactic/goal.cpp','    m_A = src.m_A;','    semantic_provider=src.semantic_provider;\n    m_A = src.m_A;')
edit('tactic/goal.cpp','    target.m_A                    = m_A;','    target.semantic_provider=semantic_provider;\n    target.m_A                    = m_A;')
edit('tactic/goal.cpp','    res->m_A = m_A;','    res->semantic_provider=semantic_provider;\n    res->m_A = m_A;')
edit('smt/tactic/smt_tactic_core.cpp','m_ctx->get_model(md);','m_ctx->get_model(md);if(in->m_A)in->semantic_provider=m_ctx->get_context().semantic_backend_id();',2)
edit('tactic/tactic.cpp','#include "util/a_state.h"','#include "util/a_state.h"\n#include "model/semantic_trace.h"')
edit('tactic/tactic.cpp','        model_converter_ref mc = r[0]->mc();','''        if(g->m_A&&s3::enabled()){
            auto run=g->m_A;run->semantic_provider=r[0]->semantic_provider;
            run->semantic_chain="query:"+std::to_string(run->query)+":provider:"+std::to_string(run->semantic_provider);
            s3::ConverterTraceScope converter_scope(run);
            s3::BoundedBuffer buffer(262144);std::ostream chain(&buffer);if(r[0]->mc())r[0]->mc()->display(chain);auto value=buffer.value;bool overflow=buffer.truncated;
            auto row=s3::identity(run,run->semantic_provider,0);row["kind"]="converter_chain";row["converter_chain_id"]=run->semantic_chain;row["model_provider_backend_id"]=run->semantic_provider;row["display"]=value;row["overflow"]=overflow;s3::write(row);
        }
        model_converter_ref mc = r[0]->mc();''')
edit('api/api_solver.cpp','        lbool result = l_undef;','        struct SemanticCheckCleanup {std::shared_ptr<a2::Run> r;bool sat=false;~SemanticCheckCleanup(){if(r&&!sat)r->semantic_snapshots.clear();}} semantic_cleanup{to_solver_ref(s)->m_semantic_last};\n        lbool result = l_undef;')
edit('api/api_solver.cpp','        return static_cast<Z3_lbool>(result);','        semantic_cleanup.sat=result==l_true;\n        return static_cast<Z3_lbool>(result);')
# Structured identities from the actual converters on the selected chain.
(z/'ast/converters').mkdir(parents=True,exist_ok=True)
shutil.copyfile(UP/'z3/src/ast/converters/generic_model_converter.cpp',z/'ast/converters/generic_model_converter.cpp')
edit('ast/converters/generic_model_converter.cpp','#include "model/model_evaluator.h"','#include "model/model_evaluator.h"\n#include "model/semantic_trace.h"')
edit('ast/converters/generic_model_converter.cpp','void generic_model_converter::display(std::ostream & out) {','void generic_model_converter::display(std::ostream & out) {\n    if(s3::converter_trace())for(entry const& e:m_entries)s3::converter_entry(m,e.m_f.get(),e.m_def.get(),e.m_instruction==instruction::HIDE,m_orig.c_str());')
# Test-only native RNG audit; exactly one original state update per call.
shutil.copyfile(UP/'z3/src/util/util.h',z/'util/util.h')
edit('util/util.h','#pragma once','#pragma once\n#include <cstdio>\n#include <cstdlib>')
edit('util/util.h','        return ((m_data = m_data * 214013L + 2531011L) >> 16) & 0x7fff;','''        unsigned before=m_data;
        int result=((m_data = m_data * 214013L + 2531011L) >> 16) & 0x7fff;
        static const char* path=std::getenv("GUIDED_TEST_RNG_TRACE");
        if(path){if(auto f=std::fopen(path,"a")){std::fprintf(f,"%u %u %d\\n",before,m_data,result);std::fclose(f);}}
        return result;''')
edit('smt/smt_context.cpp','bool context::propagate_atoms() {','''bool context::propagate_atoms() {
    struct SemanticCauseScope {s3::PendingSemanticSnapshot* s;~SemanticCauseScope(){if(s)s->causal_watch=~0u;}} semantic_cause_scope{m_S.get()};''')
edit('api/api_solver.cpp','                result = to_solver_ref(s)->check_sat(num_assumptions, _assumptions);','                if(!to_solver_ref(s)->m_A)to_solver_ref(s)->m_semantic_last.reset();\n                result = to_solver_ref(s)->check_sat(num_assumptions, _assumptions);')
edit('api/api_solver.cpp','        to_solver_ref(s)->pop(n);','        if(to_solver_ref(s)->m_semantic_last)to_solver_ref(s)->m_semantic_last->semantic_snapshots.clear();to_solver_ref(s)->m_semantic_last.reset();\n        to_solver_ref(s)->pop(n);')
edit('api/api_solver.cpp','        LOG_Z3_solver_reset(c, s);','        LOG_Z3_solver_reset(c, s);\n        if(to_solver(s)->m_solver)to_solver(s)->m_solver->m_semantic_last.reset();')
for f in z.rglob('*'):
 if f.is_file():
  dest=target/'z3/src'/f.relative_to(z);dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists() or f.read_bytes()!=dest.read_bytes():shutil.copyfile(f,dest)
print('Round3 read-only hooks applied:',target)
