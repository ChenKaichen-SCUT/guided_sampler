#pragma once
#include "r6_stagnation_guard.hpp"
#include "r6_sha256.hpp"
#include <nlohmann/json.hpp>
#include <chrono>
#include <ctime>
#include <cstdlib>
#include <fstream>
#include <random>
#include <atomic>
namespace r6 {
using J=nlohmann::json;using Clock=std::chrono::steady_clock;
inline bool on(){auto p=std::getenv("GUIDED_CCSS_STAGNATION_GUARD");return p&&std::string(p)=="1";}
inline bool trace_on(){return std::getenv("GUIDED_R6_TRACE_DIR")!=nullptr;}
inline double cpu(){timespec ts;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts);return ts.tv_sec+ts.tv_nsec*1e-9;}
inline double wall(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
inline std::string rng_hash(std::mt19937 const& mt){std::ostringstream s;s<<mt;return sha256(s.str());}
struct GuardTrace {
    StagnationGuard guard;
    bool active=false,begun=false,emitted=false,search_started=false;
    uint64_t call_id=0,query=0,seed=0;double cutoff=0,search_cpu=0,search_wall=0;
    std::string reason="unknown",error,map_sha,rng_before,rng_search_before;
    J consumed=J::object();Clock::time_point whole_start;
    template<class Map>void begin(Map const& original,std::mt19937 const& mt,double native_cutoff){
        active=trace_on();begun=true;emitted=false;search_started=false;reason="unknown";error.clear();consumed=J::object();cutoff=native_cutoff;guard.reset(on());whole_start=Clock::now();
        if(active){static std::atomic<uint64_t> next{0};call_id=++next;auto q=std::getenv("GUIDED_R6_QUERY");query=q?std::stoull(q):0;Map copy=original;J map=copy;map_sha=sha256(map.dump());rng_before=rng_hash(mt);setenv("GUIDED_R6_LAST_CALL_ID",std::to_string(call_id).c_str(),1);}
    }
    void read(std::string const& name,J raw){if(active)consumed[name]=std::move(raw);}
    void finish(std::mt19937 const& mt,std::string const& why,bool produced){
        if(!begun||emitted)return;reason=why;guard.update_span();emitted=true;
        if(!active)return;
        setenv("GUIDED_R6_LAST_REASON",reason.c_str(),1);
        J j={{"call_id",call_id},{"source_query_id",query},{"guard_enabled",guard.enabled},{"stagnation_limit",StagnationGuard::limit},{"map_sha256",map_sha},{"consumed_map_sha256",sha256(consumed.dump())},{"consumed_map",consumed},{"initial_global_best",guard.valid?J(guard.initial_global_best):J(nullptr)},{"last_global_best",guard.valid?J(guard.best_global_cost):J(nullptr)},{"last_improvement_step",guard.valid?J(guard.last_global_improvement_step):J(nullptr)},{"exit_step_exact",search_started?J(guard.step):J(nullptr)},{"max_stagnation_steps",search_started?J(guard.max_stagnation_steps):J(nullptr)},{"initialization_count",guard.initialization_count},{"restart_count",guard.initialization_count?guard.initialization_count-1:0},{"exit_reason",reason},{"exception_text",error},{"search_cpu_seconds",search_started?J(search_cpu):J(nullptr)},{"search_wall_seconds",search_started?J(search_wall):J(nullptr)},{"whole_ccss_wall_seconds",wall(whole_start)},{"rng_before_sha256",rng_before},{"rng_search_before_sha256",rng_search_before.empty()?J(nullptr):J(rng_search_before)},{"rng_after_sha256",rng_hash(mt)},{"model_produced",produced},{"native_cutoff_seconds",cutoff},{"seed",seed},{"search_started",search_started},{"map_hash_encoding","SHA256 of sorted UTF8 compact JSON; absent consumed key = null"}};
        std::ofstream f(std::string(std::getenv("GUIDED_R6_TRACE_DIR"))+"/ccss_guard.jsonl",std::ios::app);f<<j.dump()<<'\n';if(!f)throw std::runtime_error("round6 guard log write failure");
    }
};
struct SearchTimer {
    GuardTrace& t;Clock::time_point started=Clock::now();double started_cpu=0;
    SearchTimer(GuardTrace& t,std::mt19937 const& mt):t(t){t.guard.reset(on());t.search_started=true;started_cpu=cpu();if(t.active)t.rng_search_before=rng_hash(mt);}
    ~SearchTimer(){t.search_wall=wall(started);t.search_cpu=cpu()-started_cpu;t.guard.update_span();}
};
}
