#pragma once
#include "observation.hpp"
#ifdef GUIDED_BUILD
#include "z3_guidance.h"
#endif
#include <fstream>
namespace guided {
class GuidanceBridge {
public:
    OriginalAst ast;AtomHintCatalog catalog;TargetEncoder encoder;
    unsigned mode;double cost=0,budget;bool disabled=false;
    std::map<unsigned,z3::expr> encoded;
    std::vector<Target> window;
    std::ofstream events,targets;
    GuidanceBridge(z3::expr const& f,unsigned mode,double wall,std::string const& dir):
        ast(f),catalog(ast),encoder(ast),mode(mode),budget(wall*0.05),
        events(dir+"/guidance_events.jsonl"),targets(dir+"/target_catalog.jsonl"){}
    void prepare(z3::solver& solver,unsigned epoch) {
#ifdef GUIDED_BUILD
        auto begin=Clock::now();window.clear();
        if(!ast.version)return;
        if(disabled||cost>=budget){
            if(!disabled){events<<Json({{"kind","cost_disabled"},{"epoch",epoch},{"cost",cost},{"budget",budget}}).dump()<<'\n';events.flush();}
            disabled=true;
            // Pure diagnostics retain visibility of old registered proxies.
            Z3_solver_set_coverage_guidance(solver.ctx(),solver,0,epoch,ast.version,0,nullptr,nullptr,0,nullptr,nullptr,nullptr);
            cost+=std::chrono::duration<double>(Clock::now()-begin).count();return;
        }
        window=ast.select_window();if(window.empty())return;
        std::vector<Z3_ast> predicates,atoms;std::vector<unsigned> ids,phases,indices;
        std::vector<z3::expr> hold;
        unsigned created=0;
        for(unsigned i=0;i<window.size();++i) {
            auto t=window[i];ids.push_back(t.id());Z3_ast pred=nullptr;
            auto hints=catalog.lookup(t);
            if(mode&1)for(auto const& h:hints){hold.push_back(h.atom);atoms.push_back(h.atom);phases.push_back(h.phase);indices.push_back(i);}
            Json log={{"epoch",epoch},{"coverage_version",ast.version},{"target_id",t.id()},{"node",t.node},{"bit",t.bit},{"desired",t.desired},{"sort",ast.nodes[t.node].boolean?"Bool":"Int"},{"a_static_match",hints.size()}};
            if(mode&2) {
                auto it=encoded.find(t.id());
                if(it!=encoded.end()){pred=it->second;log["encoding"]="reused";}
                else if(encoded.size()>=2048)log["encoding"]="registry_cap";
                else if(std::chrono::duration<double>(Clock::now()-begin).count()>=0.010)log["encoding"]="slice_incomplete";
                else {
                    try {
                        auto e=encoder.make(t);encoded.emplace(t.id(),e);pred=e;++created;log["encoding"]="created";
                        targets<<Json({{"target_id",t.id()},{"node",t.node},{"bit",t.bit},{"desired",t.desired},{"predicate",e.to_string()}}).dump()<<'\n';
                    }catch(std::runtime_error const& ex){if(std::string(ex.what())!="encoding_incomplete")throw;log["encoding"]="encoding_incomplete";}
                }
            }
            predicates.push_back(pred);events<<log.dump()<<'\n';
        }
        Z3_solver_set_coverage_guidance(solver.ctx(),solver,mode,epoch,ast.version,ids.size(),predicates.data(),ids.data(),atoms.size(),atoms.data(),phases.data(),indices.data());
        solver.ctx().check_error();
        targets.flush();events.flush();
        cost+=std::chrono::duration<double>(Clock::now()-begin).count();
#endif
    }
    Json end_check(z3::solver& solver) {
        Json out=Json::object();
#ifdef GUIDED_BUILD
        auto begin=Clock::now();
        out=Json::parse(Z3_solver_get_coverage_guidance_stats(solver.ctx(),solver));
        Z3_solver_clear_coverage_guidance(solver.ctx(),solver);
        cost+=out.value("prepare_seconds",0.0)+out.value("broker_seconds",0.0);
        events<<Json({{"kind","check_end"},{"stats",out},{"explicit_cost_seconds",cost}}).dump()<<'\n';events.flush();
        cost+=std::chrono::duration<double>(Clock::now()-begin).count();
#endif
        return out;
    }
    Json outcomes(Evaluation const& ev)const {
        Json r=Json::array();for(auto t:window){bool visited=ev.values[t.node].has_value();bool hit=visited&&bool((low64(*ev.values[t.node])>>t.bit)&1)==t.desired;
            auto const& n=ast.nodes[t.node];bool seen=t.desired?((n.seen1>>t.bit)&1):((n.seen0>>t.bit)&1);
            r.push_back({{"target_id",t.id()},{"reach",visited},{"hit",hit},{"new_observation",hit&&!seen}});}
        return r;
    }
};
}
