#include "refinement/native_output_split.hpp"
#include <iostream>
#define REQUIRE(x) do{if(!(x))throw std::runtime_error(#x);}while(false)
using namespace refinement;
int main(){
    WorkBudget b;ObservationTrace a;a.values={Big(1),Big(0)};a.zero={0,1};a.one={1,0};a.legal=true;
    ObservationTrace hidden=a;hidden.values[1].reset();hidden.zero[1]=hidden.one[1]=0;
    ObservationHistory h(2);auto p=make_protected(a,h,b);REQUIRE(!preserves(p,hidden,b));REQUIRE(missing(p,hidden,b).size()==1);
    h.commit(hidden);auto pending=make_protected(a,h,b);REQUIRE(pending.count==1);REQUIRE(!preserves(pending,hidden,b)); // single side, not yet covered
    NativeOutputSplit split(2,120,Mode::Identity);auto first=split.accept({0},a);REQUIRE(first.accepted_for_native_history);REQUIRE(!split.deliver({0},a,false,false).committed);REQUIRE(split.output.committed_count==0&&split.native.accepted_count==1);
    REQUIRE(split.deliver({0},a,false,true).committed);REQUIRE(split.accept({0},a).native_duplicate);
    auto native2=split.accept({1},a);REQUIRE(native2.accepted_for_native_history);REQUIRE(split.deliver({2},a,true,true).committed);
    auto native3=split.accept({2},a);REQUIRE(native3.accepted_for_native_history);REQUIRE(split.deliver({2},a,false,true).output_duplicate);REQUIRE(split.native.accepted_count==3&&split.output.committed_count==2);
    REQUIRE(contains(split.output.observations,split.native.observations));
    WorkBudget cancelled;cancelled.cancelled=[](){return true;};bool caught=false;try{cancelled.check();}catch(Exhausted const&){caught=true;}REQUIRE(caught);
    WorkBudget bits(1,1);caught=false;try{checked_mul(Big(1)<<4095,Big(2),bits);}catch(Exhausted const&){caught=true;}REQUIRE(caught);
    BudgetLedger ledger(120);REQUIRE(!ledger.can_start(100));ledger.native_cpu=1;ledger.native_wall=2;REQUIRE(ledger.available_cpu()==0.1&&ledger.available_wall()==0.2);REQUIRE(!ledger.can_start(0.009));ledger.optional_cpu=0.1;REQUIRE(!ledger.can_start(10));
    ledger.cancelled=[](){return true;};auto cb=ledger.budget(false,100);caught=false;try{cb.check();}catch(Exhausted const& e){caught=std::string(e.what())=="cancelled";}REQUIRE(caught);
    IntervalUnion intervals;for(int i=0;i<4100;++i)intervals.push_back({Big(i*2),Big(i*2)});DomainBudget db{b};caught=false;try{normalize(intervals,db);}catch(Exhausted const& e){caught=std::string(e.what())=="domain_interval_limit";}REQUIRE(caught);
    std::cout<<"PASS protected Reach, first-side containment, separate duplicate ledgers, cancellation, integer cap, earned CPU AND wall budgets\n";
}
