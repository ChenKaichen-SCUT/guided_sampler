"""Generate only R5 overlays from immutable R4 source; never edits the frozen trees."""
from common5 import *
import shutil
def patch(tree,variant):
    source=ROOT/f'worktrees/round4_S_{variant}';z=tree/'z3/src';h=tree/'round5_include';h.mkdir(exist_ok=True)
    for p in (ROOT/'include/round4/soft_reference').glob('*.hpp'):shutil.copyfile(p,h/p.name)
    def edit(path,old,new,count=1):
        s=path.read_text();assert s.count(old)==count,(path,old[:70],s.count(old));path.write_text(s.replace(old,new))
    edit(h/'preference_types.hpp','Legacy, Reference, Coverage','Legacy, Reference, Coverage, SupportOnly')
    shutil.copyfile(ROOT/'include/round5/coverage_policy.hpp',h/'coverage_policy.hpp')
    edit(h/'a_shared.hpp','#include "phase_evidence.hpp"','#include "phase_evidence.hpp"\n#include "coverage_policy.hpp"')
    p=h/'session.hpp';edit(p,'host_mode==3||host_mode==4','host_mode==3||host_mode==4||host_mode==5')
    edit(p,'q->policy=host_mode==4?', 'q->policy=host_mode==5?a2::r4::Policy::SupportOnly:host_mode==4?')
    edit(p,'host_mode==4?"S_cov":"S_ref"','host_mode==5?"S_support":host_mode==4?"S_full":"S_ref"')
    edit(p,'query_begin=elapsed();','query_begin=elapsed();\n        if(std::getenv("GUIDED_R5_EXCHANGE_DIR")){setenv("GUIDED_R5_QUERY",std::to_string(query).c_str(),1);setenv("GUIDED_R5_ROLE",phase.c_str(),1);setenv("GUIDED_R5_REMAINING",std::to_string(std::max(0.0,wall-elapsed())).c_str(),1);}')
    for name in ['a_shared.hpp','preference_types.hpp','coverage_policy.hpp']:shutil.copyfile(h/name,z/'util'/name)
    for original,new in [('decision_audit.hpp','r5_decision_audit.hpp'),('ccss_exchange_trace.hpp','r5_exchange_trace.hpp'),('ccss_replay_recipe.hpp','r5_replay_recipe.hpp')]:shutil.copyfile(ROOT/'include/round5'/original,z/'util'/new)
    affected=['util/a_state.h','smt/a_context.inc','ast/ast.cpp','sampler/sampler.h','sampler/sampler.cpp','smt/smt_context.cpp','smt/smt_context_pp.cpp','smt/smt_model_generator.cpp']
    for rel in affected:shutil.copyfile(source/'z3/src'/rel,z/rel)
    edit(z/'util/a_state.h','struct NonSmtLeaf {','#include "r5_decision_audit.hpp"\nstruct NonSmtLeaf {')
    edit(z/'smt/a_context.inc',(ROOT/'src/round4/soft_phase.inc').read_text(),(ROOT/'src/round5/soft_phase.inc').read_text())
    p=z/'ast/ast.cpp';edit(p,'ast_manager::~ast_manager() {','ast_manager::~ast_manager() {\n    r5::destroy(this);');p.write_text('#include "util/r5_exchange_trace.hpp"\n'+p.read_text())
    p=z/'smt/smt_model_generator.cpp';p.write_text('#include "util/r5_exchange_trace.hpp"\n'+p.read_text())
    edit(p,'        // send model\n        for (enode * n', '        // send model\n        r5::batch(&m,m_context->get_A_provider_id());\n        for (enode * n')
    edit(p,'                m.last_CDCL_model[d->get_name().str()] = var_val_stream.str();','''                m.last_CDCL_model[d->get_name().str()] = var_val_stream.str();
                if(r5::enabled()){std::ostringstream sort;sort<<mk_pp(d->get_range(),m);r5::write(&m,d->get_name().str(),var_val_stream.str(),{{"name",d->get_name().str()},{"sort",sort.str()},{"decl_id",d->get_id()},{"skolem",d->is_skolem()},{"arity",d->get_arity()},{"hidden",false},{"relevant",true}},m_context->get_A_provider_id());}''')
    # Provider accessor only, no changes to native ownership/layout.
    shutil.copyfile(source/'z3/src/smt/smt_context.h',z/'smt/smt_context.h')
    edit(z/'smt/smt_context.h','    bool apply_S_phase_hint(', 'public:\n    unsigned get_A_provider_id()const{return m_A_call;}\n    bool apply_S_phase_hint(')
    p=z/'sampler/sampler.h';p.write_text('#include "util/r5_replay_recipe.hpp"\n'+p.read_text())
    edit(p,'    // debug\n','''    std::unique_ptr<r5::Probe> m_r5;
    r5::J r5_state(bool initialized)const;
    void r5_begin_replay(r5::J const&,std::string const&,bool);
    void r5_first_initialize();
    void r5_point(char const*);
    r5::J r5_solution();
    // debug
''')
    edit(p,'        mt.seed(seed);','        mt.seed(seed);\n        if(r5::enabled())m_r5.reset(new r5::Probe(seed,timeout,mt));')
    edit(p,'        _num_lits = num_lits;','        if(m_r5&&m_r5->active)m_r5->recipe["make_lits_space"]=num_lits;\n        _num_lits = num_lits;')
    p=z/'sampler/sampler.cpp';edit(p,'namespace sampler {','namespace sampler {\n#include "ccss_probe.inc"')
    shutil.copyfile(ROOT/'src/round5/ccss_probe.inc',z/'sampler/ccss_probe.inc')
    edit(p,'void ls_sampler::build_lits(std::string& in_string) {','void ls_sampler::build_lits(std::string& in_string) {\n    if(m_r5&&m_r5->active)m_r5->recipe["build_lits"].push_back(in_string);')
    edit(p,'    last_cdcl_model = model;','''    r5::PhaseTimer build_timer(m_r5.get(),"build_instance_inclusive");
    if(m_r5&&m_r5->active){m_r5->recipe["clause_vec"]=clause_vec;m_r5->recipe["use_interval_move"]=_use_interval_move;m_r5->save("recipe",m_r5->recipe);}
    last_cdcl_model = model;''')
    edit(p,'    calc_var_intervals();','''    if(m_r5&&m_r5->active)m_r5->save("R1",r5_state(false));
    calc_var_intervals();
    if(m_r5&&m_r5->active){m_r5->save("R2",r5_state(false));m_r5->save("intervals",{{"reads",m_r5->reads},{"variables",m_r5->interval_rows}});}''')
    edit(p,'void ls_sampler::calc_var_intervals() {','void ls_sampler::calc_var_intervals() {\n    r5::PhaseTimer interval_timer(m_r5.get(),"calc_var_intervals_nested_in_build");')
    edit(p,'        if (found == last_cdcl_model.end()) return false;','        if (found == last_cdcl_model.end()){if(m_r5)m_r5->read(name,"missing",nullptr);return false;}')
    edit(p,'            value = string_to_int128(processNegNumber(found->second));\n            return true;', '            value = string_to_int128(processNegNumber(found->second));\n            if(m_r5)m_r5->read(name,"present",found->second,r5::decimal(value));return true;')
    edit(p,'        } catch (const std::exception&) {\n            return false;','        } catch (const std::exception& error) {\n            if(m_r5)m_r5->read(name,dynamic_cast<std::out_of_range const*>(&error)?"128bit_overflow":"parse_error",found->second,error.what());return false;')
    edit(p,'        valid[l_idx] = known;','''        valid[l_idx] = known;
        if(m_r5&&m_r5->active)m_r5->recipe["inequality_evaluation"].push_back({{"literal",l_idx},{"valid",known},{"computed_delta",r5::decimal(delta)}});''')
    edit(p,'        const auto& var = _vars[v_idx];\n        if (!var.is_lia || var.in_equal_closure', '''        const auto& var = _vars[v_idx];
        if(m_r5&&m_r5->active){unsigned ok=0,unknown=0;for(auto lit:var.literals){auto idx=std::abs(lit);if(_lits[idx].is_lia_lit&&!_lits[idx].is_equal){ok+=bool(valid[idx]);unknown+=!valid[idx];}}m_r5->interval_rows[v_idx]["valid_inequality_occurrences"]=ok;m_r5->interval_rows[v_idx]["unknown_or_overflow_inequality_occurrences"]=unknown;}
        if (!var.is_lia || var.in_equal_closure''')
    # Per-variable recorded intermediates are values already computed by native code.
    edit(p,'    // Evaluate each inequality once.', '''    if(m_r5&&m_r5->active){m_r5->interval_rows=r5::J::array();for(size_t i=0;i<_vars.size();++i){auto j=r5_variable(_vars[i],false);j["index"]=i;j["has_model_value"]=bool(has_model_value[i]);j["model_value"]=has_model_value[i]?r5::J(r5::decimal(cdcl_solution[i])):r5::J(nullptr);j["branch"]="not_processed";j["literal_intervals"]=r5::J::array();m_r5->interval_rows.push_back(j);}}
    // Evaluate each inequality once.''')
    edit(p,'        if (!var.is_lia || var.in_equal_closure || !has_model_value[v_idx]) continue;', '''        if (!var.is_lia || var.in_equal_closure || !has_model_value[v_idx]) {if(m_r5&&m_r5->active)m_r5->interval_rows[v_idx]["branch"]=!var.is_lia?"bool":var.in_equal_closure?"equal_closure":"missing_or_invalid_model";continue;}''')
    edit(p,'            auto inserted = clause_intervals.emplace(var.literal_clause[i], interval);','''            if(m_r5&&m_r5->active)m_r5->interval_rows[v_idx]["literal_intervals"].push_back({{"signed_literal",signed_idx},{"clause",var.literal_clause[i]},{"coefficient",r5::decimal(coefficient)},{"numerator",r5::decimal(numerator)},{"delta",r5::decimal(deltas[l_idx])},{"interval",{std::to_string(interval.start),std::to_string(interval.end)}}});
            auto inserted = clause_intervals.emplace(var.literal_clause[i], interval);''')
    edit(p,'        if (clause_intervals.empty()) continue;', '        if (clause_intervals.empty()){if(m_r5&&m_r5->active)m_r5->interval_rows[v_idx]["branch"]="no_usable_inequality";continue;}')
    marker='''            _vars_initialization_intervals[v_idx] = random_complement(feasible, mt, domain);
        }
    }
}'''
    edit(p,marker,'''            _vars_initialization_intervals[v_idx] = random_complement(feasible, mt, domain);
        }
        if(m_r5&&m_r5->active){auto& j=m_r5->interval_rows[v_idx];j["branch"]=var.in_occs_closure?"feasible":"complement";j["domain"]={std::to_string(domain.start),std::to_string(domain.end)};j["feasible"]={std::to_string(feasible.start),std::to_string(feasible.end)};j["result"]={std::to_string(_vars_initialization_intervals[v_idx].start),std::to_string(_vars_initialization_intervals[v_idx].end)};j["clause_intervals"]=r5::J::array();for(auto const& kv:clause_intervals)j["clause_intervals"].push_back({kv.first,std::to_string(kv.second.start),std::to_string(kv.second.end)});}
    }
}''')
    edit(p,'void ls_sampler::initialize() {','void ls_sampler::initialize() {\n    r5::PhaseTimer initialize_timer(m_r5.get(),"initialize_nested_in_search");')
    edit(p,'m_r5->save("intervals",{{"reads",m_r5->reads},{"variables",m_r5->interval_rows}});','m_r5->save("intervals",{{"reads",m_r5->reads},{"variables",m_r5->interval_rows},{"inequalities",m_r5->recipe.value("inequality_evaluation",r5::J::array())}});')
    edit(p,'    update_best_solution();\n}', '    update_best_solution();\n    r5_first_initialize();\n}')
    edit(p,'void ls_sampler::construct_solution_score() {','void ls_sampler::construct_solution_score() {\n    r5::PhaseTimer value_timer(m_r5.get(),"value_generation_nested_in_initialize");\n    if(m_r5&&m_r5->active&&!m_r5->first_initialized)m_r5->recipe["initial_values"]=r5::J::array();')
    edit(p,'            _solution[i] = (mt() % 2 == 1) ? 1 : -1;', '''            _solution[i] = (mt() % 2 == 1) ? 1 : -1;
            if(m_r5&&m_r5->active&&!m_r5->first_initialized)m_r5->recipe["initial_values"].push_back({{"index",i},{"branch","bool"},{"value",r5::decimal(_solution[i])}});''')
    edit(p,'            _solution[i] = std::max(var.low_bound, std::min<__int128_t>(0, var.upper_bound));','''            _solution[i] = std::max(var.low_bound, std::min<__int128_t>(0, var.upper_bound));
            if(m_r5&&m_r5->active&&!m_r5->first_initialized)m_r5->recipe["initial_values"].push_back({{"index",i},{"branch","equal_closure_projected_zero"},{"value",r5::decimal(_solution[i])}});''')
    edit(p,'        if (initial.start > initial.end) initial = domain;', '''        bool r5_fallback=initial.start>initial.end;
        if (initial.start > initial.end) initial = domain;''')
    edit(p,'        _solution[i] = random_int64_in_range(initial.start, initial.end);','''        _solution[i] = random_int64_in_range(initial.start, initial.end);
        if(m_r5&&m_r5->active&&!m_r5->first_initialized)m_r5->recipe["initial_values"].push_back({{"index",i},{"branch",r5_fallback?"empty_guided_intersection_fallback_domain":"guided_interval"},{"domain",{std::to_string(domain.start),std::to_string(domain.end)}},{"initial",{std::to_string(initial.start),std::to_string(initial.end)}},{"value",r5::decimal(_solution[i])}});''')
    edit(p,'void ls_sampler::initialize_lit_datas() {','void ls_sampler::initialize_lit_datas() {\n    r5::PhaseTimer literal_timer(m_r5.get(),"literal_statistics_nested_in_initialize");')
    edit(p,'void ls_sampler::initialize_clause_datas() {','void ls_sampler::initialize_clause_datas() {\n    r5::PhaseTimer clause_timer(m_r5.get(),"clause_statistics_nested_in_initialize");')
    edit(p,'bool ls_sampler::ls_sampling() {','bool ls_sampler::ls_sampling() {\n    r5::PhaseTimer search_timer(m_r5.get(),"ls_sampling_inclusive");')
    edit(p,'bool ls_sampler::search() {','bool ls_sampler::search() {\n    if(m_r5&&m_r5->active)m_r5->search_started=!m_r5->initialize_only;')
    edit(p,'        if (_step % 1000 == 0 && TimeElapsed_total() > _cutoff) break;', '''        if(m_r5&&m_r5->active&&(_step&(_step-1))==0)r5_point("power_of_two_step");
        if (_step % 1000 == 0 && TimeElapsed_total() > _cutoff){if(m_r5)m_r5->exit="native_cutoff";break;}''')
    edit(p,'            choose_value_for_pair();\n            up_bool_vars();','''            r5::PhaseTimer reconstruction_timer(m_r5.get(),"reconstruction_nested_in_search");
            if(m_r5)m_r5->exit="first_satisfying_assignment";
            r5_point("first_solution_before_reconstruction");
            choose_value_for_pair();
            up_bool_vars();''')
    edit(p,'    return improve;\n}', '    if(improve&&m_r5&&m_r5->active&&m_r5->first_initialized)r5_point("best_improved");\n    return improve;\n}')
    for function in ['random_walk','update_clause_weight','enter_bool_mode','enter_lia_mode']:
        edit(p,f'void ls_sampler::{function}() {{',f'void ls_sampler::{function}() {{\n    if(m_r5)m_r5->count("{function}");')
    p=z/'smt/smt_context.cpp';edit(p,'                expr_bool_var_map(m_ls_sampler);','''                if(m_ls_sampler->m_r5){m_ls_sampler->m_r5->activate(r5::snapshot(&m,m.last_CDCL_model));if(m_ls_sampler->m_r5->active){auto rem=std::getenv("GUIDED_R5_REMAINING");m_ls_sampler->m_r5->recipe["session_remaining_at_host_entry"]=rem?rem:"not_recorded";}}
                {r5::PhaseTimer literal_timer(m_ls_sampler->m_r5.get(),"expr_bool_var_map");expr_bool_var_map(m_ls_sampler);}''')
    edit(p,'                    return check_finalize(l_true);','''                    if(m_ls_sampler->m_r5){m_ls_sampler->m_r5->exit="sat_delivered";m_ls_sampler->m_r5->flush();}
                    return check_finalize(l_true);''')
    edit(p,'            } catch (const std::exception&) {','''            } catch (const std::exception& error) {
                if(m_ls_sampler->m_r5){m_ls_sampler->m_r5->exit=std::string("exception:")+error.what();m_ls_sampler->m_r5->flush();}''')
    edit(p,'            return check_finalize(l_undef);\n        } else {','''            if(m_ls_sampler->m_r5)m_ls_sampler->m_r5->flush();
            return check_finalize(l_undef);
        } else {''')
    p=z/'smt/smt_context_pp.cpp';p.write_text('#include "ast/ast_smt2_pp.h"\n'+p.read_text())
    edit(p,'            myString = ss.str();','''            myString = ss.str();
            if(sampler->m_r5&&sampler->m_r5->active){std::ostringstream expr;expr<<mk_ismt2_pp(n,m);sampler->m_r5->recipe["literal_identity"].push_back({{"build_order",i},{"native_bool_var",l_curr.var()},{"native_negated",l_curr.sign()},{"expression",expr.str()}});}''')
    for rel in ['HighDiv/src/main/main.cpp','HighDiv/src/sampler/liasampler.cpp','HighDiv/makefile']:shutil.copyfile(source/rel,tree/rel)
    edit(tree/'HighDiv/src/main/main.cpp','else if(mode=="S_cov")argp->guidance_mode=4;', 'else if(mode=="S_cov"||mode=="S_full")argp->guidance_mode=4;else if(mode=="S_support")argp->guidance_mode=5;')
    edit(tree/'HighDiv/makefile',f'-I{ROOT}/include/round4/soft_reference',f'-I{h}')
    print('Generated R5 sources',tree)
if __name__=='__main__':patch(pathlib.Path(sys.argv[1]),sys.argv[2])
