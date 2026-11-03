#pragma once
#include "refiner.hpp"
namespace refinement {
enum class Mode {Off,Identity,Observe,Improve};
inline Mode mode_from(std::string const& name){if(name=="off")return Mode::Off;if(name=="identity")return Mode::Identity;if(name=="observe")return Mode::Observe;if(name=="improve")return Mode::Improve;throw std::runtime_error("invalid refinement mode");}
struct NativeAcceptance {bool legal=false,native_duplicate=false,accepted_for_native_history=false;uint64_t native_event_id=0;Assignment assignment;ObservationTrace trace;};
struct DeliveryResult {bool committed=false,replaced=false,output_duplicate=false;std::string reason;};
class NativeOutputSplit {
public:
    NativeLedger native;OutputLedger output;BudgetLedger budget;Mode mode;RepairMode repair_configuration;
    uint64_t native_raw_count=0,output_duplicates=0,replacements=0,covered_replacements=0,deadline_missed_after_native_ready=0;
    std::unique_ptr<Refiner> refiner;std::string disabled_reason;
    NativeOutputSplit(size_t nodes,double seconds,Mode m):native(nodes),output(nodes),budget(seconds),mode(m),repair_configuration(repair_mode(std::getenv("REFINEMENT_REPAIR_MODE")?std::getenv("REFINEMENT_REPAIR_MODE"):"Legacy")){}
    NativeAcceptance accept(Assignment assignment,ObservationTrace trace){NativeAcceptance a;a.assignment=std::move(assignment);a.trace=std::move(trace);a.legal=a.trace.legal;++native_raw_count;if(!a.legal)throw std::runtime_error("illegal native assignment");a.accepted_for_native_history=native.accept(a.assignment,a.trace);a.native_duplicate=!a.accepted_for_native_history;a.native_event_id=native.accepted_count;return a;}
    template<typename BuildAst,typename SaveMetadata,typename BuildHard,typename SaveResult>
    RefinementResult choose(NativeAcceptance const& a,double remaining,BuildAst build,SaveMetadata save,BuildHard hard,SaveResult log){
        RefinementResult result;
        if(!a.accepted_for_native_history){result.reason="native_duplicate_no_refinement";return result;}
        if(a.native_event_id==1||output.committed_count==0){result.reason="first_output_identity";return result;}
        if(mode==Mode::Off||mode==Mode::Identity){result.reason="optional_refinement_disabled";return result;}
        if(!budget.can_start(remaining)){result.reason=budget.disabled?disabled_reason:remaining<0.010?"deadline_reserve":"no_earned_budget";return result;}
        if(!budget.preprocess_attempted){
            budget.preprocess_attempted=true;auto b=budget.budget(true,remaining);
            try{auto ast=build(b);refiner=std::make_unique<Refiner>(std::move(ast),b,repair_configuration);save(*refiner,b);b.check();}
            catch(Exhausted const& e){disabled_reason=e.what();budget.disabled=true;refiner.reset();}
            catch(Unsupported const& e){disabled_reason=e.what();budget.disabled=true;refiner.reset();}
            budget.charge(b,true);remaining-=b.wall();
        }
        if(!refiner){result.reason="preprocessing_disabled:"+disabled_reason;return result;}
        if(mode==Mode::Observe){result.reason="observe_only_no_candidates";return result;}
        if(!budget.can_start(remaining)){result.reason=remaining<0.010?"deadline_reserve":"no_earned_budget";return result;}
        auto b=budget.budget(false,remaining);
        try{auto hard_ir=hard(b);result=refiner->try_refine(a.assignment,a.trace,output,a.native_event_id,b,false,hard_ir);}
        catch(Exhausted const& e){result.reason="hard_condition_preparation_incomplete";result.cancellation=e.what();}
        catch(Unsupported const& e){result.reason=e.what();}
        double lw=wall_now(),lc=cpu_now();log(result,b);budget.log_wall+=wall_now()-lw;budget.log_cpu+=cpu_now()-lc;budget.charge(b);return result;
    }
    // The caller owns prepare/commit/confirm I/O. Native feedback has already
    // advanced, and failure here cannot undo or replace it.
    DeliveryResult deliver(Assignment const& assignment,ObservationTrace const& trace,bool replaced,bool transaction_confirmed){DeliveryResult r;r.replaced=replaced;r.output_duplicate=output.unique.count(assignment_key(assignment));
        if(r.output_duplicate){++output_duplicates;r.reason="output_duplicate";return r;}
        if(!transaction_confirmed){++deadline_missed_after_native_ready;r.reason="unconfirmed_or_late";return r;}
        output.commit(assignment,trace);r.committed=true;r.reason=replaced?"replacement_committed":"native_committed";if(replaced)++replacements;return r;
    }
};
}
