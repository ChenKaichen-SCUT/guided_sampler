// Included inside namespace smt. A never mutates the native decision variable.
void context::attach_A_guidance(std::shared_ptr<a2::Run> run,char const* leaf) {
    detach_A_guidance();m_S_pending.reset();if(!run||run->closed)return;
    auto attach_start=a2::Clock::now();m_A=std::move(run);std::lock_guard<std::recursive_mutex> lock(m_A->mutex);m_A_data=std::make_unique<a2::ContextCache>(m);m_A_local_disabled=false;m_A_snapshot_done=false;++m_A_generation;m_A_call=m_A->backend(reinterpret_cast<uintptr_t>(this),m_A_generation,m_fparams.m_ls_sampling,leaf);
    if(s3::enabled()&&!m_fparams.m_ls_sampling)m_S=std::make_shared<s3::PendingSemanticSnapshot>(m,m_A,m_A_call,m_A_generation);
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
    if(m_S){S_sample("detach");m_S->flush();if(b["result"]=="sat")m_S_pending=m_S;m_S.reset();}
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
// One arbiter on the ordinary native decision. Never creates or chooses a variable.
bool context::apply_S_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase) {
 if(!m_A||m_A_local_disabled||m_A->closed||m_A->direct_disabled)return false;
 std::lock_guard<std::recursive_mutex> lock(m_A->mutex);auto& r=*m_A;auto const& q=*r.preferences;
 auto start=a2::Clock::now();struct cost {a2::Run& r;a2::Clock::time_point t;~cost(){double x=a2::seconds(t);r.direct_seconds+=x;r.hot_seconds+=x;if(r.direct_seconds>=r.explicit_remaining)r.direct_disabled=true;}} charge{r,start};
 r.count(m_A_call,"native_ordinary_seen");++r.ordinal;
 if(r.ordinal>64){r.count(m_A_call,"outside_decision_window");return false;}r.count(m_A_call,"within_decision_window");
 if(get_assignment(native_var)!=l_undef){r.count(m_A_call,"already_propagated");return false;}
 if(r.direct_seconds>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");return false;}
 a2::Work work;work.deadline=std::min(start+std::chrono::milliseconds(10),start+std::chrono::duration_cast<a2::Clock::duration>(std::chrono::duration<double>(std::max(0.0,r.explicit_remaining-r.direct_seconds))));
 expr* e=bool_var2expr(native_var);a2::InternalView view(m);auto it=m_A_data->cache.find(e);
 if(it==m_A_data->cache.end()){auto n=a2::canonical(view,e,work);m_A_data->refs.push_back(e);it=m_A_data->cache.emplace(e,std::move(n)).first;auto& c=r.call(m_A_call)["normalized_atoms"];c=c.get<unsigned>()+1;}
 auto const& n=it->second;
 if(!n.complete){r.count(m_A_call,"unsupported_mapping");return false;}
 std::string ref_reason;auto ref=a2::r4::evaluate_reference_phase(view,e,q,work,ref_reason);
 if(!ref)r.count(m_A_call,ref_reason.c_str());else r.count(m_A_call,"reference_available");
 a2::r4::PhaseEvidence evidence;auto found=r.index->entries.find(n.key);bool mapped=found!=r.index->entries.end(),exact=mapped&&found->second.original_exact==n.exact;
 a2::Json originals=a2::Json::array();
 if(mapped){r.count(m_A_call,"has_direct_mapping");auto& c=r.call(m_A_call)[exact?"exact_matches":"normalized_matches"];c=c.get<unsigned>()+1;evidence=a2::r4::score_phase_evidence(found->second,work);for(auto const& o:found->second.originals)originals.push_back({{"original_node_id",o.node},{"original_expression_fingerprint",o.fingerprint},{"canonical_negated",o.negated}});}
 else {r.count(m_A_call,"unsupported_mapping");auto& c=r.call(m_A_call)["unmapped"];c=c.get<unsigned>()+1;}
 if(!evidence.complete)r.count(m_A_call,"scoring_incomplete");
 bool active=evidence.support[0]||evidence.support[1]||evidence.block[0]||evidence.block[1];r.count(m_A_call,active?"has_current_demand":"no_active_demand");
 if(mapped&&!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_matched");r.count(m_A_call,r.version?"new_rule_after_first_model":"new_rule_version_zero");if(active)r.count(m_A_call,"new_rule_single_sided_demand");}
 auto best=evidence.best();std::optional<bool> coverage_phase=best?std::optional<bool>(*best!=n.negated):std::nullopt;
 char const* source="native";bool suggested=native_phase,coverage=false;std::vector<a2::Support> masks;std::vector<std::string> new_dedup;
 if(q.policy==a2::r4::Policy::Coverage&&best){
  if(r.suggestions>=4)r.count(m_A_call,"quota_exhausted");
  else {
   bool avoid=evidence.support[0]==evidence.support[1];source=avoid?"avoid_direct_blocker":"coverage_support";
   auto targets=a2::r4::advice_targets(evidence,*best,avoid);
   for(auto const& kv:targets){a2::Support s{kv.first,0,0};for(unsigned d=0;d<2;++d){uint64_t bits=d?kv.second.first:kv.second.second;while(bits){unsigned bit=__builtin_ctzll(bits);bits&=bits-1;auto key=a2::r4::advice_identity(n.key,*best,source,kv.first,bit,d);if(!r.preference_attempted.count(key)){(d?s.one:s.zero)|=uint64_t(1)<<bit;new_dedup.push_back(std::move(key));}}}if(s.one||s.zero)masks.push_back(s);}
   if(!masks.empty()){suggested=*coverage_phase;coverage=true;}else {source="native";r.count(m_A_call,"duplicate_coverage_advice");}
  }
 }
 std::string reference_key=std::to_string(n.key.size())+":"+n.key+":"+std::to_string(ref.value_or(false)!=n.negated);
 if(!coverage&&ref){if(!r.reference_attempted.count(reference_key)){source="inherited_reference";suggested=*ref;}else r.count(m_A_call,"duplicate_reference_advice");}
 a2::Json meta={{"preference_source",source},{"hard_assumptions_hash",q.hard_hash},{"reference_hash",q.reference_hash},{"hard_assumptions_count",q.hard_count},{"reference_count",q.reference_count},{"reference_source_query",q.source_query},
  {"support_true",evidence.support[!n.negated]},{"support_false",evidence.support[n.negated]},{"block_true",evidence.block[!n.negated]},{"block_false",evidence.block[n.negated]},{"evidence_complete",evidence.complete},
  {"reference_phase",ref?a2::Json(*ref):a2::Json(nullptr)},{"coverage_phase",coverage_phase?a2::Json(*coverage_phase):a2::Json(nullptr)},{"coverage_overrode_reference",coverage&&ref&&suggested!=*ref},
  {"new_mapping_rule",n.mapping_rule},{"native_expression_fingerprint",a2::r4::fingerprint(n.exact)},{"originals",originals},{"equivalence_scope","unconditional_integer_declaration_space"},{"target_semantics",coverage?(std::string(source)=="avoid_direct_blocker"?"avoid_known_opposite_not_guaranteed_value":"direct_value_support_not_guaranteed_reach"):"no_coverage_claim"}};
 if(m_S){auto rec=meta;rec.update({{"decision_id",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"canonical_negated",n.negated},{"complete",true},{"reason",ref_reason},{"mapping_atom_slot",m_S->refs.size()}});m_S->refs.push_back(e);m_S->encounters.push_back(std::move(rec));}
 if(std::string(source)=="native")return false;
 bool changed=suggested!=native_phase;
 if(changed&&(r.expired()||a2::seconds(r.begin)>=r.exposure_remaining)){r.count(m_A_call,"exposure_rejected");return false;}
 if(r.direct_seconds+a2::seconds(start)>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");return false;}
 if(coverage){++r.suggestions;for(auto const& k:new_dedup)r.preference_attempted.insert(k);r.count(m_A_call,source);}else {r.reference_attempted.insert(reference_key);r.count(m_A_call,"inherited_reference");}
 r.count(m_A_call,suggested==native_phase?"same_phase_suggestions":"different_phase_suggestions");
 if(changed){r.changed=true;r.count(m_A_call,"phase_overrides");r.count(m_A_call,coverage?"coverage_phase_overrides":"reference_phase_overrides");}
 if(coverage&&!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_advice");if(changed)r.count(m_A_call,"new_rule_override");}
 effective_phase=suggested;unsigned action=r.actions.size();a2::Action event;
 event.query=r.query;event.backend=m_A_call;event.context=m_A_call;event.generation=m_A_generation;event.decision=r.ordinal;event.level=m_scope_lvl;event.var=native_var;event.version=r.version;
 event.native_phase=native_phase;event.suggested_phase=suggested;event.effective_phase=suggested;event.changed=changed;event.negated=n.negated;event.extra=std::move(meta);
 event.mapping=exact?"exact_structure":n.kind;event.key=n.key;event.support=std::move(masks);r.actions.push_back(std::move(event));
 if(m_S){auto a=r.actions.back().json();a["kind"]="suggestion";S_watch(native_var,a);}
 m_A_data->tracks.push_back({native_var,e,action,0,false});return true;
}

bool context::apply_A_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase) {
    if(m_A&&m_A->preferences&&m_A->preferences->policy!=a2::r4::Policy::Legacy)return apply_S_phase_hint(native_var,native_phase,effective_phase);
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
    if(m_S&&r.ordinal<=64)m_S->encounters.push_back({{"decision_id",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"complete",n.complete},{"reason",n.reason},{"ast_kind",is_app(e)?to_app(e)->get_decl_kind():0}});
    if(!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_matched");r.count(m_A_call,r.version?"new_rule_after_first_model":"new_rule_version_zero");}
    unsigned encounter=0;
    if(r.diagnostic){auto& rows=r.call(m_A_call)["native_encounters"];if(rows.is_null())rows=a2::Json::array();encounter=rows.size();rows.push_back({{"ordinal",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"complete",n.complete},{"reason",n.reason},{"outside_window",outside_window},{"score_false",nullptr},{"score_true",nullptr}});}

    if(!n.complete){r.count(m_A_call,n.reason.c_str());auto key=n.reason=="normalization_incomplete"?"incomplete_mapping":"unsupported_normal_form";auto& x=r.call(m_A_call)[key];x=x.get<unsigned>()+1;return false;}
    auto found=r.index->entries.find(n.key);
    if(found==r.index->entries.end()){if(m_S&&s3::select_unmapped(n.key))S_watch(native_var,{{"kind","unmapped"},{"canonical_key",n.key},{"normalization_kind",n.kind},{"canonical_negated",n.negated}});r.count(m_A_call,"unmapped_reason_unknown");auto& x=r.call(m_A_call)["unmapped"];x=x.get<unsigned>()+1;return false;}
    if(r.diagnostic&&r.call(m_A_call).contains("binding_snapshot"))for(auto& row:r.call(m_A_call)["binding_snapshot"])if(row["key"]==n.key)row["encountered_in_window"]=true;
    r.count(m_A_call,"has_direct_mapping");auto const& entry=found->second;bool exact=entry.original_exact==n.exact;
    auto& match=r.call(m_A_call)[exact?"exact_matches":"normalized_matches"];match=match.get<unsigned>()+1;
    if(!n.mapping_rule.empty()){
        a2::Json originals=a2::Json::array();for(auto const& o:entry.originals)originals.push_back({{"original_node_id",o.node},{"original_expression_fingerprint",o.fingerprint},{"canonical_negated",o.negated}});
        if(m_S&&!m_S->encounters.empty()){auto& rec=m_S->encounters.back();rec["mapping_atom_slot"]=m_S->refs.size();m_S->refs.push_back(e);rec["new_mapping_rule"]=n.mapping_rule;rec["originals"]=originals;rec["canonical_negated"]=n.negated;}
        bool demand=false,covered=false,unseen=false;for(auto const& rule:entry.rules){demand|=(rule.want_one|rule.want_zero)!=0;if(rule.node>=r.index->node_states.size())continue;auto const& state=r.index->node_states[rule.node];unseen|=!(state.first|state.second);covered|=(state.first&state.second)!=0;}
        r.count(m_A_call,demand?"new_rule_single_sided_demand":"new_rule_no_active_demand");if(unseen)r.count(m_A_call,"new_rule_two_sides_unseen");if(covered)r.count(m_A_call,"new_rule_has_covered_bits");
        r.event({{"kind","new_mapping_opportunity"},{"backend_call_id",m_A_call},{"decision_id",r.ordinal},{"native_var",native_var},{"native_expression_fingerprint",a2::r4::fingerprint(n.exact)},{"canonical_key",n.key},{"mapping_rule",n.mapping_rule},{"canonical_negated",n.negated},{"originals",originals},{"equivalence_scope","unconditional_integer_declaration_space"},{"coverage_version",r.version},{"single_sided_demand",demand},{"unassigned",true},{"native_selected",true},{"outside_window",outside_window}});
    }
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
    if(!n.mapping_rule.empty())r.count(m_A_call,score[0]==score[1]?"new_rule_support_tie":"new_rule_support_nontie");
    if(score[0]==score[1]){r.count(m_A_call,"score_tie");return false;}
    if(r.suggestions>=4){r.count(m_A_call,"quota_rejected");return false;}
    bool canonical_phase=score[1]>score[0],suggested=canonical_phase!=n.negated;
    bool changed=r.mode!=1&&suggested!=native_phase;
    if(changed&&(r.expired()||a2::seconds(r.begin)>=r.exposure_remaining)){r.count(m_A_call,"exposure_rejected");return false;}
    if(r.direct_seconds+a2::seconds(start)>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");return false;}
    unsigned action=r.actions.size();std::vector<a2::Support> masks;
    for(auto const& kv:supports[canonical_phase])if(kv.second.first||kv.second.second){masks.push_back({kv.first,kv.second.first,kv.second.second});auto& used=r.attempted[kv.first];used.first|=kv.second.first;used.second|=kv.second.second;}
    if(!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_advice");if(changed)r.count(m_A_call,"new_rule_override");}
    ++r.suggestions;r.count(m_A_call,suggested==native_phase?"same_phase_suggestions":"different_phase_suggestions");
    if(changed){r.changed=true;r.count(m_A_call,"phase_overrides");}
    effective_phase=r.mode==1?native_phase:suggested;
    a2::Action event;event.query=r.query;event.backend=m_A_call;event.context=m_A_call;event.generation=m_A_generation;event.decision=r.ordinal;event.level=m_scope_lvl;event.var=native_var;event.version=r.version;
    event.native_phase=native_phase;event.suggested_phase=suggested;event.effective_phase=effective_phase;event.changed=changed;event.negated=n.negated;
    event.extra={{"new_mapping_rule",n.mapping_rule},{"native_expression_fingerprint",a2::r4::fingerprint(n.exact)},{"equivalence_scope","unconditional_integer_declaration_space"}};
    event.mapping=exact?"exact_structure":n.kind;event.key=n.key;event.support=std::move(masks);r.actions.push_back(std::move(event));
    if(m_S){auto a=r.actions.back().json();a["kind"]="suggestion";S_watch(native_var,a);}
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
    S_sample("final_internal_assignment");
    if(!m_A)return;std::lock_guard<std::recursive_mutex> lock(m_A->mutex);auto& b=m_A->call(m_A_call);b["result"]=result==l_true?"sat":result==l_false?"unsat":"unknown";b["original_reason_unknown"]=result==l_undef?(m_A_last_exposure?"canceled":last_failure_as_string()):"";
    for(auto const& t:m_A_data->tracks){auto value=t.var<get_num_bool_vars()&&bool_var2expr(t.var)==t.e?get_assignment(t.var):l_undef;m_A->actions[t.action].final_truth=result==l_true&&value!=l_undef?int(value==l_true):-1;}
}
