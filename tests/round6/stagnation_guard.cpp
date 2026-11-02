#include "stagnation_guard.hpp"
#include "sha256.hpp"
#include <cassert>
#include <iostream>
int main(){
    using r6::StagnationGuard;StagnationGuard g;g.reset(true);g.observe(100);
    g.tick(65535);assert(!g.should_yield(100));g.tick(65536);assert(g.should_yield(100));assert(g.max_stagnation_steps==65536);
    g.reset(true);g.observe(100);g.tick(30000);g.observe(80);g.tick(60000);g.observe(80);g.observe(90);g.tick(95535);assert(!g.should_yield(90));g.tick(95536);assert(g.should_yield(90));assert(g.last_global_improvement_step==30000);
    g.reset(true);g.observe(100);g.tick(65536);g.observe(0);assert(!g.should_yield(0));assert(g.last_global_improvement_step==65536);
    g.reset(true);g.observe(100);g.tick(65536);assert(!g.should_yield(0));
    g.reset(false);g.observe(100);g.tick(1000000);assert(!g.should_yield(100));
    g.reset(true);g.observe(100);g.tick(60000);++g.initialization_count;g.observe(101);assert(g.last_global_improvement_step==0);g.observe(99);assert(g.last_global_improvement_step==60000);g.tick(125535);assert(!g.should_yield(99));g.tick(125536);assert(g.should_yield(99));
    assert(r6::sha256("")=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    assert(r6::sha256("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    assert(r6::sha256(std::string(1000000,'a'))=="cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
    std::cout<<"global/restart/zero/disabled/call-reset/SHA passed\n";
}
