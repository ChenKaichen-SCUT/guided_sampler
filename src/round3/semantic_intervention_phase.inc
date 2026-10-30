    // Experimental intervention is entirely absent from the frozen D1 library.
    auto& micro=d3::state();
    if(micro.enabled){
        if(!m_A||m_A->closed||m_fparams.m_ls_sampling)return false;
        std::lock_guard<std::recursive_mutex> lock(m_A->mutex);auto& r=*m_A;
        r.count(m_A_call,"native_ordinary_seen");++r.ordinal;
        if(micro.fired||r.ordinal>64)return false;
        expr* e=bool_var2expr(native_var);a2::InternalView view(m);a2::Work work;
        work.deadline=a2::Clock::now()+std::chrono::milliseconds(10);auto n=a2::canonical(view,e,work);
        if(m_S)m_S->encounters.push_back({{"decision_id",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"complete",n.complete},{"reason",n.reason}});
        if(!n.complete||n.key!=micro.spec["canonical_key"]||s3::text(e,m)!=micro.spec["actual_atom"]["expr"]||get_assignment(native_var)!=l_undef)return false;
        if(r.index->entries.find(n.key)==r.index->entries.end())return false;
        if(r.version!=micro.spec["coverage_version"])throw std::runtime_error("D3 coverage mismatch");
        micro.fired=true;bool desired=micro.spec["suggested_phase"],activate=micro.cell[1]=='1';
        a2::Action a;a.query=r.query;a.backend=m_A_call;a.context=m_A_call;a.generation=m_A_generation;a.decision=r.ordinal;a.level=m_scope_lvl;a.var=native_var;a.version=r.version;a.native_phase=native_phase;a.suggested_phase=desired;a.effective_phase=native_phase;a.changed=false;a.negated=n.negated;a.mapping="D3_existing_atom_verified_print_and_original_key";a.key=n.key;
        for(auto const& s:micro.spec["support"])a.support.push_back({s["node"].get<unsigned>(),std::stoull(s["desired_one_mask"].get<std::string>()),std::stoull(s["desired_zero_mask"].get<std::string>())});
        ++r.suggestions;unsigned action=r.actions.size();r.actions.push_back(a);m_A_data->tracks.push_back({native_var,e,action,0,false});if(m_S){auto j=a.json();j["kind"]="D3_checkpoint";j["cell"]=micro.cell;S_watch(native_var,j);}
        auto rng_before=d3::trace_size("GUIDED_TEST_RNG_TRACE"),decisions_before=d3::trace_size("HIGHDIV_NATIVE_DECISION_TRACE");unsigned trail_before=m_assigned_literals.size();auto t=a2::Clock::now();unsigned before=get_num_bool_vars(),assertions=get_num_asserted_formulas();bool relevant_before=is_relevant(e);
        if(activate){mark_as_relevant(native_var);if(!inconsistent())propagate();}
        bool assigned=get_assignment(native_var)!=l_undef,conflict=inconsistent(),cancel=get_cancel_flag();micro.handoff=assigned||conflict||cancel;
        if(!micro.handoff){effective_phase=micro.cell[0]=='A'?desired:native_phase;bool changed=effective_phase!=native_phase;r.actions[action].effective_phase=effective_phase;r.actions[action].changed=changed;if(changed){r.changed=true;r.count(m_A_call,"phase_overrides");}}
        if(m_S&&!m_S->watches.empty()){auto& j=m_S->watches.back().action;j["effective_phase"]=r.actions[action].effective_phase;j["phase_changed"]=r.actions[action].changed;j["propagated_before_test_decision"]=assigned;j["conflict_before_test_decision"]=conflict;}
        r.event({{"kind","D3_checkpoint"},{"cell",micro.cell},{"query_id",r.query},{"historical_decision_id",micro.spec["decision_id"]},{"actual_decision_id",r.ordinal},{"backend_call_id",m_A_call},{"native_var",native_var},{"actual_var",native_var},{"native_phase",native_phase},{"suggested_phase",desired},{"effective_phase",r.actions[action].effective_phase},{"phase_changed",r.actions[action].changed},{"activation",activate},{"relevant_before",relevant_before},{"relevant_after_activation",is_relevant(e)},{"activation_and_native_propagation_seconds",a2::seconds(t)},{"bool_vars_before",before},{"bool_vars_after",get_num_bool_vars()},{"assertions_before",assertions},{"assertions_after",get_num_asserted_formulas()},{"propagated_before_test_decision",assigned},{"conflict_before_test_decision",conflict},{"cancelled",cancel},{"scope_level",m_scope_lvl},{"trail_size",m_assigned_literals.size()},{"trail_size_before",trail_before},{"native_trace_bytes_before",decisions_before},{"rng_trace_bytes_before",rng_before},{"process_thread_count",d3::task_count()},{"state_relation","same_query_not_same_state"},{"fork_used",false}});
        return !micro.handoff;
    }
