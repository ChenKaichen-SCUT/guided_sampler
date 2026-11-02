#pragma once
#include <algorithm>
#include <climits>
#include <cstdint>
namespace r6 {
struct StagnationGuard {
    static constexpr uint64_t limit=65536;
    bool enabled=false,valid=false,yielded=false;
    uint64_t step=0,last_global_improvement_step=0,max_stagnation_steps=0;
    int initial_global_best=INT_MAX,best_global_cost=INT_MAX;
    unsigned initialization_count=0;
    void reset(bool on){*this=StagnationGuard();enabled=on;}
    void tick(uint64_t s){step=s;update_span();}
    void update_span(){if(valid)max_stagnation_steps=std::max(max_stagnation_steps,step-last_global_improvement_step);}
    void observe(int cost){
        update_span();
        if(!valid){valid=true;initial_global_best=cost;best_global_cost=cost;last_global_improvement_step=step;}
        else if(cost<best_global_cost){best_global_cost=cost;last_global_improvement_step=step;}
    }
    bool should_yield(unsigned unsat){
        update_span();
        if(enabled&&valid&&unsat!=0&&best_global_cost>0&&step-last_global_improvement_step>=limit){yielded=true;return true;}
        return false;
    }
};
}
