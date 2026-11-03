#include "refinement/budgeted_delivery.hpp"
#include <fstream>
#include <iostream>
#include <sys/resource.h>
#include "round6/sha256.hpp"
using namespace refinement;
int main(int argc,char** argv){
 if(argc!=5)return 2;std::string input=argv[1],directory=argv[2],configuration=argv[3],track=argv[4];
 double all_w=wall_now(),all_c=cpu_now();std::ofstream output(directory+"/stream.jsonl");
 auto emit=[&](Json const& j){output<<j.dump()<<'\n';output.flush();if(!output)throw std::runtime_error("stream write failed");};
 try{
  auto strategies=delivery_strategies(configuration);bool probe=track=="probe",l1=probe||track=="L1";
  Json data;Ast ast;CostTrace parse_trace;WorkBudget parsing;parsing.trace=&parse_trace;
  {StageScope stage(&parse_trace,RepairStage::ParseInput);std::ifstream f(input);f>>data;}
  {StageScope stage(&parse_trace,RepairStage::CopyAst);ast=ast_from_json(data.at("ast"),parsing);}
  emit({{"kind","input"},{"configuration",configuration},{"track",track},{"parse_cpu",parsing.cpu()},{"parse_wall",parsing.wall()},{"trace",parse_trace.json()}});
  double pre_cap=probe?2:.100,pre_soft=probe?2:.096,event_cap=probe?.5:.020,event_soft=probe?.5:.018;
  double used_w=0,used_c=0,mandatory_w=0,mandatory_c=0;std::unique_ptr<Refiner> ref;ScoreState scores;
  CostTrace pre_trace;WorkBudget pre(pre_cap,pre_cap);pre.trace=&pre_trace;auto pre_search=pre.view(pre_soft,pre_soft);std::string pre_status="completed";bool pre_eligible=false;Json metadata=nullptr;
  // Fixed-size event receipt storage is also optional preprocessing work.
  std::vector<Json> receipts(data.at("models").size());
  try{
   {StageScope stage(&pre_trace,RepairStage::CopyAst);ref=std::make_unique<Refiner>(ast,pre_search,strategies);if(ref->score_index)scores=initial_score_state(ref->ir.ast,*ref->score_index,pre_search);pre_search.check();}
   {StageScope stage(&pre_trace,RepairStage::Metadata);metadata=ref->metadata();if(ref->score_index)metadata["score_index"]={{"groups",ref->score_index->groups.size()},{"original_affected_entries",ref->score_index->original_entries},{"compressed_group_direction_entries",ref->score_index->group_entries}};pre.check();}
   {StageScope stage(&pre_trace,RepairStage::SerializeResult);emit({{"kind","metadata"},{"metadata",metadata}});metadata=nullptr;pre.check();}
  }catch(Exhausted const& e){pre_status=e.what();ref.reset();}catch(Unsupported const& e){pre_status=e.what();ref.reset();}
  rusage pre_rss{};getrusage(RUSAGE_SELF,&pre_rss);
  emit({{"preprocess_process_peak_rss_kb",pre_rss.ru_maxrss},{"kind","preprocess"},{"status",pre_status},{"cpu_before_record",pre.cpu()},{"wall_before_record",pre.wall()},{"cap",pre_cap},{"soft",pre_soft},{"trace",pre_trace.json()}});
  double pc=pre.cpu(),pw=pre.wall();pre_eligible=ref&&pc<pre_cap&&pw<pre_cap;if(ref&&!pre_eligible){pre_status="preprocess_tail_overrun";ref.reset();pc=pre.cpu();pw=pre.wall();}used_c+=pc;used_w+=pw;
  OutputLedger history(ast.nodes.size());ObservationHistory native_history(ast.nodes.size());std::string identity=directory+":"+(l1?"native_prefix":"actual_output");
  unsigned processed=0;double postlude_start_c=0,postlude_start_w=0;
  auto finalize_postlude=[&](){
   if(!processed||postlude_start_w==0)return;auto& rec=receipts[processed-1];double delta_c=cpu_now()-postlude_start_c,delta_w=wall_now()-postlude_start_w;postlude_start_w=0;
   used_c+=delta_c;used_w+=delta_w;rec["measured_postlude_cpu"]=delta_c;rec["measured_postlude_wall"]=delta_w;rec["event_total_cpu"]=rec["event_total_cpu"].get<double>()+delta_c;rec["event_total_wall"]=rec["event_total_wall"].get<double>()+delta_w;
   double check_c=cpu_now(),check_w=wall_now();
   bool late=rec["event_total_cpu"].get<double>()>=rec["event_cpu_cap"].get<double>()||rec["event_total_wall"].get<double>()>=rec["event_wall_cap"].get<double>();
   if(rec["budget_eligible"].get<bool>()&&late){
    if(rec["actually_delivered"].get<bool>()){OutputLedger restored(ast.nodes.size());WorkBudget cleanup;for(unsigned k=0;k<processed;++k){auto const& prior=receipts[k];bool use_candidate=k+1<processed&&prior["actually_delivered"].get<bool>();auto m=assignment_from(use_candidate?prior["candidate_assignment"]:data["models"][k]);auto t=observe_official(ast,m,cleanup);if(!restored.unique.count(assignment_key(m)))restored.commit(m,t);}history=std::move(restored);scores.valid=false;}
    rec["budget_eligible"]=false;rec["actually_delivered"]=false;rec["delivery_rejection"]="delivery_tail_overrun";rec["output_covered"]=history.observations.covered();rec["output_count"]=history.committed_count;
   }
   double extra_c=cpu_now()-check_c,extra_w=wall_now()-check_w;used_c+=extra_c;used_w+=extra_w;rec["event_total_cpu"]=rec["event_total_cpu"].get<double>()+extra_c;rec["event_total_wall"]=rec["event_total_wall"].get<double>()+extra_w;
   // If the remaining margin cannot cover even the measured outer bookkeeping,
   // conservatively withhold eligibility. This is a measurement uncertainty, not a larger cap.
   double margin_c=rec["event_cpu_cap"].get<double>()-rec["event_total_cpu"].get<double>(),margin_w=rec["event_wall_cap"].get<double>()-rec["event_total_wall"].get<double>();
   rec["measurement_uncertainty_cpu"]=extra_c;rec["measurement_uncertainty_wall"]=extra_w;
   if(rec["budget_eligible"].get<bool>()&&(margin_c<=extra_c||margin_w<=extra_w)){
    double rw=wall_now(),rc=cpu_now();if(rec["actually_delivered"].get<bool>()){OutputLedger restored(ast.nodes.size());WorkBudget cleanup;for(unsigned k=0;k<processed;++k){auto const& prior=receipts[k];bool chosen=k+1<processed&&prior["actually_delivered"].get<bool>();auto m=assignment_from(chosen?prior["candidate_assignment"]:data["models"][k]);auto t=observe_official(ast,m,cleanup);if(!restored.unique.count(assignment_key(m)))restored.commit(m,t);}history=std::move(restored);scores.valid=false;}
    rec["budget_eligible"]=false;rec["actually_delivered"]=false;rec["delivery_rejection"]=(margin_c<=0||margin_w<=0)?"delivery_tail_overrun":"budget_eligibility_unknown";rec["output_covered"]=history.observations.covered();rec["output_count"]=history.committed_count;
    double c=cpu_now()-rc,w=wall_now()-rw;used_c+=c;used_w+=w;rec["event_total_cpu"]=rec["event_total_cpu"].get<double>()+c;rec["event_total_wall"]=rec["event_total_wall"].get<double>()+w;
   }
   // Clock/readback margin is reported separately, never replaced by a zero tail.
   rec["delivered_gain"]=rec["actually_delivered"].get<bool>()?rec["candidate_gain"]:rec["native_gain"];
   rec["overrun_cpu"]=std::max(0.,rec["event_total_cpu"].get<double>()-rec["event_cpu_cap"].get<double>());rec["overrun_wall"]=std::max(0.,rec["event_total_wall"].get<double>()-rec["event_wall_cap"].get<double>());
  };
  for(auto const& mj:data.at("models")){
   finalize_postlude();if(probe&&processed==5)break;++processed;double mw=wall_now(),mc=cpu_now();Assignment native_m=assignment_from(mj);WorkBudget required;auto native=observe_official(ast,native_m,required);if(!native.legal)throw std::runtime_error("invalid frozen native");native_history.commit(native);mandatory_w+=wall_now()-mw;mandatory_c+=cpu_now()-mc;
   CostTrace trace;double cw=probe?event_cap:std::max(0.0,std::min(event_cap,6-used_w)),cc=probe?event_cap:std::max(0.0,std::min(event_cap,6-used_c));WorkBudget total(cw,cc);total.trace=&trace;auto search=total.view(std::min(event_soft,cw),std::min(event_soft,cc));
   RefinementResult result;BudgetedDeliveryTransaction transaction(history);auto version=history.observations.version;bool attempted=false;
   if(processed==1)result.reason="first_output_identity";
   else if(!ref)result.reason="preprocessing_disabled:"+pre_status;
   else if(cw<=0||cc<=0)result.reason="sequence_optional_exhausted";
   else{attempted=true;result=ref->try_refine(native_m,native,history,processed,search,false,{},probe?StopPolicy::AuditAll:StopPolicy::FirstCovered,&scores,identity);}
   Json rec={{"native_event_id",processed},{"source_assignment",assignment_json(native_m)},{"source_assignment_sha",r6::sha256(assignment_json(native_m).dump())},{"output_history_identity",identity},{"output_history_version",version},{"configuration",configuration},{"stop_policy",probe?"AuditAll":"FirstCovered"},{"first_output_identity",processed==1},{"preprocess_eligible",pre_eligible},{"preprocess_total_cpu",pc},{"preprocess_total_wall",pw},{"event_cpu_cap",cc},{"event_wall_cap",cw},{"search_soft_cpu",search.max_cpu},{"search_soft_wall",search.max_wall},{"first_complete",result.first_complete},{"first_preserved_covered",result.first_preserved_covered},{"historical_cpu_credit_proven",false},{"native_gain",result.baseline_scored?Json{{"covered",result.base_gain.covered},{"observed",result.base_gain.observed}}:Json(nullptr)},{"cancellation",result.cancellation},{"reason",result.reason},{"completed_evaluations",result.completed_evaluations},{"history_mode",l1?"native_prefix":"actual_output"}};
   rec["protected_missing"]=0;rec["delivered_gain"]=nullptr;rec["proposed_replacement"]=bool(result.chosen);rec["candidate_assignment"]=result.chosen?assignment_json(result.chosen->assignment):Json(nullptr);rec["candidate_gain"]=result.chosen?Json{{"covered",result.chosen->gain.covered},{"observed",result.chosen->gain.observed}}:Json(nullptr);
   try{if(result.chosen)transaction.prepare(*result.chosen,total);}catch(Exhausted const& e){transaction.rejection=e.what();}
   {StageScope stage(&trace,RepairStage::SerializeResult);auto row=refinement_json(result);row["kind"]="event_proposed";row["native_event_id"]=processed;row["native_assignment"]=assignment_json(native_m);row["state"]="proposed";row["configuration"]=configuration;emit(row);}
   // All complete candidates, observations, losses and targets are durable before any output commit.
   {StageScope stage(&trace,RepairStage::DeliveryCleanup);result=RefinementResult{};}
   emit({{"kind","event_cost_proposed"},{"native_event_id",processed},{"cpu_before_record",total.cpu()},{"wall_before_record",total.wall()},{"trace",trace.json()}});
   rec["delivery_ready_cpu"]=total.cpu();rec["delivery_ready_wall"]=total.wall();double tailc=cpu_now(),tailw=wall_now();
   if(transaction.rejection.empty())transaction.decide(total,pre_eligible,l1);
   transaction.recheck(total);
   bool delivery=transaction.delivered,eligible=transaction.eligible;std::string reject=transaction.rejection;
   // Dispose search/serialization/staging objects before the outer cap measurement.
   {StageScope cleanup(&trace,RepairStage::DeliveryCleanup);transaction.release_before_outer_check();}
   rec["delivery_ready_cpu"]=total.cpu();rec["delivery_ready_wall"]=total.wall();
   auto rebuild_previous=[&](){
       double rw=wall_now(),rc=cpu_now();OutputLedger restored(ast.nodes.size());WorkBudget cleanup;
       for(unsigned k=0;k+1<processed;++k){auto const& prior=receipts[k];auto m=assignment_from(prior.at("actually_delivered").get<bool>()?prior.at("candidate_assignment"):data.at("models").at(k));auto t=observe_official(ast,m,cleanup);if(!restored.unique.count(assignment_key(m)))restored.commit(m,t);}
       history=std::move(restored);scores.valid=false;auto& rr=receipts[processed-1].is_null()?rec:receipts[processed-1];rr["rollback_cpu"]=cpu_now()-rc;rr["rollback_wall"]=wall_now()-rw;
   };
   auto cap_failed=[&](){return total.cpu()>=cc||total.wall()>=cw;};
   if(eligible&&cap_failed()){if(delivery)rebuild_previous();delivery=false;eligible=false;reject="delivery_tail_overrun";}
   rec["budget_eligible"]=eligible;rec["actually_delivered"]=delivery;rec["delivery_rejection"]=reject;rec["event_tail_cpu"]=cpu_now()-tailc;rec["event_tail_wall"]=wall_now()-tailw;
   rec["event_total_cpu"]=0.;rec["event_total_wall"]=0.;rec["overrun_cpu"]=0.;rec["overrun_wall"]=0.;rec["attempted"]=attempted;
   receipts[processed-1]=std::move(rec);
   // Publication may itself allocate. If it exceeds the cap, reconstruct only from actual prior outputs.
   if(eligible&&cap_failed()){if(delivery)rebuild_previous();delivery=false;eligible=false;reject="delivery_tail_overrun";}
   auto& done=receipts[processed-1];done["budget_eligible"]=eligible;done["actually_delivered"]=delivery;done["delivery_rejection"]=reject;
   double ec=total.cpu(),ew=total.wall();
   if(eligible&&(ec>=cc||ew>=cw)){if(delivery)rebuild_previous();delivery=false;eligible=false;done["budget_eligible"]=false;done["actually_delivered"]=false;done["delivery_rejection"]="delivery_tail_overrun";ec=total.cpu();ew=total.wall();}
   done["event_total_cpu"]=ec;done["event_total_wall"]=ew;done["overrun_cpu"]=std::max(0.0,ec-cc);done["overrun_wall"]=std::max(0.0,ew-cw);
   used_c+=ec;used_w+=ew;
   // Only the old basic ledger operation and prefix comparison are mandatory.
   mw=wall_now();mc=cpu_now();if(!delivery){if(!history.unique.count(assignment_key(native_m)))history.commit(native_m,native);}bool inclusion=contains(history.observations,native_history);if(!inclusion)throw std::runtime_error("prefix observation loss");
   auto ncov=native_history.covered(),ocov=history.observations.covered(),ocount=history.committed_count;
   double mandatory_event_w=wall_now()-mw,mandatory_event_c=cpu_now()-mc;mandatory_w+=mandatory_event_w;mandatory_c+=mandatory_event_c;
   done["prefix_contains_native"]=inclusion;done["native_covered"]=ncov;done["output_covered"]=ocov;done["output_count"]=ocount;
   // Measure all receipt work after subtracting only that old mandatory block.
   double outer_c=total.cpu()-mandatory_event_c,outer_w=total.wall()-mandatory_event_w;
   if(eligible&&(outer_c>=cc||outer_w>=cw)){
       if(delivery){rebuild_previous();WorkBudget fallback;auto key=assignment_key(native_m);if(!history.unique.count(key))history.commit(native_m,native);}
       eligible=false;delivery=false;done["budget_eligible"]=false;done["actually_delivered"]=false;done["delivery_rejection"]="delivery_tail_overrun";
       done["output_covered"]=history.observations.covered();done["output_count"]=history.committed_count;
       outer_c=total.cpu()-mandatory_event_c;outer_w=total.wall()-mandatory_event_w;
   }
   used_c+=outer_c-ec;used_w+=outer_w-ew;done["event_total_cpu"]=outer_c;done["event_total_wall"]=outer_w;done["overrun_cpu"]=std::max(0.,outer_c-cc);done["overrun_wall"]=std::max(0.,outer_w-cw);
   done["measurement_margin_cpu"]=cc-outer_c;done["measurement_margin_wall"]=cw-outer_w;
   postlude_start_c=cpu_now();postlude_start_w=wall_now();

  }
  finalize_postlude();double summary_c=cpu_now(),summary_w=wall_now();Json finalized=Json::array();for(unsigned i=0;i<processed;++i)finalized.push_back(std::move(receipts[i]));
  emit({{"kind","summary"},{"receipts",finalized},{"effective_preprocess_status",pre_status},{"preprocess_eligible",pre_eligible},{"preprocess_total_cpu",pc},{"preprocess_total_wall",pw},{"processed_models",processed},{"optional_cpu",used_c},{"optional_wall",used_w},{"mandatory_cpu",mandatory_c},{"mandatory_wall",mandatory_w},{"native_covered",native_history.covered()},{"output_covered",history.observations.covered()},{"output_count",history.committed_count},{"process_cpu_before_final_record",cpu_now()-all_c},{"process_wall_before_final_record",wall_now()-all_w},{"historical_cpu_credit_proven",false}});
  std::ofstream tail(directory+"/outer_tail.json");tail<<Json{{"summary_cpu",cpu_now()-summary_c},{"summary_wall",wall_now()-summary_w},{"last_monotonic",wall_now()},{"last_thread_cpu",cpu_now()},{"last_record_self_tail","parent measured, not zero"}}.dump()<<'\n';return 0;
 }catch(std::exception const& e){emit({{"kind","failure"},{"error",e.what()}});return 1;}
}
