#pragma once
// Included after Run, within a2. Only bounded first-window records, no solver work.
namespace r5 {
struct DecisionAudit {
 Run& run;bool enabled;Json data;
 DecisionAudit(Run& r,unsigned backend,unsigned var,bool native):run(r),enabled(std::getenv("GUIDED_R5_DECISION_AUDIT")!=nullptr){
  if(!enabled)return;
  unsigned support=0,avoid=0;for(auto const& a:r.actions){auto s=a.extra.value("preference_source","");support+=s=="coverage_support";avoid+=s=="avoid_direct_blocker";}
  data={{"kind","round5_decision_audit"},{"query_id",r.query},{"backend_call_id",backend},{"decision_id",r.ordinal},{"coverage_version",r.version},{"native_var",var},{"native_phase",native},{"quota_before",r.suggestions},{"prior_support",support},{"prior_avoid",avoid},{"reason","early_exit"},{"actual_source","native"},{"actual_phase",native},{"changed_vs_native",false},{"evidence_complete",nullptr},{"unattempted_demand_count",nullptr},{"local_fallback_phase",native}};
 }
 void reason(char const* s){if(enabled)data["reason"]=s;}
 ~DecisionAudit(){if(enabled){data["quota_after"]=run.suggestions;run.event(std::move(data));}}
};
}
