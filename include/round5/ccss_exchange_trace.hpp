#pragma once
#include <nlohmann/json.hpp>
#include <mutex>
#include <map>
#include <fstream>
#include <sstream>
#include <chrono>
#include <cstdlib>
#include <random>
#include <algorithm>
namespace r5 {
using J=nlohmann::json;using Clock=std::chrono::steady_clock;
inline bool enabled(){return std::getenv("GUIDED_R5_EXCHANGE_DIR")!=nullptr;}
inline std::string directory(){auto p=std::getenv("GUIDED_R5_EXCHANGE_DIR");return p?p:"";}
inline unsigned query(){auto p=std::getenv("GUIDED_R5_QUERY");return p?std::stoul(p):0;}
inline std::string role(){auto p=std::getenv("GUIDED_R5_ROLE");return p?p:"unknown";}
inline double seconds(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
inline std::string decimal(__int128_t v){bool neg=v<0;__uint128_t n=neg?-(__uint128_t)v:(__uint128_t)v;std::string s;do{s.push_back('0'+n%10);n/=10;}while(n);if(neg)s.push_back('-');std::reverse(s.begin(),s.end());return s;}
inline std::string rng(std::mt19937 const& mt){std::ostringstream s;s<<mt;return s.str();}
inline void file(std::string const& name,J const& j){if(!enabled())return;std::ofstream f(directory()+"/"+name);f<<j.dump()<<'\n';if(!f)throw std::runtime_error("round5 trace write failed");}
inline void event(J j){if(!enabled())return;static std::mutex m;static unsigned count=0;std::lock_guard<std::mutex> lock(m);if(count>200000)return;if(count++==200000)j={{"kind","trace_overflow"}};j["external_query"]=query();j["role"]=role();std::ofstream f(directory()+"/exchange_events.jsonl",std::ios::app);f<<j.dump()<<'\n';}
struct ManagerState {unsigned generation=0,batch=0;std::map<std::string,J> producers;};
inline std::map<void const*,ManagerState>& managers(){static std::map<void const*,ManagerState> m;return m;}
inline ManagerState& manager(void const* ptr){auto& s=managers()[ptr];if(!s.generation){static unsigned next=0;s.generation=++next;}return s;}
inline void destroy(void const* ptr){if(enabled())managers().erase(ptr);}
inline unsigned batch(void const* ptr,unsigned provider){if(!enabled())return 0;auto& s=manager(ptr);++s.batch;event({{"kind","producer_batch"},{"manager",s.generation},{"batch",s.batch},{"provider",provider}});return s.batch;}
inline void write(void const* ptr,std::string const& name,std::string const& raw,J identity,unsigned provider){if(!enabled())return;auto& s=manager(ptr);J j={{"kind","exchange_write"},{"manager",s.generation},{"batch",s.batch},{"provider",provider},{"query",query()},{"role",role()},{"name",name},{"raw",raw},{"identity",identity},{"overwrites_recorded_key",s.producers.count(name)!=0}};s.producers[name]=j;event(j);}
template<class Map> inline J snapshot(void const* ptr,Map const& original){
 Map copy=original;J out={{"map",J::object()},{"iteration",J::array()},{"producers",J::object()}};
 auto& s=manager(ptr);out["manager"]=s.generation;out["latest_batch"]=s.batch;
 for(auto const& kv:copy){out["map"][kv.first]=kv.second;out["iteration"].push_back(kv.first);auto it=s.producers.find(kv.first);out["producers"][kv.first]=it==s.producers.end()?J(nullptr):it->second;}
 return out;
}
struct Timer {double& dest;Clock::time_point t=Clock::now();explicit Timer(double& d):dest(d){}~Timer(){dest+=seconds(t);}};
}
