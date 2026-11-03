#include "refinement/native_output_split.hpp"
#include <iostream>
using namespace refinement;
Json run(Json const& j){
    WorkBudget b;
    auto op=j.at("op").get<std::string>();
    if(op=="arithmetic"){
        Json out=Json::array();for(auto const& r:j.at("cases")){auto k=r[0].get<std::string>();Big a(r[1].get<std::string>()),c(r[2].get<std::string>());
            if(k=="div")out.push_back({floor_div(a,c).str(),ceil_div(a,c).str()});
            else if(k=="floor_sum")out.push_back(floor_sum(a,c,Big(r[3].get<std::string>()),Big(r[4].get<std::string>()),b).str());
            else if(k=="count")out.push_back(count_residue_interval(a,c,Big(r[3].get<std::string>()),Big(r[4].get<std::string>()),Big(r[5].get<std::string>()),Big(r[6].get<std::string>()),Big(r[7].get<std::string>()),b).str());
        }return out;
    }
    if(op=="hits"){
        IntervalUnion u;for(auto const& x:j.at("intervals"))u.push_back({x[0].is_null()?std::nullopt:std::optional<Big>(Big(x[0].get<std::string>())),x[1].is_null()?std::nullopt:std::optional<Big>(Big(x[1].get<std::string>()))});
        auto h=nearest_modular_hits({Big(j.at("c").get<std::string>()),Big(j.at("a").get<std::string>())},j.at("bit"),j.at("desired"),u,b);
        Json p=Json::array();for(auto const& t:h.parameters)p.push_back(t.str());return {{"parameters",p},{"status",h.status}};
    }
    Ast ast=ast_from_json(j.at("ast"),b);
    if(op=="observe"){auto m=assignment_from(j.at("assignment"));auto t=evaluate(ast,m,b,j.value("official",true));return {{"legal",t.legal},{"trace",trace_json(t)}};}
    if(op=="algebra"||op=="domain"){
        if(op=="algebra"){Refiner r(std::move(ast),b);return r.metadata();}
        auto ir=compile_affine_ir(std::move(ast),b);
        std::map<unsigned,Big> d;for(auto const& x:j.at("direction"))d[x[0].get<unsigned>()]=Big(x[1].get<std::string>());
        auto assignment=assignment_from(j.at("assignment"));LineDomain domain(ir,assignment,d,b);return domain_json(domain.formula());
    }
    if(op=="sequence"){
        bool bounded=j.value("bounded",true);double pre_cap=bounded?0.100:30,event_cap=bounded?0.020:30;
        double used_wall=0,used_cpu=0;std::unique_ptr<Refiner> ref;std::string pre_reason="completed";
        Json metadata=nullptr;WorkBudget pre(pre_cap,pre_cap);try{ref=std::make_unique<Refiner>(ast,pre);metadata=ref->metadata();auto serialized=metadata.dump();pre.check();}catch(Exhausted const& e){ref.reset();pre_reason=e.what();}catch(Unsupported const& e){ref.reset();pre_reason=e.what();}
        double prewall=pre.wall(),precpu=pre.cpu();used_wall+=prewall;used_cpu+=precpu;
        OutputLedger output(ast.nodes.size());ObservationHistory native_history(ast.nodes.size());Json rows=Json::array();uint64_t event=0;
        for(auto const& mjson:j.at("models")){auto m=assignment_from(mjson);auto trace=observe_official(ast,m,b);if(!trace.legal)throw std::runtime_error("invalid frozen native model");++event;
            RefinementResult result;if(event==1)result.reason="first_output_identity";else if(!ref)result.reason="preprocessing_disabled:"+pre_reason;
            else {WorkBudget eb(std::max(0.0,std::min(event_cap,6-used_wall)),std::max(0.0,std::min(event_cap,6-used_cpu)));result=ref->try_refine(m,trace,output,event,eb,j.value("component_only",false));
                // Include complete diagnostic serialization in event cost. The
                // single noninterruptible dump is separately measured below.
                double lw=wall_now(),lc=cpu_now();auto encoded=refinement_json(result).dump();double logw=wall_now()-lw,logc=cpu_now()-lc;
                Json row=Json::parse(encoded);row["event_wall"]=eb.wall();row["event_cpu"]=eb.cpu();row["serialization_wall"]=logw;row["serialization_cpu"]=logc;row["wall_cap"]=eb.max_wall;row["cpu_cap"]=eb.max_cpu;used_wall+=eb.wall();used_cpu+=eb.cpu();rows.push_back(row);
            }
            if(rows.size()<event)rows.push_back(refinement_json(result));
            auto const& chosen=result.chosen?result.chosen->assignment:m;auto const& qt=result.chosen?result.chosen->trace:trace;
            native_history.commit(trace);bool duplicate=output.unique.count(assignment_key(chosen));
            if(j.value("layer",std::string("L2"))=="L1")output.commit(m,trace);else if(!duplicate)output.commit(chosen,qt);
            auto& row=rows.back();row["native_event_id"]=event;row["native_assignment"]=assignment_json(m);row["output_assignment"]=assignment_json(j.value("layer",std::string("L2"))=="L1"?m:chosen);row["output_duplicate"]=duplicate;row["native_covered"]=native_history.covered();row["output_covered"]=output.observations.covered();row["prefix_contains_native"]=contains(output.observations,native_history);row["output_count"]=output.committed_count;
        }
        return {{"preprocessing_reason",pre_reason},{"preprocess_wall",prewall}, {"preprocess_cpu",precpu},{"optional_wall",used_wall},{"optional_cpu",used_cpu},{"metadata",metadata},{"events",rows}};
    }
    throw std::runtime_error("unknown command");
}
int main(){std::string line;while(std::getline(std::cin,line)){try{std::cout<<Json({{"ok",true},{"result",run(Json::parse(line))}}).dump()<<'\n';}catch(std::exception const& e){std::cout<<Json({{"ok",false},{"error",e.what()}}).dump()<<'\n';}std::cout.flush();}}
