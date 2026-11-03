#include "refinement/refiner.hpp"
#include <fstream>
#include <iostream>
using namespace refinement;
int main(int argc,char** argv){
    if(argc!=5)return 2;std::string input=argv[1],directory=argv[2],mode=argv[3],track=argv[4];
    double all_w=wall_now(),all_c=cpu_now();std::ofstream output(directory+"/stream.jsonl");
    auto emit=[&](Json const& j){output<<j.dump()<<'\n';output.flush();if(!output)throw std::runtime_error("stream write failed");};
    try{
        if(mode!="Legacy")throw std::runtime_error("repair configurations not implemented at Legacy probe freeze");
        Json data;Ast ast;CostTrace parse_trace;WorkBudget parsing;parsing.trace=&parse_trace;
        {StageScope stage(&parse_trace,RepairStage::ParseInput);std::ifstream f(input);f>>data;}
        {StageScope stage(&parse_trace,RepairStage::CopyAst);ast=ast_from_json(data.at("ast"),parsing);}
        emit({{"kind","input"},{"mode",mode},{"track",track},{"nodes",ast.nodes.size()},{"variables",ast.variables.size()},{"parse_cpu",parsing.cpu()},{"parse_wall",parsing.wall()},{"trace",parse_trace.json()}});
        bool probe=track=="probe";double pre_cap=probe?2:.1,event_cap=probe?.5:.02;double used_w=0,used_c=0;Json record_tails=Json::array();std::unique_ptr<Refiner> ref;std::string pre_status="completed";CostTrace pre_trace;WorkBudget pre(pre_cap,pre_cap);pre.trace=&pre_trace;Json metadata=nullptr;
        try{{StageScope copy(&pre_trace,RepairStage::CopyAst);ref=std::make_unique<Refiner>(ast,pre);} {StageScope meta(&pre_trace,RepairStage::Metadata);metadata=ref->metadata();} {StageScope serialized(&pre_trace,RepairStage::SerializeResult);emit({{"kind","metadata"},{"metadata",metadata}});pre.check();}}
        catch(Exhausted const& e){pre_status=e.what();ref.reset();}catch(Unsupported const& e){pre_status=e.what();ref.reset();}
        double pw=pre.wall(),pc=pre.cpu();used_w+=pw;used_c+=pc;
        double tailw=wall_now(),tailc=cpu_now();emit({{"kind","preprocess"},{"status",pre_status},{"cpu",pc},{"wall",pw},{"cpu_cap",pre.max_cpu},{"wall_cap",pre.max_wall},{"trace",pre_trace.json()}});
        double ptw=wall_now()-tailw,ptc=cpu_now()-tailc;used_w+=ptw;used_c+=ptc;record_tails.push_back({{"phase","preprocess"},{"wall",ptw},{"cpu",ptc}});if(ref&&(used_w>pre_cap||used_c>pre_cap)){ref.reset();pre_status="preprocess_log_tail_overrun";}
        OutputLedger history(ast.nodes.size());ObservationHistory native_history(ast.nodes.size());uint64_t event=0;bool component=track=="component_only",l1=track=="L1"||probe;double mandatory_w=0,mandatory_c=0;
        for(auto const& mjson:data.at("models")){
            ++event;if(probe&&event>5)break;double mw=wall_now(),mc=cpu_now();auto m=assignment_from(mjson);WorkBudget required;auto native=observe_official(ast,m,required);if(!native.legal)throw std::runtime_error("invalid frozen original model");mandatory_w+=wall_now()-mw;mandatory_c+=cpu_now()-mc;
            RefinementResult r;CostTrace event_trace;double capw=probe?event_cap:std::max(0.0,std::min(event_cap,6-used_w)),capc=probe?event_cap:std::max(0.0,std::min(event_cap,6-used_c));WorkBudget eb(capw,capc);eb.trace=&event_trace;
            if(event==1)r.reason="first_output_identity";
            else if(!ref)r.reason="preprocessing_disabled:"+pre_status;
            else r=ref->try_refine(m,native,history,event,eb,component);
            auto const& chosen=r.chosen?r.chosen->assignment:m;auto const& trace=r.chosen?r.chosen->trace:native;
            {StageScope serialization(&event_trace,RepairStage::SerializeResult);auto row=refinement_json(r);row["kind"]="event";row["native_event_id"]=event;row["native_assignment"]=assignment_json(m);row["output_assignment"]=assignment_json(l1?m:chosen);row["mode"]=mode;row["historical_cpu_credit_proven"]=false;emit(row);}
            double ew=eb.wall(),ec=eb.cpu();used_w+=ew;used_c+=ec;
            mw=wall_now();mc=cpu_now();native_history.commit(native);auto const& delivery=l1?m:chosen;auto const& observations=l1?native:trace;bool duplicate=history.unique.count(assignment_key(delivery));if(!duplicate)history.commit(delivery,observations);bool inclusion=contains(history.observations,native_history);if(!inclusion)throw std::runtime_error("prefix observation loss");mandatory_w+=wall_now()-mw;mandatory_c+=cpu_now()-mc;
            tailw=wall_now();tailc=cpu_now();emit({{"kind","event_cost"},{"native_event_id",event},{"wall",ew},{"cpu",ec},{"wall_cap",capw},{"cpu_cap",capc},{"trace",event_trace.json()},{"native_covered",native_history.covered()},{"output_covered",history.observations.covered()},{"output_count",history.committed_count},{"output_duplicate",duplicate},{"prefix_contains_native",inclusion}});
            double tw=wall_now()-tailw,tc=cpu_now()-tailc;used_w+=tw;used_c+=tc;record_tails.push_back({{"phase","event"},{"native_event_id",event},{"wall",tw},{"cpu",tc}});
        }
        emit({{"kind","summary"},{"record_tails",record_tails},{"effective_preprocess_status",pre_status},{"processed_models",event-(probe&&event>5?1:0)},{"optional_cpu",used_c},{"optional_wall",used_w},{"mandatory_cpu",mandatory_c},{"mandatory_wall",mandatory_w},{"process_cpu_before_final_record",cpu_now()-all_c},{"process_wall_before_final_record",wall_now()-all_w},{"native_covered",native_history.covered()},{"output_covered",history.observations.covered()},{"output_count",history.committed_count},{"historical_cpu_credit_proven",false}});return 0;
    }catch(std::exception const& e){emit({{"kind","failure"},{"error",e.what()},{"cpu",cpu_now()-all_c},{"wall",wall_now()-all_w}});return 1;}
}
