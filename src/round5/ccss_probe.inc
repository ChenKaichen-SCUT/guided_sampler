// Definitions compiled into the actual native sampler translation unit.
static r5::J r5_array(Array const* a){r5::J j=r5::J::array();if(a)for(int i=0;i<a->size();++i)j.push_back(a->element_at(i));return j;}
static r5::J r5_numbers(std::vector<__int128_t> const& xs){r5::J j=r5::J::array();for(auto x:xs)j.push_back(r5::decimal(x));return j;}
static r5::J r5_variable(variable const& v,bool initialized){
 r5::J j={{"name",v.var_name},{"is_lia",v.is_lia},{"deleted",v.is_delete},{"low",r5::decimal(v.low_bound)},{"upper",r5::decimal(v.upper_bound)},{"s_low",std::to_string(v.s_lower_bound)},{"s_upper",std::to_string(v.s_upper_bound)},{"in_equal",v.is_in_equal},{"equal_closure",v.in_equal_closure},{"occs_closure",v.in_occs_closure},{"occs",v.occs},{"literals",v.literals},{"literal_clause",v.literal_clause},{"literal_coff",r5_numbers(v.literal_coff)},{"clause_idxs",v.clause_idxs},{"up_bool",v.up_bool}};
 if(initialized&&!v.is_lia)j["score"]=r5::decimal(v.score);return j;
}
static r5::J r5_clause(clause const& c,bool initialized){r5::J j={{"literals",c.literals},{"lia",c.lia_literals},{"bool",c.bool_literals},{"weight",c.weight},{"deleted",c.is_delete}};if(initialized){j["sat_count"]=c.sat_count;}return j;}
r5::J ls_sampler::r5_state(bool initialized)const {
 r5::J vars=r5::J::array(),tmp=r5::J::array(),resolution=r5::J::array(),lits=r5::J::array(),clauses=r5::J::array(),stack=r5::J::array(),intervals=r5::J::array();
 for(auto const& v:_vars)vars.push_back(r5_variable(v,initialized));
 for(auto const& v:_tmp_vars)tmp.push_back(r5_variable(v,false));
 for(auto const& v:_resolution_vars)resolution.push_back(r5_variable(v,false));
 for(auto const& l:_lits){r5::J j={{"index",l.lits_index},{"lia",l.is_lia_lit},{"equal",l.is_equal},{"equal_pair",l.equal_pair}};if(l.lits_index!=0){j["key"]=r5::decimal(l.key);j["pos_var"]=l.pos_coff_var_idx;j["neg_var"]=l.neg_coff_var_idx;j["pos"]=r5_numbers(l.pos_coff);j["neg"]=r5_numbers(l.neg_coff);if(initialized||!l.is_lia_lit)j["delta"]=r5::decimal(l.delta);}lits.push_back(j);}
 for(auto const& c:_clauses)clauses.push_back(r5_clause(c,initialized));
 auto copy=_reconstruct_stack;while(!copy.empty()){stack.push_back(r5_clause(copy.top(),false));copy.pop();}
 for(auto const& i:_vars_initialization_intervals)intervals.push_back({std::to_string(i.start),std::to_string(i.end)});
 r5::J j={{"vars",vars},{"tmp_vars",tmp},{"resolution_vars",resolution},{"lits",lits},{"clauses",clauses},{"reconstruct_stack",stack},{"intervals",intervals},{"pair_x",r5_array(pair_x)},{"pair_y",r5_array(pair_y)},{"pair_x_value",r5_numbers(pair_x_value)},{"pair_y_value",r5_numbers(pair_y_value)},{"bound_lits",_bound_lits},{"lit_appear",_lit_appear},{"bool_var_vec",_bool_var_vec},{"pre_value1",_pre_value_1},{"pre_value2",_pre_value_2},{"name2var",_name2var},{"name2tmp",_name2tmp_var},{"name2resolution",_name2resolution_var},{"num_vars",_num_vars},{"num_lits",_num_lits},{"num_clauses",_num_clauses},{"num_opt",_num_opt},{"use_interval_move",_use_interval_move},{"use_pbs",use_pbs},{"is_pb",is_pb},{"is_idl",is_idl},{"use_swap_small_weight",use_swap_from_from_small_weight},{"best_cost",_best_found_cost},{"rng",r5::rng(mt)}};
 j["max_step"]=_max_step;j["smooth_probability"]=smooth_probability;j["additional_len"]=_additional_len;j["num_bool_lits"]=_num_bool_lits;bool has_lia_literals=false;for(auto const& v:_vars)has_lia_literals|=v.is_lia&&!v.literals.empty();j["lia_var_with_most_lits"]=has_lia_literals?r5::J(_lia_var_idx_with_most_lits):r5::J("not_initialized_not_used");j["consumed_map_copy"]=last_cdcl_model;
 if(initialized){j["solution"]=r5_numbers(_solution);j["unsat"]=r5_array(_unsat_clauses);j["unsat_with_bool"]=r5_array(_contain_bool_unsat_clauses);j["sat_with_false"]=r5_array(_sat_clause_with_false_literal);j["tabulist"]=_tabulist;j["last_move"]=_last_move;j["is_overflow"]=is_overflow;j["lit_unsat"]=_lit_in_unsat_clause_num;j["bool_lit_unsat"]=_bool_lit_in_unsat_clause_num;j["operation_var_indices"]=_operation_var_idx_vec;j["operation_bool_indices"]=_operation_var_idx_bool_vec;j["operation_changes"]=r5_numbers(_operation_change_value_vec);j["updated_literals"]=_updated_literals;j["chosen_bool_vars"]=_is_chosen_bool_var;j["no_improve_bool"]=_no_improve_cnt_bool;j["no_improve_lia"]=_no_improve_cnt_lia;j["best_restart"]=best_found_this_restart;}
 return j;
}
void ls_sampler::r5_begin_replay(r5::J const& recipe,std::string const& id,bool initialize_only){
 if(!m_r5)m_r5.reset(new r5::Probe(recipe.at("seed"),recipe.at("cutoff_seconds"),mt));m_r5->begin_replay(id,initialize_only);
 if(r5::rng(mt)!=recipe.at("R0").get<std::string>())throw std::runtime_error("R0 constructor mismatch");
 _use_interval_move=recipe.at("use_interval_move").get<bool>();
}
void ls_sampler::r5_first_initialize(){
 if(!m_r5||!m_r5->active)return;++m_r5->init_count;
 if(!m_r5->first_initialized){m_r5->first_initialized=true;m_r5->save("initial_values",m_r5->recipe.value("initial_values",r5::J::array()));m_r5->save("R3",r5_state(true));if(m_r5->initialize_only){m_r5->exit="initialization_only";throw r5::InitializationOnly();}}
}
void ls_sampler::r5_point(char const* kind){
 if(!m_r5||!m_r5->active)return;
 m_r5->point({{"kind",kind},{"step",_step},{"outer_step",_outer_layer_step},{"unsat",_unsat_clauses->size()},{"bool_unsat",_contain_bool_unsat_clauses->size()},{"best",_best_found_cost},{"bool_mode",is_in_bool_search},{"overflow_count",_overflow_cnt}});
}
r5::J ls_sampler::r5_solution(){
 r5::J values=r5::J::object();
 for(auto const& kv:_name2tmp_var){std::string name=kv.first,value;print_var_solution(name,value);values[name]=value;}
 return {{"native_check_solution",check_solution()},{"unsat_count",_unsat_clauses->size()},{"overflow",is_overflow},{"tmp_variable_values",values},{"state",r5_state(true)},{"validation_scope","ccss_solution_only_until_saved_converter_restoration_validated"}};
}
