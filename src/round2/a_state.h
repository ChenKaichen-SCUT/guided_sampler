#pragma once
#include "solver/a_shared.hpp"
#include <nlohmann/json.hpp>
#include <mutex>
#include <thread>
namespace a2 {
using Json=nlohmann::json;
struct Run {
 std::shared_ptr<const Index> index;unsigned query,version,mode,diagnostic;
 Clock::time_point begin=Clock::now();bool started=false,closed=false;
 std::atomic<bool> changed{false},sticky{false};double exposure_remaining,explicit_remaining,direct_seconds=0;
 std::recursive_mutex mutex;unsigned ordinal=0,suggestions=0,next_id=0;
 std::map<unsigned,std::pair<uint64_t,uint64_t>> attempted;
 Json backends=Json::array(),actions=Json::array(),lifecycle=Json::array(),stages=Json::array();
 std::map<std::thread::id,std::vector<unsigned>> parents;
 std::string route,route_reason;
 Run(std::shared_ptr<Index> p,unsigned q,unsigned v,unsigned md,double exposure,double explicit_cost,unsigned diag):index(p),query(q),version(v),mode(md),diagnostic(diag),exposure_remaining(exposure),explicit_remaining(explicit_cost){++p->active;}
 ~Run(){close();}
 void close(){std::lock_guard<std::recursive_mutex> lock(mutex);if(!closed){closed=true;if(index)--const_cast<Index&>(*index).active;}}
 void start(){std::lock_guard<std::recursive_mutex> lock(mutex);if(!started){begin=Clock::now();started=true;}}
 bool expired(){if(sticky)return true;if(changed&&seconds(begin)>=exposure_remaining){sticky=true;return true;}return false;}
 unsigned parent(){auto& p=parents[std::this_thread::get_id()];return p.empty()?0:p.back();}
 unsigned stage_begin(std::string const& name){std::lock_guard<std::recursive_mutex> lock(mutex);unsigned id=++next_id;stages.push_back({{"backend_call_id",id},{"parent_call_id",parent()},{"tactic_name",name},{"start",seconds(begin)},{"outer_route",route}});parents[std::this_thread::get_id()].push_back(id);return id;}
 void stage_end(unsigned id){std::lock_guard<std::recursive_mutex> lock(mutex);for(auto& s:stages)if(s["backend_call_id"]==id){s["end"]=seconds(begin);break;}auto& p=parents[std::this_thread::get_id()];if(!p.empty()&&p.back()==id)p.pop_back();}
 unsigned backend(uintptr_t ctx,unsigned gen,bool ls,std::string const& name){std::lock_guard<std::recursive_mutex> lock(mutex);unsigned id=++next_id;backends.push_back({{"query_id",query},{"backend_call_id",id},{"parent_call_id",parent()},{"context_id",ctx},{"context_generation",gen},{"tactic_name",name},{"outer_route",route},{"route_reason",route_reason},{"ls_sampling",ls},{"metadata_received",!ls},{"start",seconds(begin)},{"entry_function","not_entered"},{"funnel",Json::object()},{"binding_seconds",0.0},{"normalized_atoms",0},{"exact_matches",0},{"normalized_matches",0},{"unmapped",0},{"unsupported_normal_form",0},{"incomplete_mapping",0}});return id;}
 Json& call(unsigned id){for(auto& b:backends)if(b["backend_call_id"]==id)return b;throw std::logic_error("unknown A backend");}
 void count(unsigned id,char const* key){auto& f=call(id)["funnel"];f[key]=f.value(key,0ull)+1;}
 Json json(){std::lock_guard<std::recursive_mutex> lock(mutex);return {{"query_id",query},{"coverage_version",version},{"mode",mode},{"ordinary",ordinal},{"suggestions",suggestions},{"phase_overrides",std::count_if(actions.begin(),actions.end(),[](Json const& e){return e["phase_changed"].get<bool>();})},{"exposure_limit",sticky.load()},{"intervened_check",changed.load()},{"requested_exposure_limit",exposure_remaining},{"actual_end",seconds(begin)},{"exposure_overrun",changed?std::max(0.0,seconds(begin)-exposure_remaining):0.0},{"direct_seconds",direct_seconds},{"backend_calls",backends},{"actions",actions},{"stages",stages},{"lifecycle",lifecycle},{"b_encoded",0},{"b_internalized",0},{"b_selected",0},{"guidance_created_bool_vars",0},{"guidance_added_assertions",0},{"guidance_marked_relevant",0}};}
};
}
