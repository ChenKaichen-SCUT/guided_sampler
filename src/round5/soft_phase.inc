// One arbiter on the ordinary native decision. Never creates or chooses a variable.
bool context::apply_S_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase) {
 if(!m_A||m_A_local_disabled||m_A->closed||m_A->direct_disabled)return false;
 std::lock_guard<std::recursive_mutex> lock(m_A->mutex);auto& r=*m_A;auto const& q=*r.preferences;
 auto start=a2::Clock::now();struct cost {a2::Run& r;a2::Clock::time_point t;~cost(){double x=a2::seconds(t);r.direct_seconds+=x;r.hot_seconds+=x;if(r.direct_seconds>=r.explicit_remaining)r.direct_disabled=true;}} charge{r,start};
 r.count(m_A_call,"native_ordinary_seen");++r.ordinal;
 if(r.ordinal>64){r.count(m_A_call,"outside_decision_window");return false;}r.count(m_A_call,"within_decision_window");
 a2::r5::DecisionAudit audit(r,m_A_call,native_var,native_phase);
 if(get_assignment(native_var)!=l_undef){r.count(m_A_call,"already_propagated");audit.reason("already_propagated");return false;}
 if(r.direct_seconds>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");audit.reason("cost_rejected");return false;}
 a2::Work work;work.deadline=std::min(start+std::chrono::milliseconds(10),start+std::chrono::duration_cast<a2::Clock::duration>(std::chrono::duration<double>(std::max(0.0,r.explicit_remaining-r.direct_seconds))));
 expr* e=bool_var2expr(native_var);a2::InternalView view(m);auto it=m_A_data->cache.find(e);
 if(it==m_A_data->cache.end()){auto n=a2::canonical(view,e,work);m_A_data->refs.push_back(e);it=m_A_data->cache.emplace(e,std::move(n)).first;auto& c=r.call(m_A_call)["normalized_atoms"];c=c.get<unsigned>()+1;}
 auto const& n=it->second;
 if(!n.complete){r.count(m_A_call,"unsupported_mapping");audit.reason("unsupported_mapping");return false;}
 std::string ref_reason;auto ref=a2::r4::evaluate_reference_phase(view,e,q,work,ref_reason);
 if(!ref)r.count(m_A_call,ref_reason.c_str());else r.count(m_A_call,"reference_available");
 a2::r4::PhaseEvidence evidence;auto found=r.index->entries.find(n.key);bool mapped=found!=r.index->entries.end(),exact=mapped&&found->second.original_exact==n.exact;
 a2::Json originals=a2::Json::array();
 if(mapped){r.count(m_A_call,"has_direct_mapping");auto& c=r.call(m_A_call)[exact?"exact_matches":"normalized_matches"];c=c.get<unsigned>()+1;evidence=a2::r4::score_phase_evidence(found->second,work);for(auto const& o:found->second.originals)originals.push_back({{"original_node_id",o.node},{"original_expression_fingerprint",o.fingerprint},{"canonical_negated",o.negated}});}
 else {r.count(m_A_call,"unsupported_mapping");auto& c=r.call(m_A_call)["unmapped"];c=c.get<unsigned>()+1;}
 if(!evidence.complete)r.count(m_A_call,"scoring_incomplete");
 bool active=evidence.support[0]||evidence.support[1]||evidence.block[0]||evidence.block[1];r.count(m_A_call,active?"has_current_demand":"no_active_demand");
 if(mapped&&!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_matched");r.count(m_A_call,r.version?"new_rule_after_first_model":"new_rule_version_zero");if(active)r.count(m_A_call,"new_rule_single_sided_demand");}
 auto raw_best=evidence.best();
 auto policy=q.policy==a2::r4::Policy::Coverage?a2::r5::CoveragePolicy::Full:q.policy==a2::r4::Policy::SupportOnly?a2::r5::CoveragePolicy::SupportOnly:a2::r5::CoveragePolicy::ReferenceOnly;
 auto choice=a2::r5::choose_coverage(evidence,policy);
 auto best=choice?std::optional<bool>(choice->phase):std::nullopt;std::optional<bool> coverage_phase=raw_best?std::optional<bool>(*raw_best!=n.negated):std::nullopt;
 char const* source="native";bool suggested=native_phase,coverage=false;std::vector<a2::Support> masks;std::vector<std::string> new_dedup;
 if(best){
  if(r.suggestions>=4)r.count(m_A_call,"quota_exhausted");
  else {
   bool avoid=evidence.support[0]==evidence.support[1];source=avoid?"avoid_direct_blocker":"coverage_support";
   auto targets=a2::r4::advice_targets(evidence,*best,avoid);
   for(auto const& kv:targets){a2::Support s{kv.first,0,0};for(unsigned d=0;d<2;++d){uint64_t bits=d?kv.second.first:kv.second.second;while(bits){unsigned bit=__builtin_ctzll(bits);bits&=bits-1;auto key=a2::r4::advice_identity(n.key,*best,source,kv.first,bit,d);if(!r.preference_attempted.count(key)){(d?s.one:s.zero)|=uint64_t(1)<<bit;new_dedup.push_back(std::move(key));}}}if(s.one||s.zero)masks.push_back(s);}
   if(!masks.empty()){suggested=*coverage_phase;coverage=true;}else {source="native";r.count(m_A_call,"duplicate_coverage_advice");}
  }
 }
 std::string reference_key=std::to_string(n.key.size())+":"+n.key+":"+std::to_string(ref.value_or(false)!=n.negated);

 if(audit.enabled){
  auto candidate=raw_best?a2::r4::advice_targets(evidence,*raw_best,evidence.support[0]==evidence.support[1]):a2::r4::Masks{};unsigned untried=0;auto raw_source=evidence.support[0]==evidence.support[1]?"avoid_direct_blocker":"coverage_support";a2::Json audit_targets=a2::Json::array();
  for(auto const& kv:candidate)for(unsigned d=0;d<2;++d){uint64_t bits=d?kv.second.first:kv.second.second;while(bits){unsigned bit=__builtin_ctzll(bits);bits&=bits-1;auto key=a2::r4::advice_identity(n.key,*raw_best,raw_source,kv.first,bit,d);bool seen=r.preference_attempted.count(key);untried+=!seen;if(audit_targets.size()<4096)audit_targets.push_back({{"node",kv.first},{"bit",bit},{"desired",d},{"already_attempted",seen}});else audit.data["target_buffer_overflow"]=true;}}
  bool fallback=ref&&!r.reference_attempted.count(reference_key)?*ref:native_phase;
  bool would_change=raw_best&&((*raw_best!=n.negated)!=native_phase);
  bool exposure_ok=!would_change||!(r.sticky.load()||a2::seconds(r.begin)>=r.exposure_remaining);
  audit.data.update({{"canonical_key",n.key},{"negated",n.negated},{"support_false",evidence.support[n.negated]},{"support_true",evidence.support[!n.negated]},{"block_false",evidence.block[n.negated]},{"block_true",evidence.block[!n.negated]},{"evidence_complete",evidence.complete},{"reference_phase",ref?a2::Json(*ref):a2::Json(nullptr)},{"raw_preferred_kind",raw_best?a2::Json(raw_source):a2::Json(nullptr)},{"raw_preferred_phase",raw_best?a2::Json(*raw_best!=n.negated):a2::Json(nullptr)},{"unattempted_demand_count",untried},{"local_fallback_phase",fallback},{"unassigned",true},{"exposure_guard_at_audit",exposure_ok},{"cost_guard_at_audit",r.direct_seconds+a2::seconds(start)<r.explicit_remaining},{"targets",audit_targets},{"policy_suppressed_avoid",policy==a2::r5::CoveragePolicy::SupportOnly&&raw_best&&!best}});
  audit.reason(r.suggestions>=4&&best?"quota_exhausted":raw_best&&!untried?"all_targets_attempted":!best?"policy_or_tie_fallback":"candidate");
 }
 if(!coverage&&ref){if(!r.reference_attempted.count(reference_key)){source="inherited_reference";suggested=*ref;}else r.count(m_A_call,"duplicate_reference_advice");}
 a2::Json meta={{"preference_source",source},{"hard_assumptions_hash",q.hard_hash},{"reference_hash",q.reference_hash},{"hard_assumptions_count",q.hard_count},{"reference_count",q.reference_count},{"reference_source_query",q.source_query},
  {"support_true",evidence.support[!n.negated]},{"support_false",evidence.support[n.negated]},{"block_true",evidence.block[!n.negated]},{"block_false",evidence.block[n.negated]},{"evidence_complete",evidence.complete},
  {"reference_phase",ref?a2::Json(*ref):a2::Json(nullptr)},{"coverage_phase",coverage_phase?a2::Json(*coverage_phase):a2::Json(nullptr)},{"coverage_overrode_reference",coverage&&ref&&suggested!=*ref},
  {"new_mapping_rule",n.mapping_rule},{"native_expression_fingerprint",a2::r4::fingerprint(n.exact)},{"originals",originals},{"equivalence_scope","unconditional_integer_declaration_space"},{"target_semantics",coverage?(std::string(source)=="avoid_direct_blocker"?"avoid_known_opposite_not_guaranteed_value":"direct_value_support_not_guaranteed_reach"):"no_coverage_claim"}};
 if(m_S){auto rec=meta;rec.update({{"decision_id",r.ordinal},{"native_var",native_var},{"native_phase",native_phase},{"canonical_key",n.key},{"canonical_negated",n.negated},{"complete",true},{"reason",ref_reason},{"mapping_atom_slot",m_S->refs.size()}});m_S->refs.push_back(e);m_S->encounters.push_back(std::move(rec));}
 if(std::string(source)=="native")return false;
 bool changed=suggested!=native_phase;
 if(changed&&(r.expired()||a2::seconds(r.begin)>=r.exposure_remaining)){r.count(m_A_call,"exposure_rejected");audit.reason("exposure_rejected");return false;}
 if(r.direct_seconds+a2::seconds(start)>=r.explicit_remaining){r.count(m_A_call,"cost_rejected");audit.reason("cost_rejected");return false;}
 if(coverage){++r.suggestions;for(auto const& k:new_dedup)r.preference_attempted.insert(k);r.count(m_A_call,source);}else {r.reference_attempted.insert(reference_key);r.count(m_A_call,"inherited_reference");}
 r.count(m_A_call,suggested==native_phase?"same_phase_suggestions":"different_phase_suggestions");
 if(changed){r.changed=true;r.count(m_A_call,"phase_overrides");r.count(m_A_call,coverage?"coverage_phase_overrides":"reference_phase_overrides");}
 if(coverage&&!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_advice");if(changed)r.count(m_A_call,"new_rule_override");}
 if(audit.enabled){audit.data.update({{"actual_source",source},{"actual_phase",suggested},{"changed_vs_native",changed},{"changed_vs_local_fallback",suggested!=audit.data["local_fallback_phase"].get<bool>()}});audit.reason("applied");}
 effective_phase=suggested;unsigned action=r.actions.size();a2::Action event;
 event.query=r.query;event.backend=m_A_call;event.context=m_A_call;event.generation=m_A_generation;event.decision=r.ordinal;event.level=m_scope_lvl;event.var=native_var;event.version=r.version;
 event.native_phase=native_phase;event.suggested_phase=suggested;event.effective_phase=suggested;event.changed=changed;event.negated=n.negated;event.extra=std::move(meta);
 event.mapping=exact?"exact_structure":n.kind;event.key=n.key;event.support=std::move(masks);r.actions.push_back(std::move(event));
 if(m_S){auto a=r.actions.back().json();a["kind"]="suggestion";S_watch(native_var,a);}
 m_A_data->tracks.push_back({native_var,e,action,0,false});return true;
}
