#pragma once
#include "pattern.hpp"
#include "impossible.hpp"
#include "kernel_api.hpp"
#include <chrono>
#include <fstream>
#include <memory>
#include <unordered_set>

namespace esg {
class Session {
    using Clock=std::chrono::steady_clock;
    z3::context& context;
    z3::expr formula;
    std::vector<z3::expr> variables;
    std::unique_ptr<Observer> observer;
    std::unique_ptr<Pattern> pattern;
    std::unique_ptr<ImpossibleBits> impossible;
    std::unordered_set<std::string> unique;
    Clock::time_point start;
    double wall;
    std::string mode,directory;
    std::ofstream samples,receipts,queries,ccss_log;
    std::string feedback="native";
    double ccss_budget_ms=0,ccss_start=0;
    bool ccss_disabled=false,exchange_saved=false;
    Json ccss_pending;
    unsigned ccss_calls=0,ccss_expired=0;
    double ccss_wall=0;
    size_t cursor=0;
    std::vector<unsigned> candidates;
    unsigned query=0,accepted=0,duplicates=0,target_node=0;
    unsigned max_bits=8;
    bool scoped=false,installed=false,query_open=false;
    double query_start=0;
    Json pending;
    z3::solver* active_solver=nullptr;
public:
    uint64_t covered()const{return observer?observer->covered:0;}
    bool ccss_enabled()const{return !ccss_disabled;}
    bool ccss_bounded()const{return ccss_budget_ms>0;}
    double now()const{return std::chrono::duration<double>(Clock::now()-start).count();}
    Session(z3::expr const& f,std::string dir,double limit,Clock::time_point origin):context(f.ctx()),formula(f),start(origin),wall(limit),directory(dir){
        mode=std::getenv("ESG_MODE")?std::getenv("ESG_MODE"):"native";
        if(mode!="native"&&mode!="observe"&&mode!="scope"&&mode!="route"&&mode!="definitions"&&mode!="soft"&&mode!="soft_unfiltered"&&mode!="soft_static"&&mode!="soft_release")throw std::runtime_error("invalid ESG_MODE");
        samples.open(dir+"/samples.raw");receipts.open(dir+"/receipts.jsonl");queries.open(dir+"/queries.jsonl");
        ccss_log.open(dir+"/ccss.jsonl");
        if(auto* value=std::getenv("ESG_CCSS_MS"))ccss_budget_ms=std::stod(value);
        if(auto* value=std::getenv("ESG_CCSS_OFF"))ccss_disabled=std::string(value)=="1";
        if(auto* value=std::getenv("ESG_CCSS_FEEDBACK"))feedback=value;
        if(ccss_budget_ms<0||!std::isfinite(ccss_budget_ms)||(feedback!="native"&&feedback!="complete"&&feedback!="hold"))throw std::runtime_error("invalid CCSS policy");
        std::set<unsigned> seen;std::vector<z3::expr> stack{f};
        while(!stack.empty()){auto e=stack.back();stack.pop_back();if(!seen.insert(e.id()).second)continue;
            if(e.is_const()&&e.decl().decl_kind()==Z3_OP_UNINTERPRETED)variables.push_back(e);
            for(unsigned j=0;j<e.num_args();++j)stack.push_back(e.arg(j));}
        std::sort(variables.begin(),variables.end(),[](auto const&a,auto const&b){return a.decl().name().str()<b.decl().name().str();});
        if(mode!="native"){
            observer=std::make_unique<Observer>(f);
            for(unsigned i=0;i<observer->nodes.size();++i){auto const& n=observer->nodes[i];
                if(n.constant||observer->dependencies[i].empty()||observer->dependencies[i].size()>16)continue;
                if(n.boolean&&observer->forced_boolean[i]!=-1)continue;
                candidates.push_back(i);}
            auto priority=[&](unsigned i){auto const& n=observer->nodes[i];return !n.boolean&&!n.children.empty()?0:n.boolean?1:2;};
            std::stable_sort(candidates.begin(),candidates.end(),[&](unsigned a,unsigned b){return priority(a)<priority(b);});
            if(mode=="soft"||mode=="soft_static"||mode=="soft_release")impossible=std::make_unique<ImpossibleBits>(*observer,dir,std::min(0.5,limit*0.02));
        }
        if(auto* value=std::getenv("ESG_MAX_BITS"))max_bits=std::min(64u,unsigned(std::stoul(value)));
        std::ofstream meta(dir+"/metadata.json");Json nodes=Json::array();
        if(observer)for(unsigned i=0;i<observer->nodes.size();++i){auto const& n=observer->nodes[i];nodes.push_back({{"id",i},{"kind",n.kind},{"name",n.name},{"boolean",n.boolean},{"children",n.children}});}
        meta<<Json({{"mode",mode},{"max_bits",max_bits},{"nodes",nodes},{"startup_wall",now()},{"ccss_budget_ms",ccss_budget_ms},{"ccss_disabled",ccss_disabled},{"feedback",feedback}}).dump();
    }
    ~Session(){if(installed)Z3_expr_soft_end();}
    bool prepare_pattern(){
        if(!observer||accepted==0||max_bits==0)return false;
        auto& o=*observer;unsigned count=candidates.size();bool probed=false;
        // A bounded rotating window of original expressions, with all selected
        // bits retained as individual preferences. No future samples are used.
        for(unsigned attempt=0;attempt<std::min(count,512u);++attempt){
            unsigned id=candidates[cursor++%count];auto const& n=o.nodes[id];
            uint64_t demand=(n.seen0^n.seen1)&(n.boolean?1:UINT64_MAX);if(!demand)continue;
            if(impossible)demand=impossible->eligible(id,demand,n.seen0&~n.seen1,query);if(!demand)continue;
            uint64_t selected=0;unsigned picked=0,rotation=(query*7)%64;
            for(unsigned j=0;j<64&&picked<max_bits;++j){unsigned bit=(rotation+j)%64;if((demand>>bit)&1){selected|=uint64_t(1)<<bit;++picked;}}
            try{
                auto original_reach=o.reach(id,o.context);
                if(impossible&&mode!="soft_static"&&!probed){selected=impossible->probe(id,selected,n.seen0&~n.seen1,original_reach,query,wall-now());probed=true;}
                if(!selected)continue;
                auto reach=z3::expr(context,Z3_translate(o.context,original_reach,context));auto expression=o.translate(id,context);
                pattern=std::make_unique<Pattern>(encode_pattern(expression,reach,selected,n.seen0&~n.seen1));target_node=id;
                pending["target"]={{"node",id},{"mask",selected},{"desired",pattern->desired},{"bits",pattern->bits},{"expression",n.expr.to_string()},{"reach",reach.to_string()},{"auxiliaries",pattern->auxiliaries.size()}};
                return true;
            }catch(std::runtime_error const& e){pending["target_skip"]=e.what();return false;}
        }
        return false;
    }
    z3::check_result check(z3::solver& solver,z3::expr_vector const& inherited){
        if(query_open)throw std::runtime_error("previous CDCL query not closed");
        ++query;query_open=true;active_solver=&solver;query_start=now();
        pending={{"query",query},{"start",query_start},{"mode",mode},{"inherited_before",inherited.size()},{"released",Json::array()}};
        z3::expr_vector asms(context);for(auto e:inherited)asms.push_back(e);
        bool target=(mode=="definitions"||mode=="soft"||mode=="soft_unfiltered"||mode=="soft_static"||mode=="soft_release")&&prepare_pattern();
        pending["exchange_before"]=Z3_expr_exchange(context,0,0,nullptr,nullptr);
        if(target&&feedback=="hold"){Z3_expr_exchange(context,1,0,nullptr,nullptr);exchange_saved=true;}
        if(target&&mode=="soft_release"){
            std::set<std::string> names;for(auto id:observer->dependencies[target_node])names.insert(observer->nodes[id].name);
            asms.resize(0);
            for(auto e:inherited){bool release=e.is_eq()&&e.arg(0).is_const()&&names.count(e.arg(0).decl().name().str());
                if(release)pending["released"].push_back(e.arg(0).decl().name().str());else asms.push_back(e);}
        }
        // The host never scopes the combined solver for new guidance. Only the
        // legacy scope control deliberately changes its route.
        scoped=accepted>0&&mode=="scope";
        if(target||mode=="route"){
            std::vector<Z3_ast> goals,aux,definitions;
            if(target){if(mode!="definitions")for(auto e:pattern->goals)goals.push_back(e);
            for(auto e:pattern->auxiliaries)aux.push_back(e);for(auto e:pattern->definitions)definitions.push_back(e);}
            Z3_expr_soft_begin(context,goals.size(),goals.data(),aux.size(),aux.data(),64,definitions.size(),definitions.data());installed=true;
        }
        if(scoped)solver.push();
        pending["inherited_after"]=asms.size();pending["scoped"]=scoped;pending["preparation_wall"]=now()-query_start;
        z3::params p(context);p.set("timeout",unsigned(std::max(1.0,std::min(50000.0,(wall-now())*1000.0))));solver.set(p);
        auto result=solver.check(asms);pending["check_complete"]=now();pending["result"]=result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown";
        if(result==z3::unknown)pending["reason"]=solver.reason_unknown();
        return result;
    }
    void end_query(){
        if(!query_open)return;
        if(installed){uint64_t stats[12];Z3_expr_soft_stats(stats);pending["kernel"]={{"prepared",stats[0]},{"chosen",stats[1]},{"already_true",stats[2]},{"already_false",stats[3]},{"decision_calls",stats[4]},{"targets_consumed",stats[5]},{"auxiliary_exchange_skips",stats[6]},{"window_skips",stats[7]},{"tactic_routes",stats[8]},{"incremental_routes",stats[9]},{"mapped",stats[10]},{"mapping_failures",stats[11]}};}
        if(scoped)active_solver->pop();scoped=false;
        if(installed){Z3_expr_soft_end();installed=false;}
        pending["exchange_after_solver"]=Z3_expr_exchange(context,0,0,nullptr,nullptr);
        if(exchange_saved){Z3_expr_exchange(context,2,0,nullptr,nullptr);exchange_saved=false;}
        pending["exchange_delivered"]=Z3_expr_exchange(context,0,0,nullptr,nullptr);
        pattern.reset();pending["complete"]=now();queries<<pending.dump()<<"\n";queries.flush();query_open=false;
    }
    bool commit(z3::model const& model,std::string const& source){
        if(now()>=wall)return false;
        std::map<std::string,Int> values;z3::model snapshot(context);std::string key;
        Json assignment=Json::object();
        for(auto const& variable:variables){auto value=model.eval(variable,false);Int integer;
            if(variable.is_bool())integer=value.is_true()?1:0;
            else if(value.is_numeral())integer=parse_integer(value.to_string());else integer=0;
            auto name=variable.decl().name().str(),string=decimal(integer);values.emplace(name,integer);assignment[name]=string;
            auto literal=variable.is_bool()?context.bool_val(bool(integer)):context.int_val(string.c_str());auto decl=variable.decl();snapshot.add_const_interp(decl,literal);
            key+=std::to_string(name.size())+":"+name+std::to_string(string.size())+":"+string;
        }
        if(!snapshot.eval(formula,true).is_true())throw std::runtime_error("projected model violates original formula");
        if(source=="CDCL"&&feedback=="complete"){
            std::vector<std::string> names,strings;std::vector<char const*> np,vp;
            for(auto const& variable:variables){auto name=variable.decl().name().str();names.push_back(name);
                strings.push_back(variable.is_bool()?(values.at(name)!=0?"true":"false"):decimal(values.at(name)));}
            for(unsigned i=0;i<names.size();++i){np.push_back(names[i].c_str());vp.push_back(strings[i].c_str());}
            Z3_expr_exchange(context,3,np.size(),np.data(),vp.data());pending["exchange_projected"]=np.size();
            // A valid duplicate is still a valid seed. Replace the entire map
            // after hard-formula validation, before output deduplication.
        }
        if(unique.count(key)){++duplicates;return false;}
        Evaluation ev;if(observer){ev=observer->evaluate(values);if(!ev.legal)throw std::runtime_error("independent observer rejected model");}
        Json targets=Json::array();
        if(source=="CDCL"&&pattern){for(unsigned bit:pattern->bits){bool visited=ev.visited[target_node];bool actual=(low64(ev.values[target_node])>>bit)&1;bool desired=(pattern->desired>>bit)&1;
            targets.push_back({{"bit",bit},{"desired",desired},{"visited",visited},{"value_hit",visited&&actual==desired}});}
            pending["formal_target_observations"]=targets;
            // Goals contain auxiliaries: their truth is audited in the original solver model.
            unsigned fulfilled=0,i=0;for(auto g:pattern->goals){bool hit=model.eval(g,true).is_true();
                if(hit!=targets[i]["value_hit"].get<bool>())throw std::runtime_error("solver goal disagrees with original expression/Reach");
                targets[i++]["solver_goal"]=hit;fulfilled+=hit;}pending["model_goal_hits"]=fulfilled;
            pending["formal_target_observations"]=targets;
        }
        if(now()>=wall)return false;
        samples<<accepted<<": ";for(auto const& [name,value]:values)samples<<name<<":"<<decimal(value)<<";";samples<<"\n";samples.flush();
        double done=now();if(done>=wall){receipts<<Json({{"accepted",false},{"reason","late_write"},{"time",done}}).dump()<<"\n";receipts.flush();return false;}
        unique.insert(std::move(key));uint64_t gain=observer?observer->commit(ev):0;
        receipts<<Json({{"accepted",true},{"index",accepted},{"source",source},{"query",query},{"time",done},{"assignment",assignment},{"covered",covered()},{"gain",gain}}).dump()<<"\n";receipts.flush();++accepted;return true;
    }
    void begin_ccss(z3::solver& solver){
        ccss_start=now();++ccss_calls;
        double budget=ccss_budget_ms>0?std::min(ccss_budget_ms,std::max(0.001,(wall-now())*1000)):0;
        ccss_pending={{"call",ccss_calls},{"query",query},{"start",ccss_start},{"budget_ms",budget},{"feedback",feedback},{"exchange_size",Z3_expr_exchange(context,0,0,nullptr,nullptr)},{"models_before",accepted},{"covered_before",covered()}};
        if(budget>0)solver.set("timeout",unsigned(std::max(1.0,std::ceil(budget))));
        Z3_expr_ccss_begin(budget);
    }
    void checked_ccss(z3::check_result result){
        double stats[8];Z3_expr_ccss_end(stats);
        ccss_pending["check_complete"]=now();ccss_pending["result"]=result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown";
        ccss_pending["kernel_seconds"]=std::vector<double>(stats,stats+6);
        ccss_pending["deadline_hit"]=stats[6]!=0;ccss_pending["checkpoint_visits"]=uint64_t(stats[7]);ccss_expired+=stats[6]!=0;
    }
    void end_ccss(){
        auto done=now();ccss_pending["complete"]=done;ccss_pending["models_after"]=accepted;ccss_pending["covered_after"]=covered();
        ccss_wall+=done-ccss_start;ccss_log<<ccss_pending.dump()<<"\n";ccss_log.flush();
    }
    void finish(){end_query();std::ofstream out(directory+"/summary.json");Json summary={{"mode",mode},{"models",accepted},{"duplicates",duplicates},{"queries",query},{"covered",covered()},{"wall",now()},{"limit",wall},{"normal",true},{"ccss_calls",ccss_calls},{"ccss_deadline_hits",ccss_expired},{"ccss_wall",ccss_wall}};
        if(impossible)summary["filter"]={{"static_bits",impossible->static_bits},{"unsat_bits",impossible->unsat_bits},{"filtered_occurrences",impossible->filtered_occurrences},{"proof_calls",impossible->proof_calls},{"proof_wall",impossible->proof_wall}};
        out<<summary.dump(2)<<"\n";}
};
}
