#pragma once
#include "util/a_shared.hpp"
#include <nlohmann/json.hpp>
#include <mutex>
#include <thread>
namespace a2 {
using Json=nlohmann::json;
struct Action {
 unsigned query,backend,context,generation,decision,level,var,version;
 bool native_phase,suggested_phase,effective_phase,changed,negated,popped=false;
 std::string mapping,key;std::vector<Support> support;
 uint64_t token=0;unsigned trail_index=0,reassigned_same=0,reassigned_opposite=0;
 int final_truth=-1;
 Json json()const {Json masks=Json::array();for(auto const& s:support)masks.push_back({{"node",s.node},{"desired_one_mask",std::to_string(s.one)},{"desired_zero_mask",std::to_string(s.zero)}});
 return {{"query_id",query},{"backend_call_id",backend},{"context_id",context},{"context_generation",generation},{"decision_id",decision},{"level",level},{"native_var",var},{"actual_var",var},{"native_phase",native_phase},{"suggested_phase",suggested_phase},{"effective_phase",effective_phase},{"phase_changed",changed},{"would_override",suggested_phase!=native_phase},{"mapping_kind",mapping},{"canonical_key",key},{"literal_negated",negated},{"support",masks},{"coverage_version",version},{"trailed_assignment_popped",popped},{"reassigned_same",reassigned_same},{"reassigned_opposite",reassigned_opposite},{"assignment_token",token},{"trail_index",trail_index},{"final_atom_truth",final_truth<0?Json(nullptr):Json(final_truth!=0)}};}
};
struct Run {
 std::shared_ptr<const Index> index;unsigned query,version,mode,diagnostic;uintptr_t solver_id=0;
 Clock::time_point begin=Clock::now();bool started=false,closed=false;
 std::atomic<bool> changed{false},sticky{false},direct_disabled{false};double exposure_remaining,explicit_remaining,direct_seconds=0,hot_seconds=0,binding_seconds=0,stage_seconds=0,snapshot_seconds=0;std::atomic<uint64_t> guard_nanoseconds{0};
 std::recursive_mutex mutex;unsigned ordinal=0,suggestions=0,next_id=0;
 std::map<unsigned,std::pair<uint64_t,uint64_t>> attempted;
 Json backends=Json::array(),lifecycle=Json::array(),stages=Json::array();std::vector<Action> actions;
 std::map<std::thread::id,std::vector<unsigned>> parents;
 std::string route,route_reason;
 Run(std::shared_ptr<Index> p,unsigned q,unsigned v,unsigned md,double exposure,double explicit_cost,unsigned diag):index(p),query(q),version(v),mode(md),diagnostic(diag),exposure_remaining(exposure),explicit_remaining(explicit_cost){++p->active;}
 ~Run(){close();}
 void close(){std::lock_guard<std::recursive_mutex> lock(mutex);if(!closed){closed=true;if(index)--const_cast<Index&>(*index).active;}}
 void start(){std::lock_guard<std::recursive_mutex> lock(mutex);if(!started){begin=Clock::now();started=true;}}
 bool expired(){if(sticky)return true;if(!changed)return false;auto t=Clock::now();bool over=std::chrono::duration<double>(t-begin).count()>=exposure_remaining;if(over)sticky=true;guard_nanoseconds.fetch_add(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-t).count());return over;}
 unsigned parent(){auto& p=parents[std::this_thread::get_id()];return p.empty()?0:p.back();}
 unsigned stage_begin(std::string const& name){auto started_at=Clock::now();std::lock_guard<std::recursive_mutex> lock(mutex);if(direct_disabled)return 0;unsigned id=++next_id;stages.push_back({{"backend_call_id",id},{"parent_call_id",parent()},{"tactic_name",name},{"start",seconds(begin)},{"outer_route",route}});parents[std::this_thread::get_id()].push_back(id);double elapsed=seconds(started_at);direct_seconds+=elapsed;stage_seconds+=elapsed;if(direct_seconds>=explicit_remaining)direct_disabled=true;return id;}
 void stage_end(unsigned id){auto started_at=Clock::now();std::lock_guard<std::recursive_mutex> lock(mutex);for(auto& s:stages)if(s["backend_call_id"]==id){s["end"]=seconds(begin);break;}auto& p=parents[std::this_thread::get_id()];if(!p.empty()&&p.back()==id)p.pop_back();double elapsed=seconds(started_at);direct_seconds+=elapsed;stage_seconds+=elapsed;if(direct_seconds>=explicit_remaining)direct_disabled=true;}
 unsigned backend(uintptr_t ctx,unsigned gen,bool ls,std::string const& name){std::lock_guard<std::recursive_mutex> lock(mutex);unsigned id=++next_id;backends.push_back({{"query_id",query},{"solver_id",solver_id},{"backend_call_id",id},{"parent_call_id",parent()},{"context_id",id},{"native_context_address",ctx},{"context_generation",gen},{"tactic_name",name},{"outer_route",route},{"route_reason",route_reason},{"ls_sampling",ls},{"metadata_received",!ls},{"start",seconds(begin)},{"entry_function","not_entered"},{"funnel",Json::object()},{"binding_seconds",0.0},{"normalized_atoms",0},{"exact_matches",0},{"normalized_matches",0},{"unmapped",0},{"unsupported_normal_form",0},{"incomplete_mapping",0}});return id;}
 Json& call(unsigned id){for(auto& b:backends)if(b["backend_call_id"]==id)return b;throw std::logic_error("unknown A backend");}
 void event(Json e){std::lock_guard<std::recursive_mutex> lock(mutex);lifecycle.push_back(std::move(e));}
 void count(unsigned id,char const* key){std::lock_guard<std::recursive_mutex> lock(mutex);auto& f=call(id)["funnel"];f[key]=f.value(key,0ull)+1;}
 Json json(){std::lock_guard<std::recursive_mutex> lock(mutex);Json serialized_actions=Json::array();for(auto const& a:actions)serialized_actions.push_back(a.json());return {{"query_id",query},{"coverage_version",version},{"mode",mode},{"ordinary",ordinal},{"suggestions",suggestions},{"phase_overrides",std::count_if(actions.begin(),actions.end(),[](Action const& e){return e.changed;})},{"exposure_limit",sticky.load()},{"explicit_limit",direct_disabled.load()},{"intervened_check",changed.load()},{"requested_exposure_limit",exposure_remaining},{"actual_end",seconds(begin)},{"exposure_overrun",changed?std::max(0.0,seconds(begin)-exposure_remaining):0.0},{"direct_seconds",direct_seconds+guard_nanoseconds.load()*1e-9},{"hot_callback_seconds",hot_seconds},{"binding_seconds",binding_seconds},{"route_metadata_seconds",stage_seconds},{"diagnostic_snapshot_seconds",snapshot_seconds},{"exposure_guard_seconds",guard_nanoseconds.load()*1e-9},{"backend_calls",backends},{"actions",serialized_actions},{"stages",stages},{"lifecycle",lifecycle},{"b_encoded",0},{"b_internalized",0},{"b_selected",0},{"guidance_created_bool_vars",0},{"guidance_added_assertions",0},{"guidance_marked_relevant",0}};}
};
struct NonSmtLeaf {
 std::shared_ptr<Run> run;unsigned id=0;
 NonSmtLeaf(std::shared_ptr<Run> r,char const* name):run(std::move(r)){if(!run||run->closed)return;std::lock_guard<std::recursive_mutex> lock(run->mutex);id=run->backend(0,0,false,name);auto& b=run->call(id);b["entry_function"]="sat_tactic::operator";b["disabled_reason"]="non_smt_leaf";b["supports_A"]=false;b["ordinary_decisions"]=0;}
 void result(char const* value){if(!id)return;std::lock_guard<std::recursive_mutex> lock(run->mutex);run->call(id)["result"]=value;}
 ~NonSmtLeaf(){if(!id)return;std::lock_guard<std::recursive_mutex> lock(run->mutex);auto& b=run->call(id);b["end"]=seconds(run->begin);b["check_seconds"]=b["end"].get<double>()-b["start"].get<double>();if(!b.contains("result"))b["result"]="exception";}
};

}
