#pragma once
#include "directions.hpp"
#include "modular_hits.hpp"
#include <memory>
namespace refinement {
struct BitTarget{unsigned node=0,bit=0;bool desired=false;};
struct Candidate {Assignment assignment;ObservationTrace trace;CoverageGain gain;unsigned direction=0;Big parameter=0;};
struct RefinementResult {
    std::optional<Candidate> chosen,unprotected_chosen;
    Json candidates=Json::array(),directions=Json::array(),protected_masks=Json::array();
    CoverageGain base_gain;bool baseline_scored=false;uint64_t protected_count=0,completed_evaluations=0;
    std::string reason="no_strictly_better_candidate",cancellation;
    Json selected_direction_order=Json::array();
    double generation_wall=0,generation_cpu=0,validation_wall=0,validation_cpu=0,observation_wall=0,observation_cpu=0,selection_wall=0,selection_cpu=0;
};
inline bool tie_before(unsigned direction,Big const& t,Candidate const& best){return direction!=best.direction?direction<best.direction:abs_big(t)!=abs_big(best.parameter)?abs_big(t)<abs_big(best.parameter):t<best.parameter;}
inline bool bool_target(Node const& n){return n.op==Op::Eq||n.op==Op::Distinct||n.op==Op::Le||n.op==Op::Lt||n.op==Op::Ge||n.op==Op::Gt;}
class Refiner {
public:
    AffineIR ir;EqualitySystem equalities;DirectionPool pool;
    Refiner(Ast ast,WorkBudget& b,RepairMode mode=RepairMode::Legacy):ir(compile_affine_ir(std::move(ast),b,mode)),equalities(collect_mandatory_equalities(ir,b)),pool(build_integer_directions(ir,equalities,b)){
        if(!ir.ast.official_supported())throw Unsupported("official_observer_unsupported");
    }
    Json metadata()const{Json d=Json::array(),eq=Json::array();for(auto const& r:equalities.rows){Json c=Json::array();for(auto const& [i,v]:r.coefficients)c.push_back({i,v.str()});eq.push_back({{"coefficients",c},{"constant",r.constant.str()}});}for(auto const& x:pool.directions){Json c=Json::array();for(auto const& [i,v]:x.values)c.push_back({i,v.str()});d.push_back({{"id",x.id},{"component",x.component},{"coefficients",c},{"affected",x.affected}});}return {{"directions",d},{"equalities",eq},{"components",pool.components},{"omitted_directions",pool.omitted}};}
    RefinementResult try_refine(Assignment const& anchor,ObservationTrace const& base,OutputLedger const& output,uint64_t event,WorkBudget& b,bool component_only=false,std::vector<AffineIR> const& hard={})const{
        RefinementResult result;auto version=output.observations.version;std::set<std::string> evaluated{assignment_key(anchor)};
        struct State {unsigned dir;std::unique_ptr<LineDomain> domain;IntervalUnion legal;std::vector<BitTarget> targets;size_t next_target=0;std::vector<std::pair<Big,BitTarget>> pending;size_t next_parameter=0;bool exhausted=false,prepared=false;size_t record_index=0;};
        std::vector<State> states;ProtectedObservations protected_obs;Json pending_candidate;double pending_wall=0,pending_cpu=0;
        std::unique_ptr<AnchorValues> values;std::vector<std::unique_ptr<AnchorValues>> hard_values;
        try{
            double sw=wall_now(),sc=cpu_now();{StageScope stage(b.trace,RepairStage::Protect);protected_obs=make_protected(base,output.observations,b);}result.protected_count=protected_obs.count;{StageScope stage(b.trace,RepairStage::ScoreBase);result.base_gain=marginal_gain(base,output.observations,b);}result.baseline_scored=true;
            for(unsigned n=0;n<protected_obs.zero.size();++n)if(protected_obs.zero[n]||protected_obs.one[n])result.protected_masks.push_back({n,protected_obs.zero[n],protected_obs.one[n]});
            std::vector<unsigned> selected;{StageScope stage(b.trace,RepairStage::RankDirections);selected=select_directions(pool,ir.ast,output.observations,event,b);}result.selected_direction_order=selected;result.selection_wall+=wall_now()-sw;result.selection_cpu+=cpu_now()-sc;
            if(ir.mode!=RepairMode::Legacy){values=std::make_unique<AnchorValues>(ir,anchor,event,b);for(auto const& h:hard)hard_values.push_back(std::make_unique<AnchorValues>(h,anchor,event,b));}
            auto prepare_direction=[&](State& state){auto id=state.dir;auto& log=result.directions.at(state.record_index);log["status"]="incomplete";if(b.trace){b.trace->current_direction=id;b.trace->last_incomplete=RepairStage::Count;}double w=wall_now(),c=cpu_now();auto const& d=pool.directions[id];
                try{{StageScope stage(b.trace,RepairStage::FormulaDomain);b.check();state.domain=std::make_unique<LineDomain>(ir,anchor,d.values,b,values.get(),&d.affected);state.legal=state.domain->formula();
                    for(size_t hi=0;hi<hard.size();++hi){auto const& h=hard[hi];LineDomain hd(h,anchor,d.values,b,values?hard_values[hi].get():nullptr);state.legal=intersect(state.legal,hd.formula(),state.domain->work);}
                    if(!domain_contains(state.legal,0))throw std::runtime_error("native anchor violates real hard conditions");
                    if(component_only){auto i=std::find_if(state.legal.begin(),state.legal.end(),[](auto const& x){return (!x.lo||*x.lo<=0)&&(!x.hi||*x.hi>=0);});state.legal={*i};}
                    log["intervals"]=domain_json(state.legal);log["interval_count"]=state.legal.size();if(b.trace)++b.trace->completed_domains;}
                    StageScope targets_stage(b.trace,RepairStage::TargetSelection);
                    std::vector<BitTarget> targets;
                    for(auto node:d.affected){b.check();auto const& n=ir.ast.nodes[node];if(n.boolean){if(!bool_target(n))continue;}else {if(!ir.terms[node].supported)continue;auto term=state.domain->line_term(node);if(term.slope==0)continue;}
                        uint64_t want=(output.observations.zero[node]^output.observations.one[node])&n.mask();
                        while(want){unsigned bit=std::countr_zero(want);bool desired=(output.observations.zero[node]>>bit)&1;auto observed=desired?base.one[node]:base.zero[node];if(!((observed>>bit)&1))targets.push_back({node,bit,desired});want&=want-1;}
                    }
                    for(size_t k=0;k<std::min(size_t(8),targets.size());++k)state.targets.push_back(targets[(event+k)%targets.size()]);
                    log["eligible_targets"]=targets.size();log["selected_targets"]=Json::array();for(auto t:state.targets)log["selected_targets"].push_back({t.node,t.bit,t.desired});state.exhausted=state.targets.empty();log["status"]="supported";log["remaining_work_unknown"]=false;
                }catch(Unsupported const& e){log["status"]="unsupported";log["reason"]=e.what();log["remaining_work_unknown"]=false;state.exhausted=true;}catch(Exhausted const& e){std::string why=e.what();log["status"]="incomplete";log["cancellation"]=why;log["remaining_work_unknown"]=true;if(b.trace){log["stage"]=b.trace->last_incomplete==RepairStage::Count?Json(nullptr):Json(stage_names[unsigned(b.trace->last_incomplete)]);log["current_node"]=b.trace->last_node;log["work_counters_at_cancel"]=b.trace->json();}if(why!="domain_budget_exhausted"&&why!="domain_interval_limit"&&why!="integer_bit_limit")throw;state.exhausted=true;}
                result.generation_wall+=wall_now()-w;result.generation_cpu+=cpu_now()-c;state.prepared=true;
            };
            for(auto id:selected){State state;state.dir=id;state.record_index=result.directions.size();result.directions.push_back({{"direction_id",id},{"component",pool.directions[id].component},{"status","not_started"},{"remaining_work_unknown",true}});states.push_back(std::move(state));}
            bool active=true;while(active&&result.completed_evaluations<64){active=false;for(auto& state:states){if(result.completed_evaluations>=64)break;if(!state.prepared)result.directions.at(state.record_index)["status"]="incomplete";if(b.trace){b.trace->current_direction=state.dir;b.trace->current_node=-1;} {StageScope dispatch(b.trace,state.prepared?RepairStage::ModularHits:RepairStage::FormulaDomain);b.check();}if(!state.prepared)prepare_direction(state);if(state.exhausted)continue;active=true;auto const& direction=pool.directions[state.dir];
                    // One parameter per direction per round. No first direction can consume the event cap.
                    while(state.next_parameter>=state.pending.size()&&state.next_target<state.targets.size()){
                        auto target=state.targets[state.next_target++];StageScope modular_stage(b.trace,RepairStage::ModularHits);double w=wall_now(),c=cpu_now();HitResult hits;Json log={{"kind","target"},{"direction_id",state.dir},{"target_node",target.node},{"target_bit",target.bit},{"desired",target.desired}};
                        try{if(ir.ast.nodes[target.node].boolean){auto matching=state.domain->truth(target.node);if(!target.desired)matching=complement(matching,state.domain->work);hits=nearest_boolean_hits(intersect(state.legal,matching,state.domain->work),b);}else hits=nearest_modular_hits(state.domain->line_term(target.node),target.bit,target.desired,state.legal,b);
                            log["modular_status"]=hits.status;log["parameters"]=Json::array();for(auto const& t:hits.parameters){state.pending.emplace_back(t,target);log["parameters"].push_back(t.str());}
                        }catch(Exhausted const& e){std::string why=e.what();log["modular_status"]=why;log["search_complete"]=false;result.candidates.push_back(log);if(why=="domain_budget_exhausted"||why=="domain_interval_limit"||why=="integer_bit_limit"){state.exhausted=true;break;}throw;}
                        result.generation_wall+=wall_now()-w;result.generation_cpu+=cpu_now()-c;result.candidates.push_back(log);
                    }
                    if(state.exhausted||state.next_parameter>=state.pending.size()){state.exhausted=true;continue;}
                    auto [t,target]=state.pending[state.next_parameter++];Assignment candidate=anchor;Json log={{"kind","candidate"},{"direction_id",state.dir},{"component",direction.component},{"t",t.str()},{"target_node",target.node},{"target_bit",target.bit},{"desired",target.desired}};
                    pending_candidate=log;pending_wall=wall_now();pending_cpu=cpu_now();double w=wall_now(),c=cpu_now();{StageScope build_stage(b.trace,RepairStage::CandidateBuild);for(auto const& [v,step]:direction.values){b.check();candidate[v]=checked_add(anchor[v],checked_mul(t,step,b),b);}}auto key=assignment_key(candidate);log["assignment"]=assignment_json(candidate);result.generation_wall+=wall_now()-w;result.generation_cpu+=cpu_now()-c;
                    if(!evaluated.insert(key).second){log["reason"]="candidate_duplicate";log["candidate_wall"]=wall_now()-pending_wall;log["candidate_cpu"]=cpu_now()-pending_cpu;result.candidates.push_back(log);pending_candidate=nullptr;continue;}
                    if(result.completed_evaluations>=64)break;
                    try{
                        w=wall_now();c=cpu_now();ObservationTrace legal;bool hard_ok=true;{StageScope validation(b.trace,RepairStage::ValidateFormula);legal=evaluate(ir.ast,candidate,b,false);for(auto const& h:hard)if(!evaluate(h.ast,candidate,b,false).legal)hard_ok=false;}log["original_formula_valid"]=legal.legal;log["hard_conditions_valid"]=hard_ok;result.validation_wall+=wall_now()-w;result.validation_cpu+=cpu_now()-c;
                        if(!legal.legal||!hard_ok)throw std::runtime_error("domain claimed legal candidate but independent full evaluation failed");
                        w=wall_now();c=cpu_now();ObservationTrace trace;{StageScope observe(b.trace,RepairStage::OfficialObserve);trace=observe_official(ir.ast,candidate,b);}log["actual_observations"]=trace_json(trace);result.observation_wall+=wall_now()-w;result.observation_cpu+=cpu_now()-c;
                        w=wall_now();c=cpu_now();StageScope scoring(b.trace,RepairStage::PreserveAndScore);auto lost=missing(protected_obs,trace,b);auto gain=marginal_gain(trace,output.observations,b);bool duplicate=output.unique.count(key);log["missing_observations"]=lost;log["protected_missing_count"]=lost.size();log["output_duplicate"]=duplicate;log["gain_covered"]=gain.covered;log["gain_observed"]=gain.observed;
                        bool better=gain>result.base_gain;b.check();++result.completed_evaluations;if(b.trace)++b.trace->completed_candidates;
                        auto update=[&](std::optional<Candidate>& best){if(!best||gain>best->gain||(gain==best->gain&&tie_before(state.dir,t,*best)))best=Candidate{candidate,trace,gain,state.dir,t};};
                        if(!duplicate&&better)update(result.unprotected_chosen);
                        if(!lost.empty())log["reason"]="protected_observation_missing";else if(duplicate)log["reason"]="output_duplicate";else if(!better)log["reason"]="legal_not_better_than_native";else {log["reason"]="eligible_strict_improvement";update(result.chosen);}
                        result.selection_wall+=wall_now()-w;result.selection_cpu+=cpu_now()-c;log["candidate_wall"]=wall_now()-pending_wall;log["candidate_cpu"]=cpu_now()-pending_cpu;result.candidates.push_back(log);pending_candidate=nullptr;
                    }catch(Exhausted const& e){log["reason"]="incomplete_candidate";log["cancellation"]=e.what();log["candidate_wall"]=wall_now()-pending_wall;log["candidate_cpu"]=cpu_now()-pending_cpu;result.candidates.push_back(log);pending_candidate=nullptr;throw;}
                }}
            if(result.completed_evaluations>=64)result.cancellation="candidate_cap";
        }catch(Exhausted const& e){result.cancellation=e.what();if(b.trace&&b.trace->last_direction>=0){for(auto& log:result.directions)if(log["direction_id"]==b.trace->last_direction){log["cancellation"]=e.what();log["remaining_work_unknown"]=true;log["cancellation_stage"]=b.trace->last_incomplete==RepairStage::Count?Json(nullptr):Json(stage_names[unsigned(b.trace->last_incomplete)]);log["current_node"]=b.trace->last_node;if(log["status"]=="incomplete")log["work_counters_at_cancel"]=b.trace->json();}}if(!pending_candidate.is_null()){pending_candidate["reason"]="incomplete_candidate_generation";pending_candidate["cancellation"]=e.what();pending_candidate["candidate_wall"]=wall_now()-pending_wall;pending_candidate["candidate_cpu"]=cpu_now()-pending_cpu;result.candidates.push_back(pending_candidate);}}
        if(output.observations.version!=version)throw std::runtime_error("output history changed during refinement");
        if(result.chosen)result.reason=result.chosen->gain.covered>result.base_gain.covered?"strict_covered_improvement":"single_sided_observation_only";
        else if(pool.directions.empty())result.reason="no_integer_direction";
        return result;
    }
};
inline Json refinement_json(RefinementResult const& r){Json j={{"selected_direction_order",r.selected_direction_order},{"reason",r.reason},{"cancellation",r.cancellation},{"base_gain_covered",r.baseline_scored?Json(r.base_gain.covered):Json(nullptr)},{"base_gain_observed",r.baseline_scored?Json(r.base_gain.observed):Json(nullptr)},{"baseline_scored",r.baseline_scored},{"protected_count",r.protected_count},{"protected_masks",r.protected_masks},{"completed_evaluations",r.completed_evaluations},{"directions",r.directions},{"candidates",r.candidates},{"generation_wall",r.generation_wall},{"generation_cpu",r.generation_cpu},{"validation_wall",r.validation_wall},{"validation_cpu",r.validation_cpu},{"observation_wall",r.observation_wall},{"observation_cpu",r.observation_cpu},{"selection_wall",r.selection_wall},{"selection_cpu",r.selection_cpu}};
    auto pack=[](Candidate const& c){return Json{{"assignment",assignment_json(c.assignment)},{"trace",trace_json(c.trace)},{"gain_covered",c.gain.covered},{"gain_observed",c.gain.observed},{"direction",c.direction},{"t",c.parameter.str()}};};j["chosen"]=r.chosen?pack(*r.chosen):Json(nullptr);j["unprotected_chosen"]=r.unprotected_chosen?pack(*r.unprotected_chosen):Json(nullptr);return j;
}
}
