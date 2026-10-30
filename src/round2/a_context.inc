// Included inside namespace smt. A never mutates the native decision variable.
void context::attach_A_guidance(std::shared_ptr<a2::Run> run,char const* leaf) {
    detach_A_guidance();if(!run||run->closed)return;
    auto attach_start=a2::Clock::now();m_A=std::move(run);std::lock_guard<std::recursive_mutex> lock(m_A->mutex);m_A_data=std::make_unique<a2::ContextCache>(m);m_A_local_disabled=false;m_A_snapshot_done=false;++m_A_generation;m_A_call=m_A->backend(reinterpret_cast<uintptr_t>(this),m_A_generation,m_fparams.m_ls_sampling,leaf);
    auto& b=m_A->call(m_A_call);b["bool_vars_before_register"]=get_num_bool_vars();b["bool_vars_after_register"]=get_num_bool_vars();
    b["assertions_before_register"]=get_num_asserted_formulas();b["assertions_after_register"]=get_num_asserted_formulas();
    m_A->event({{"kind","attach"},{"backend_call_id",m_A_call},{"context_id",m_A_call}});
    double binding=a2::seconds(attach_start);b["binding_seconds"]=binding;m_A->direct_seconds+=binding;m_A->binding_seconds+=binding;
    if(m_fparams.m_ls_sampling){b["disabled_reason"]="ccss_rejected";detach_A_guidance();}
}
void context::detach_A_guidance() {
    if(!m_A)return;
    auto run=m_A;std::lock_guard<std::recursive_mutex> lock(run->mutex);
    auto& b=m_A->call(m_A_call);b["end"]=a2::seconds(m_A->begin);b["check_seconds"]=b["end"].get<double>()-b["start"].get<double>();
    b["ordinary_decisions"]=b["funnel"].value("native_ordinary_seen",0ull);
    if(!b.contains("result"))b["result"]="exception_or_early_return";
    m_A->event({{"kind","detach"},{"backend_call_id",m_A_call}});
    m_A_data->tracks.clear();m_A_data->cache.clear();m_A_data->refs.reset();m_A.reset();m_A_call=0;
}
void context::prepare_A_search_epoch(char const* entry) {
    if(!m_A)return;
    std::lock_guard<std::recursive_mutex> lock(m_A->mutex);
    m_A->call(m_A_call)["entry_function"]=entry;
    m_A->event({{"kind","search_entry"},{"backend_call_id",m_A_call},{"entry",entry}});
    if(m_fparams.m_threads>1){m_A->call(m_A_call)["disabled_reason"]="parallel_smt_unsupported";m_A_local_disabled=true;}
}
void context::A_binding_snapshot() {
    if(!m_A||!m_A->diagnostic||m_A_snapshot_done)return;m_A_snapshot_done=true;auto snapshot_start=a2::Clock::now();
    std::lock_guard<std::recursive_mutex> lock(m_A->mutex);
    a2::Json snap=a2::Json::array();a2::InternalView view(m);std::map<std::string,unsigned> selected;
    for(auto const& kv:m_A->index->entries){if(selected.size()>=128)break;selected[kv.first]=snap.size();snap.push_back({{"key",kv.first},{"state","not_internalized"},{"encountered_in_window",false}});}
    auto deadline=a2::Clock::now()+std::chrono::milliseconds(10);bool incomplete=false;unsigned scanned=0;
    for(bool_var v=0;v<get_num_bool_vars();++v){
        if(scanned>=1024||a2::Clock::now()>=deadline){incomplete=true;break;}++scanned;
        if(!bool_var2expr(v))continue;a2::Work work;work.deadline=deadline;auto n=a2::canonical(view,bool_var2expr(v),work);
        if(!n.complete){incomplete=true;continue;}auto it=selected.find(n.key);if(it==selected.end())continue;
        auto value=get_assignment(v);auto& row=snap[it->second];row["var"]=v;row["state"]=value==l_undef?"bound_unassigned":value==l_true?"bound_assigned_true":"bound_assigned_false";row["reason"]="assigned_reason_unknown";
    }
    if(incomplete)for(auto& row:snap)if(row["state"]=="not_internalized")row["state"]="mapping_incomplete";
    m_A->call(m_A_call)["binding_snapshot"]=snap;m_A->call(m_A_call)["binding_snapshot_limit"]=128;m_A->call(m_A_call)["snapshot_native_vars_scanned"]=scanned;double snapshot_elapsed=a2::seconds(snapshot_start);m_A->snapshot_seconds+=snapshot_elapsed;m_A->direct_seconds+=snapshot_elapsed;

}
bool context::apply_A_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase) {
    if(!m_A||m_A_local_disabled||m_A->closed||m_A->direct_disabled)return false;
    std::lock_guard<std::recursive_mutex> lock(m_A->mutex);auto& r=*m_A;
    auto start=a2::Clock::now();struct cost {a2::Run& r;a2::Clock::time_point t;~cost(){double elapsed=a2::seconds(t);r.direct_seconds+=elapsed;r.hot_seconds+=elapsed;if(r.direct_seconds>=r.explicit_remaining)r.direct_disabled=true;}} charge{r,start};
    r.count(m_A_call,"native_ordinary_seen");++r.ordinal;
    bool outside_window=r.ordinal>64;
    if(outside_window){r.count(m_A_call,"outside_decision_window");if(!r.diagnostic||r.ordinal>80)return false;}
    if(!outside_window)r.count(m_A_call,"within_decision_window");
    if(get_assignment(native_var)!=l_undef){r.count(m_A_call,"already_assigned");return false;}
    if(r.direct_seconds>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");return false;}
    expr* e=bool_var2expr(native_var);auto it=m_A_data->cache.find(e);
    if(it==m_A_data->cache.end()){
        a2::Work work;work.deadline=std::min(start+std::chrono::milliseconds(10),start+std::chrono::duration_cast<a2::Clock::duration>(std::chrono::duration<double>(std::max(0.0,r.explicit_remaining-r.direct_seconds))));
        a2::InternalView view(m);auto n=a2::canonical(view,e,work);m_A_data->refs.push_back(e);it=m_A_data->cache.emplace(e,std::move(n)).first;
        r.call(m_A_call)["normalized_atoms"]=r.call(m_A_call)["normalized_atoms"].get<unsigned>()+1;
    }
    auto const& n=it->second;
    unsigned encounter=0;
    if(r.diagnostic){auto& rows=r.call(m_A_call)["native_encounters"];if(rows.is_null())rows=a2::Json::array();encounter=rows.size();rows.push_back({{"ordinal",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"complete",n.complete},{"reason",n.reason},{"outside_window",outside_window},{"score_false",nullptr},{"score_true",nullptr}});}

    if(!n.complete){r.count(m_A_call,n.reason.c_str());auto key=n.reason=="normalization_incomplete"?"incomplete_mapping":"unsupported_normal_form";auto& x=r.call(m_A_call)[key];x=x.get<unsigned>()+1;return false;}
    auto found=r.index->entries.find(n.key);
    if(found==r.index->entries.end()){r.count(m_A_call,"unmapped_reason_unknown");auto& x=r.call(m_A_call)["unmapped"];x=x.get<unsigned>()+1;return false;}
    if(r.diagnostic&&r.call(m_A_call).contains("binding_snapshot"))for(auto& row:r.call(m_A_call)["binding_snapshot"])if(row["key"]==n.key)row["encountered_in_window"]=true;
    r.count(m_A_call,"has_direct_mapping");auto const& entry=found->second;bool exact=entry.original_exact==n.exact;
    auto& match=r.call(m_A_call)[exact?"exact_matches":"normalized_matches"];match=match.get<unsigned>()+1;
    std::map<unsigned,std::pair<uint64_t,uint64_t>> supports[2];unsigned steps=0;
    for(auto const& rule:entry.rules){
        if((++steps&63)==0&&(a2::seconds(start)+r.direct_seconds>=r.explicit_remaining||steps>16384)){r.count(m_A_call,"scoring_incomplete");return false;}
        auto used=r.attempted.find(rule.node);uint64_t u1=0,u0=0;if(used!=r.attempted.end()){u1=used->second.first;u0=used->second.second;}
        auto& dest=supports[rule.phase][rule.node];dest.first|=rule.one&rule.want_one&~u1;dest.second|=rule.zero&rule.want_zero&~u0;
    }
    unsigned score[2]={0,0};for(unsigned p=0;p<2;++p)for(auto const& kv:supports[p])score[p]+=a2::pop(kv.second.first)+a2::pop(kv.second.second);
    if(r.diagnostic){auto& row=r.call(m_A_call)["native_encounters"][encounter];row["score_false"]=score[0];row["score_true"]=score[1];a2::Json masks=a2::Json::array();for(unsigned phase=0;phase<2;++phase)for(auto const& kv:supports[phase])if(kv.second.first||kv.second.second)masks.push_back({{"canonical_phase",phase},{"node",kv.first},{"one",std::to_string(kv.second.first)},{"zero",std::to_string(kv.second.second)}});row["supported_demands"]=masks;}
    if(outside_window){if(score[0]!=score[1])r.count(m_A_call,"outside_window_potential");return false;}
    if(!(score[0]+score[1])){r.count(m_A_call,"no_active_demand");return false;}r.count(m_A_call,"has_current_demand");
    if(score[0]==score[1]){r.count(m_A_call,"score_tie");return false;}
    if(r.suggestions>=4){r.count(m_A_call,"quota_rejected");return false;}
    bool canonical_phase=score[1]>score[0],suggested=canonical_phase!=n.negated;
    bool changed=r.mode!=1&&suggested!=native_phase;
    if(changed&&(r.expired()||a2::seconds(r.begin)>=r.exposure_remaining)){r.count(m_A_call,"exposure_rejected");return false;}
    if(r.direct_seconds+a2::seconds(start)>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");return false;}
    unsigned action=r.actions.size();std::vector<a2::Support> masks;
    for(auto const& kv:supports[canonical_phase])if(kv.second.first||kv.second.second){masks.push_back({kv.first,kv.second.first,kv.second.second});auto& used=r.attempted[kv.first];used.first|=kv.second.first;used.second|=kv.second.second;}
    ++r.suggestions;r.count(m_A_call,suggested==native_phase?"same_phase_suggestions":"different_phase_suggestions");
    if(changed){r.changed=true;r.count(m_A_call,"phase_overrides");}
    effective_phase=r.mode==1?native_phase:suggested;
    a2::Action event;event.query=r.query;event.backend=m_A_call;event.context=m_A_call;event.generation=m_A_generation;event.decision=r.ordinal;event.level=m_scope_lvl;event.var=native_var;event.version=r.version;
    event.native_phase=native_phase;event.suggested_phase=suggested;event.effective_phase=effective_phase;event.changed=changed;event.negated=n.negated;
    event.mapping=exact?"exact_structure":n.kind;event.key=n.key;event.support=std::move(masks);r.actions.push_back(std::move(event));
    m_A_data->tracks.push_back({native_var,e,action,0,false});return true;
}
void context::A_assignment(literal l,bool popped){
    if(!m_A||m_A_data->tracks.empty())return;
    std::lock_guard<std::recursive_mutex> lock(m_A->mutex);
    for(auto& t:m_A_data->tracks)if(t.var==l.var()&&t.e==bool_var2expr(l.var())){
        auto& a=m_A->actions[t.action];if(popped){if(t.active&&t.token){a.popped=true;t.active=false;}}
        else {bool value=!l.sign();if(t.token){if(value==a.effective_phase)++a.reassigned_same;else ++a.reassigned_opposite;}else {t.token=++m_A_assignment_serial;a.token=t.token;a.trail_index=m_assigned_literals.size();}t.active=true;}
    }
}
void context::A_finalize(lbool result){
    if(!m_A)return;std::lock_guard<std::recursive_mutex> lock(m_A->mutex);auto& b=m_A->call(m_A_call);b["result"]=result==l_true?"sat":result==l_false?"unsat":"unknown";b["original_reason_unknown"]=result==l_undef?(m_A_last_exposure?"canceled":last_failure_as_string()):"";
    for(auto const& t:m_A_data->tracks){auto value=t.var<get_num_bool_vars()&&bool_var2expr(t.var)==t.e?get_assignment(t.var):l_undef;m_A->actions[t.action].final_truth=result==l_true&&value!=l_undef?int(value==l_true):-1;}
}
