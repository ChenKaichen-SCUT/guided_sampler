#include "refinement/refiner.hpp"
#include "refinement/line_blocking.hpp"
#include <fstream>
#include <iostream>
#include "round6/sha256.hpp"
using namespace refinement;
static Json coefficients(IntegerVector const& d){Json out=Json::array();for(auto const& [v,c]:d)out.push_back({v,c.str()});return out;}
int main(int argc,char** argv){
 if(argc!=5)return 2;std::ofstream stream(std::string(argv[4])+"/stream.jsonl");auto emit=[&](Json const& j){stream<<j.dump()<<'\n';stream.flush();if(!stream)throw std::runtime_error("diagnostic write failed");};
 WorkBudget global(25,25);unsigned position=std::stoul(argv[3]);
 try{
  double pw=wall_now(),pc=cpu_now();Json data,config;{std::ifstream f(argv[1]);f>>data;}{std::ifstream f(argv[2]);f>>config;}
  auto request=*std::find_if(config["real_requests"].begin(),config["real_requests"].end(),[&](auto const& r){return r["position"]==position;});
  if(r6::sha256(data["ast"].dump())!=request["ast_sha256"]||r6::sha256(data["models"].at(position-1).dump())!=request["anchor_sha256"])throw std::runtime_error("real formula/anchor SHA mismatch");
  auto ast=ast_from_json(data["ast"],global);auto anchor=assignment_from(data["models"].at(position-1));if(assignment_json(anchor)!=request["anchor"])throw std::runtime_error("wrong real anchor identity");
  OutputLedger history(ast.nodes.size());for(unsigned k=0;k+1<position;++k){auto m=assignment_from(data["models"][k]);auto t=observe_official(ast,m,global);if(!history.unique.count(assignment_key(m)))history.commit(m,t);}
  auto base=observe_official(ast,anchor,global);auto protect=make_protected(base,history.observations,global);auto native_gain=marginal_gain(base,history.observations,global);
  emit({{"kind","input"},{"position",position},{"anchor",assignment_json(anchor)},{"ast_sha256",request["ast_sha256"]},{"anchor_sha256",request["anchor_sha256"]},{"hard_conditions","none"},{"parse_prefix_cpu",cpu_now()-pc},{"parse_prefix_wall",wall_now()-pw},{"protected_count",protect.count},{"native_gain",{native_gain.covered,native_gain.observed}}});
  WorkBudget pre(std::min(2.,global.max_wall-global.wall()),std::min(2.,global.max_cpu-global.cpu()));CostTrace pre_trace;pre.trace=&pre_trace;std::unique_ptr<Refiner> ref;
  try{ref=std::make_unique<Refiner>(ast,pre,RepairMode::ValueCache);emit({{"kind","metadata"},{"metadata",ref->metadata()}});pre.check();}catch(Exhausted const& e){emit({{"kind","preprocess"},{"status","incomplete"},{"reason",e.what()},{"cpu",pre.cpu()},{"wall",pre.wall()},{"trace",pre_trace.json()}});emit({{"kind","summary"},{"status","preprocess_incomplete"},{"original_not_started",16},{"combination_not_started",request["combinations"].size()}});return 0;}
  emit({{"kind","preprocess"},{"status","complete"},{"cpu",pre.cpu()},{"wall",pre.wall()},{"trace",pre_trace.json()}});
  for(auto const& old:request["selected"]){auto const& d=ref->pool.directions.at(old["id"].get<unsigned>());if(coefficients(d.values)!=old["coefficients"]||d.component!=old["component"]||d.affected!=old["affected"].get<std::vector<unsigned>>())throw std::runtime_error("old selected direction identity mismatch");}
  std::set<std::string> pool_keys,combination_keys;for(auto const& d:ref->pool.directions)pool_keys.insert(direction_key(d.values));std::map<unsigned,bool> originals_verified;Json costs=Json::array();
  auto run=[&](IntegerVector const& direction,Json id,WorkBudget& phase,double cap){
   double cw=std::max(0.,std::min({cap,phase.max_wall-phase.wall(),global.max_wall-global.wall()})),cc=std::max(0.,std::min({cap,phase.max_cpu-phase.cpu(),global.max_cpu-global.cpu()}));
   Json row=id;row["coefficients"]=coefficients(direction);row["hard_conditions"]="none";row["root_complete"]=false;row["certificate_complete"]=false;row["nonzero_domain_found"]=false;row["legal_witness_verified"]=false;row["preserved"]=false;row["covered_gain"]=false;
   WorkBudget b(cw,cc);CostTrace trace;b.trace=&trace;RecordedDomainEvidence sink;bool blocked=false;
   if(cw<=0||cc<=0)row["status"]="not_started";
   else try{
    row["all_equality_dots"]=full_equality_dots(ref->equalities,direction,b);AnchorValues values(ref->ir,anchor,position,b);LineDomain line(ref->ir,anchor,direction,b,&values,nullptr,&sink);
    IntervalUnion domain;{StageScope stage(&trace,RepairStage::FormulaDomain);domain=line.formula();b.check();}
    row["root_complete"]=true;row["root_cpu"]=b.cpu();row["root_wall"]=b.wall();row["root_domain"]=domain_json(domain);blocked=singleton_zero(domain);row["status"]=blocked?"singleton_zero":"has_nonzero";
    row["certificate"]=std::move(sink.nodes);row["certificate_storage_allowance"]=sink.accounted_bytes;b.check();row["certificate_complete"]=true;
    if(auto t=nearest_nonzero(domain)){
     row["nonzero_domain_found"]=true;row["parameter"]=t->str();Assignment candidate=anchor;for(auto const& [v,c]:direction){b.check();candidate[v]=checked_add(anchor[v],checked_mul(c,*t,b),b);}row["assignment"]=assignment_json(candidate);
     {StageScope stage(&trace,RepairStage::ValidateFormula);if(!evaluate(ast,candidate,b,false).legal)throw std::runtime_error("illegal diagnostic witness");b.check();}row["legal_witness_verified"]=true;
     ObservationTrace observations;{StageScope stage(&trace,RepairStage::OfficialObserve);observations=observe_official(ast,candidate,b);}row["actual_observations"]=trace_json(observations);auto lost=missing(protect,observations,b);auto gain=marginal_gain(observations,history.observations,b);b.check();row["protected_missing"]=lost;row["gain"]={gain.covered,gain.observed};row["preserved"]=lost.empty();row["covered_gain"]=lost.empty()&&gain.covered>native_gain.covered;
    }
   }catch(Unsupported const& e){row["status"]="unsupported";row["reason"]=e.what();}catch(Exhausted const& e){row["status"]="incomplete";row["reason"]=e.what();if(!row.contains("certificate"))row["partial_certificate"]=std::move(sink.nodes);}
   row["trace"]=trace.json();row["cpu_before_record"]=b.cpu();row["wall_before_record"]=b.wall();emit(row);row=nullptr;sink.nodes=nullptr;
   bool within=b.cpu()<cc&&b.wall()<cw;costs.push_back({{"request",id},{"cpu",b.cpu()},{"wall",b.wall()},{"cpu_cap",cc},{"wall_cap",cw},{"within_request_cap",within}});
   return blocked&&within;
  };
  WorkBudget originals(std::min(8.,global.max_wall-global.wall()),std::min(8.,global.max_cpu-global.cpu()));
  for(auto const& old:request["selected"]){unsigned id=old["id"];originals_verified[id]=run(ref->pool.directions.at(id).values,{{"kind","original"},{"direction_id",id},{"old_domain",old["old_domain"]}},originals,.5);}
  emit({{"kind","original_phase"},{"cpu",originals.cpu()},{"wall",originals.wall()}});
  WorkBudget combinations(std::min(8.,global.max_wall-global.wall()),std::min(8.,global.max_cpu-global.cpu()));unsigned ordinal=0;
  for(auto const& pair:request["combinations"]){Json id={{"kind","combination"},{"ordinal",ordinal++},{"pair",pair},{"parents_reconfirmed_blocked",originals_verified[pair["left"].get<unsigned>()]&&originals_verified[pair["right"].get<unsigned>()]}};
   if(combinations.wall()>=combinations.max_wall||combinations.cpu()>=combinations.max_cpu||global.wall()>=global.max_wall){id["status"]="not_started";emit(id);continue;}
   // Normalization is part of this request, included in the phase and per-request budget below.
   double nw=wall_now(),nc=cpu_now();WorkBudget normalize_budget(std::min({.25,combinations.max_wall-combinations.wall(),global.max_wall-global.wall()}),std::min({.25,combinations.max_cpu-combinations.cpu(),global.max_cpu-global.cpu()}));
   try{auto d=combine_direction(ref->pool.directions.at(pair["left"].get<unsigned>()).values,ref->pool.directions.at(pair["right"].get<unsigned>()).values,pair["sign"].get<int>(),normalize_budget);
    id["normalization_cpu"]=cpu_now()-nc;id["normalization_wall"]=wall_now()-nw;
    if(d.empty()){id["status"]="zero_vector";emit(id);continue;}auto key=direction_key(d);id["already_in_pool"]=pool_keys.count(key)!=0;
    if(!combination_keys.insert(key).second){id["status"]="duplicate_direction";id["coefficients"]=coefficients(d);emit(id);continue;}
    // Subtract both measured normalization clocks. The worker never renews a full 250ms window.
    double left=std::max(0.,.25-std::max(cpu_now()-nc,wall_now()-nw));run(d,id,combinations,left);
   }catch(Exhausted const& e){id["status"]="incomplete";id["reason"]=e.what();emit(id);}
  }
  emit({{"kind","summary"},{"status","completed_requests"},{"costs",costs},{"combination_phase_cpu",combinations.cpu()},{"combination_phase_wall",combinations.wall()},{"worker_cpu_before_final",global.cpu()},{"worker_wall_before_final",global.wall()},{"new_sampling",0},{"solver_checks",0},{"output_injection",false}});return 0;
 }catch(std::exception const& e){emit({{"kind","failure"},{"error",e.what()}});return 1;}
}
