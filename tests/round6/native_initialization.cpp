#include "sampler/sampler.h"
#include "util/memory_manager.h"
#include <cassert>
#include <iostream>
int main(){
    memory::initialize(0);unsetenv("GUIDED_R5_EXCHANGE_DIR");setenv("GUIDED_CCSS_STAGNATION_GUARD","1",1);
    sampler::ls_sampler s(0,2);s.make_lits_space(67);
    std::string t="0 true";s.build_lits(t);for(int i=1;i<=64;++i){t=std::to_string(i)+" b"+std::to_string(i);s.build_lits(t);}
    // A mixed LIA recipe avoids the inherited pure-Boolean use_pbs path,
    // which replaces _resolution_vars with an empty _tmp_vars vector.
    t="65 ( >= x 0 )";s.build_lits(t);t="66 ( <= x 100 )";s.build_lits(t);
    std::minstd_rand fixture(17);std::vector<std::vector<int>> cs;
    for(int k=0;k<512;++k){int a=fixture()%64+1,b=fixture()%64+1,c=fixture()%64+1;while(b==a)b=fixture()%64+1;while(c==a||c==b)c=fixture()%64+1;cs.push_back({a,-b,-c});}
    cs.push_back({65});cs.push_back({66});
    std::unordered_map<std::string,std::string> map;s.r6_begin(map);s.build_instance(cs,map);s.m_r6.guard.reset(true);
    unsigned strict=0,worse_or_equal=0;
    for(unsigned i=0;i<128;++i){s.m_r6.guard.tick(100*i);int prior=s.m_r6.guard.best_global_cost;auto last=s.m_r6.guard.last_global_improvement_step;s.initialize();auto state=s.r5_state(true);int native=state["best_cost"];
        assert(s.m_r6.guard.best_global_cost==native);
        if(native<prior){assert(s.m_r6.guard.last_global_improvement_step==100*i);if(i)++strict;}
        else {assert(s.m_r6.guard.last_global_improvement_step==last);++worse_or_equal;}
    }
    assert(strict>0&&worse_or_equal>0&&s.m_r6.guard.initialization_count==128);
    std::cout<<"strict_initialize_improvements="<<strict<<" non_global_initialize="<<worse_or_equal<<"\n";
}
