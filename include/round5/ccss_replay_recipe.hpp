#pragma once
#include "r5_exchange_trace.hpp"
#include <memory>
namespace r5 {
struct Probe {
 bool active=false,initialize_only=false,first_initialized=false;unsigned ordinal=0,init_count=0;std::string prefix;
 J recipe,interval_rows=J::array(),reads=J::array(),progress=J::array(),counters=J::object();
 std::map<std::string,double> times;std::string stage="constructor",exit="not_finished";Clock::time_point entry=Clock::now();
 unsigned long long rows_dropped=0;bool search_started=false;
 Probe(unsigned seed,unsigned cutoff,std::mt19937 const& mt):recipe{{"format",1},{"seed",seed},{"cutoff_seconds",cutoff},{"R0",rng(mt)},{"build_lits",J::array()},{"compiler",__VERSION__},{"stdlib",__GLIBCXX__}}{}
 void activate(J const& exchange){static unsigned sequence=0;ordinal=++sequence;active=ordinal<=2;if(!active)return;prefix="ccss_"+std::to_string(ordinal);recipe["exchange"]=exchange;recipe["query"]=query();recipe["ordinal"]=ordinal;recipe["role"]=role();entry=Clock::now();event({{"kind","consumer_entry"},{"ordinal",ordinal},{"manager",exchange.value("manager",0)}});}
 void begin_replay(std::string const& id,bool init_only){active=true;prefix=id;initialize_only=init_only;entry=Clock::now();}
 void save(std::string const& name,J const& data){if(!active)return;auto t=Clock::now();file(prefix+"_"+name+".json",data);times["log_output"]+=seconds(t);}
 void count(char const* name){if(active)counters[name]=counters.value(name,0ull)+1;}
 void read(std::string const& name,std::string const& status,J raw,J parsed=nullptr){if(active)reads.push_back({{"name",name},{"status",status},{"raw",raw},{"parsed",parsed}});}
 void point(J p){if(!active)return;if(progress.size()>=8192){++rows_dropped;return;}p["elapsed"]=seconds(entry);progress.push_back(std::move(p));}
 void flush(){if(!active)return;save("progress",{{"points",progress},{"dropped",rows_dropped}});save("terminal",{{"exit",exit},{"last_stage",stage},{"parent_elapsed",seconds(entry)},{"phase_seconds",times},{"counters",counters},{"initialize_count",init_count},{"time_fields","log_output is nested in phase walls; do not sum it again"},{"search_started",search_started}});}
};
struct PhaseTimer {Probe* p;std::string name;Clock::time_point start=Clock::now();explicit PhaseTimer(Probe* p,char const* s):p(p),name(s){if(p&&p->active)p->stage=s;}~PhaseTimer(){if(p&&p->active)p->times[name]+=seconds(start);}};
struct InitializationOnly:std::exception {char const* what()const noexcept override{return "round5_initialize_only";}};
}
