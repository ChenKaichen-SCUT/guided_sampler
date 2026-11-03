#pragma once
#include "refiner.hpp"
namespace refinement {
// Owns both ledgers until the outer boundary has measured serialization and cleanup.
// A rollback swaps back the untouched snapshot, so the next event cannot see a late replacement.
class BudgetedDeliveryTransaction {
    OutputLedger& output;std::optional<OutputLedger> staged;bool swapped=false,prepared=false;
public:
    bool proposed=false,eligible=false,delivered=false;std::string rejection;
    explicit BudgetedDeliveryTransaction(OutputLedger& h):output(h){}
    void prepare(Candidate const& candidate,WorkBudget& b){
        StageScope stage(b.trace,RepairStage::SaveCandidate);proposed=true;b.check();staged.emplace(output);staged->commit(candidate.assignment,candidate.trace);b.check();prepared=true;
    }
    bool within(WorkBudget const& b)const{return b.wall()<b.max_wall&&b.cpu()<b.max_cpu;}
    void decide(WorkBudget const& b,bool pre_eligible,bool l1){
        if(!proposed)return;if(!prepared){rejection="delivery_preparation_incomplete";return;}if(!pre_eligible){rejection="preprocess_ineligible";return;}
        if(!within(b)){rejection="delivery_overrun";return;}eligible=true;
        if(!l1){std::swap(output,*staged);swapped=true;delivered=true;}
    }
    void recheck(WorkBudget const& b){if(eligible&&!within(b)){rollback();rejection="delivery_tail_overrun";}}
    void rollback(){if(swapped){std::swap(output,*staged);swapped=false;}eligible=false;delivered=false;}
    void release_before_outer_check(){staged.reset();swapped=false;}
};
}
