#pragma once
#include "observation.hpp"
#include "a_host_view.hpp"
#include "z3_a_guidance.h"
#include <fstream>
namespace guided {
class AGuidanceBridge {
public:
 OriginalAst ast;std::shared_ptr<a2::Index> index=std::make_shared<a2::Index>();
 unsigned mode;double cost=0,budget=45,exposure=0,exposure_budget=45;bool disabled=false;std::string disabled_reason;
 std::map<std::string,double> costs;std::map<std::string,uint64_t> mapping_counts;
 std::vector<std::vector<std::pair<a2::Entry*,unsigned>>> reverse;
 std::vector<std::pair<uint64_t,uint64_t>> known;
 Json current=Json::object(),pending_outcomes=Json::array();unsigned current_query=0;double last_observer=0,last_update=0;unsigned entries_updated=0;
 std::ofstream requests,backends,actions,skips,catalog,outcome_log,ledger,lifecycle;
 uint64_t tail_models=0,tail_unknown=0;double tail_cdcl=0,tail_ccss=0;
 AGuidanceBridge(z3::expr const& formula,unsigned md,double wall,std::string const& dir):ast(formula),mode(md),reverse(ast.nodes.size()),known(ast.nodes.size()),
 requests(dir+"/a_requests.jsonl"),backends(dir+"/a_backend_calls.jsonl"),actions(dir+"/a_actions.jsonl"),skips(dir+"/a_skips_summary.jsonl"),catalog(dir+"/a_atom_catalog.jsonl"),outcome_log(dir+"/a_outcomes.jsonl"),ledger(dir+"/cost_ledger.jsonl"),lifecycle(dir+"/lifecycle.jsonl") {
  (void)wall;std::ofstream(dir+"/guidance_events.jsonl");std::ofstream(dir+"/target_catalog.jsonl");
  index->node_states.resize(ast.nodes.size());
  auto start=Clock::now();a2::HostView view;
  auto add=[&](a2::Norm const& norm,unsigned node,bool phase,uint64_t one,uint64_t zero){
   auto& entry=index->entries[norm.key];if(entry.original_exact.empty())entry.original_exact=norm.exact;
   for(auto const& r:entry.rules)if(r.node==node&&r.phase==phase&&r.one==one&&r.zero==zero)return;
   unsigned k=entry.rules.size();entry.rules.push_back({node,phase,one,zero});reverse[node].push_back({&entry,k});known[node].first|=one;known[node].second|=zero;
  };
  for(unsigned i=0;i<ast.nodes.size();++i){
   if(seconds(start)>=budget){disable("explicit_budget_during_index_build");break;}
   auto const& node=ast.nodes[i];auto e=node.e;if(!node.boolean||node.literal)continue;
   auto raw=e;while(raw.is_not())raw=raw.arg(0);
   if(raw.is_and()||raw.is_or()||raw.is_ite()||raw.is_true()||raw.is_false())continue;
   a2::Work work;auto norm=a2::canonical(view,e,work);if(!norm.complete){++mapping_counts[norm.reason];continue;}
   index->entries[norm.key].originals.push_back({i,a2::r4::fingerprint(norm.exact),norm.exact,norm.negated});
   ++mapping_counts[norm.kind];add(norm,i,!norm.negated,1,0);add(norm,i,norm.negated,0,1);
   if(e.is_eq()&&e.arg(0).is_int())for(unsigned side=0;side<2;++side){auto term=e.arg(side),val=e.arg(1-side);if(!val.is_numeral())continue;unsigned n=ast.ids.at(term.id());if(ast.nodes[n].literal)continue;auto bits=low64(numeral(val));add(norm,n,!norm.negated,bits,~bits);}
  }
  for(auto const& kv:index->entries){Json rules=Json::array();for(auto const& r:kv.second.rules)rules.push_back({{"node",r.node},{"phase",r.phase},{"known_one",std::to_string(r.one)},{"known_zero",std::to_string(r.zero)}});Json originals=Json::array();for(auto const& o:kv.second.originals)originals.push_back({{"node",o.node},{"fingerprint",o.fingerprint},{"exact",o.exact},{"canonical_negated",o.negated}});catalog<<Json({{"key",kv.first},{"rules",rules},{"originals",originals}}).dump()<<'\n';}catalog.flush();
  charge("index_build_seconds",seconds(start));
  std::ofstream summary(dir+"/a_index_summary.json");summary<<Json({{"entries",index->entries.size()},{"normalization",mapping_counts},{"index_build_seconds",costs["index_build_seconds"]},{"disabled",disabled},{"b_constructed",false}}).dump(2)<<'\n';
 }
 static double seconds(Clock::time_point start){return std::chrono::duration<double>(Clock::now()-start).count();}
 void charge(std::string const& category,double x){cost+=x;costs[category]+=x;}
 void disable(std::string reason){if(disabled)return;disabled=true;disabled_reason=std::move(reason);lifecycle<<Json({{"kind","disabled"},{"reason",disabled_reason},{"cost",cost},{"exposure",exposure},{"last_online_version",ast.version},{"guidance_disabled_but_native_history_retained",true}}).dump()<<'\n';lifecycle.flush();}
 bool observing(){if(!disabled&&cost>=budget)disable("explicit_budget");return !disabled;}
 void record_observer(double t){last_observer=t;charge("observer_seconds",t);}
 void commit(Evaluation const& ev){
  if(disabled)return;auto start=Clock::now();if(index->active)throw std::runtime_error("A index modified during active check");
  // Incremental total and mappable counts: only nodes changed by committed observations.
  for(unsigned n:ev.changed){auto const& old=ast.nodes[n];auto v=low64(*ev.values[n])&old.mask();auto s0=old.seen0|(~v&old.mask()),s1=old.seen1|v;
   index->single_sided+=std::popcount(s0^s1)-std::popcount(old.seen0^old.seen1);
   auto before=std::popcount((old.seen0&~old.seen1)&known[n].first)+std::popcount((old.seen1&~old.seen0)&known[n].second);
   auto after=std::popcount((s0&~s1)&known[n].first)+std::popcount((s1&~s0)&known[n].second);index->mappable_targets+=after-before;
  }
  ast.commit(ev);entries_updated=0;
  for(unsigned n:ev.changed){if(cost+seconds(start)>=budget){disable("explicit_budget_during_update");break;}auto const& node=ast.nodes[n];for(auto [entry,k]:reverse[n]){auto& r=entry->rules[k];r.want_one=node.seen0&~node.seen1&node.mask();r.want_zero=node.seen1&~node.seen0&node.mask();++entries_updated;}}
  for(unsigned n:ev.changed)index->node_states[n]={ast.nodes[n].seen0,ast.nodes[n].seen1};
  index->version=ast.version;index->updates=entries_updated;last_update=seconds(start);charge("index_update_seconds",last_update);
 }
 void prepare(z3::solver& solver,unsigned query){
  auto start=Clock::now();current_query=query;current=Json::object();pending_outcomes=Json::array();if(!observing()||exposure>=exposure_budget){if(!disabled)disable("exposure_budget");requests<<Json({{"query_id",query},{"coverage_version",ast.version},{"single_sided_bits",nullptr},{"A_mappable_targets",nullptr},{"index_entries",index->entries.size()},{"entries_updated",0},{"request_register_seconds",0},{"request_size_bytes",0},{"has_request",false},{"disabled_reason",disabled_reason}}).dump()<<'\n';requests.flush();return;}
  bool diagnostic=std::getenv("GUIDED_A_DIAGNOSTIC")!=nullptr;
  auto reg=Clock::now();Z3_solver_set_A_guidance(solver.ctx(),solver,&index,query,ast.version,mode>2?2:mode,std::max(0.0,exposure_budget-exposure),std::max(0.0,budget-cost),diagnostic);solver.ctx().check_error();double register_time=seconds(reg);charge("request_register_seconds",register_time);
  requests<<Json({{"query_id",query},{"coverage_version",ast.version},{"single_sided_bits",index->single_sided},{"A_mappable_targets",index->mappable_targets},{"index_entries",index->entries.size()},{"entries_updated",entries_updated},{"observer_seconds",last_observer},{"index_build_seconds",costs["index_build_seconds"]},{"index_update_seconds",last_update},{"request_register_seconds",register_time},{"request_size_bytes",sizeof(void*)+4*sizeof(unsigned)+2*sizeof(double)},{"has_request",true},{"disabled_reason",""}}).dump()<<'\n';requests.flush();charge("request_log_seconds",seconds(start)-register_time);
 }
 Json end_check(z3::solver& solver){
  if(disabled)return Json::object();auto start=Clock::now();current=Json::parse(Z3_solver_get_A_guidance_stats(solver.ctx(),solver));Z3_solver_clear_A_guidance(solver.ctx(),solver);solver.ctx().check_error();
  for(auto key:{"binding_seconds","hot_callback_seconds","route_metadata_seconds","diagnostic_snapshot_seconds","exposure_guard_seconds"})charge(key,current.value(key,0.0));
  for(auto b:current.value("backend_calls",Json::array())){backends<<b.dump()<<'\n';skips<<Json({{"query_id",current_query},{"backend_call_id",b["backend_call_id"]},{"funnel",b["funnel"]},{"outside_window_potential",nullptr}}).dump()<<'\n';}
  for(auto e:current.value("actions",Json::array()))actions<<e.dump()<<'\n';
  for(auto e:current.value("lifecycle",Json::array())){e["query_id"]=current_query;lifecycle<<e.dump()<<'\n';}
  // Stage chain is once per external check, with lightweight names, no formula dumps.
  backends<<Json({{"query_id",current_query},{"kind","tactic_stages"},{"stages",current.value("stages",Json::array())}}).dump()<<'\n';
  backends.flush();actions.flush();skips.flush();lifecycle.flush();charge("diagnostic_serialization_seconds",seconds(start));return current;
 }
 void query_finished(std::string const& source,unsigned query,double check_time,std::string const& result,Json const& stats){
  auto log_start=Clock::now();bool was_disabled=disabled;
  if(source=="CDCL"&&stats.value("intervened_check",false))exposure+=check_time;
  if(stats.value("exposure_limit",false)||exposure>=exposure_budget)disable("guidance_exposure_limit");
  if(cost>=budget||stats.value("explicit_limit",false))disable("explicit_budget");
  if(was_disabled){if(source=="CDCL")tail_cdcl+=check_time;else tail_ccss+=check_time;if(result=="unknown")++tail_unknown;}
  ledger<<Json({{"query_id",query},{"source",source},{"explicit_seconds",cost},{"categories",costs},{"intervened_check_exposure_seconds",exposure},{"this_check_exposure",stats.value("intervened_check",false)?check_time:0.0},{"exposure_requested_limit",stats.value("requested_exposure_limit",0.0)},{"exposure_overrun",stats.value("intervened_check",false)?std::max(0.0,check_time-stats.value("requested_exposure_limit",0.0)):0.0},{"disabled",disabled},{"disabled_reason",disabled_reason},{"tail_cdcl_seconds",tail_cdcl},{"tail_ccss_seconds",tail_ccss},{"tail_unknown",tail_unknown}}).dump()<<'\n';ledger.flush();if(!was_disabled)charge("cost_ledger_log_seconds",seconds(log_start));
 }
 Json outcomes(Evaluation const& ev)const {
  Json result=Json::array();for(auto const& action:current.value("actions",Json::array())){Json targets=Json::array();for(auto const& support:action["support"]){unsigned n=support["node"];uint64_t one=std::stoull(support["desired_one_mask"].get<std::string>()),zero=std::stoull(support["desired_zero_mask"].get<std::string>());bool reached=ev.values[n].has_value();uint64_t v=reached?low64(*ev.values[n]):0;auto const& node=ast.nodes[n];uint64_t hit1=reached?(one&v):0,hit0=reached?(zero&~v):0,new1=hit1&~node.seen1,new0=hit0&~node.seen0;targets.push_back({{"node",n},{"reached",reached},{"desired_one_mask",std::to_string(one)},{"desired_zero_mask",std::to_string(zero)},{"hit_one_mask",std::to_string(hit1)},{"hit_zero_mask",std::to_string(hit0)},{"new_one_mask",std::to_string(new1)},{"new_zero_mask",std::to_string(new0)},{"new_covered_for_targets",std::popcount(new1&node.seen0)+std::popcount(new0&node.seen1)}});}result.push_back({{"decision_id",action["decision_id"]},{"backend_call_id",action["backend_call_id"]},{"phase_changed",action["phase_changed"]},{"targets",targets}});}return result;
 }
 void formal_record(Json const& rec){auto log_start=Clock::now();if(disabled)++tail_models;if(rec["source"]=="CDCL"&&rec["query"]==current_query)outcome_log<<Json({{"query_id",current_query},{"formal_index",rec["formal_index"]},{"formal_model",true},{"outcomes",pending_outcomes},{"model_new_observed",rec["new_observed"]},{"model_new_covered",rec["new_covered"]}}).dump()<<'\n';outcome_log.flush();if(!disabled)charge("outcome_log_seconds",seconds(log_start));}
};
}
