#include "pattern.hpp"
#include <iostream>
using namespace esg;
int main(){
    z3::context c;auto x=c.int_const("x"),y=c.int_const("y");auto sum=x+y;
    unsigned cases=0;
    for(uint64_t mask: {uint64_t(0),uint64_t(1),uint64_t(0x83),UINT64_MAX,uint64_t(1)<<63}){
        for(uint64_t desired: {uint64_t(0),uint64_t(0x82),UINT64_MAX}){
            auto p=encode_pattern(sum,c.bool_val(true),mask,desired);z3::solver s(c);s.add(p.definitions);
            for(int v=-260;v<=260;v+=13){
                s.push();s.add(sum==v);if(s.check()!=z3::sat)throw std::runtime_error("definition lost original model");
                auto m=s.get_model();
                for(unsigned i=0;i<p.bits.size();++i){bool wanted=((low64(Int(v))>>p.bits[i])&1)==((desired>>p.bits[i])&1);
                    if(m.eval(p.goals[i],true).is_true()!=wanted)throw std::runtime_error("bit decomposition mismatch");++cases;}
                s.pop();
            }
        }
    }
    auto p=encode_pattern(sum,c.bool_val(true),0x83,0x82);z3::solver s(c);s.add(p.definitions);s.add(p.goals);
    s.add(x>=0&&x<=100&&y>=0&&y<=100&&y==x+10);
    if(s.check()!=z3::sat)throw std::runtime_error("coordinated example failed");
    auto v=s.get_model().eval(sum,true);if((low64(parse_integer(v.to_string()))&0x83)!=0x82)throw std::runtime_error("example pattern");
    Observer o(z3::ite(x>0,(x+y),-y)==2);auto ev=o.evaluate({{"x",Int(1)},{"y",Int(1)}});
    if(!ev.legal)throw std::runtime_error("ite observer");
    std::cout<<Json({{"passed",true},{"bit_checks",cases},{"coordination_example",v.to_string()}}).dump()<<"\n";
}
