#pragma once
#include "observer.hpp"
namespace esg {
struct Pattern {
    z3::expr_vector definitions,goals,auxiliaries;
    std::vector<unsigned> bits;
    uint64_t mask=0,desired=0;
    explicit Pattern(z3::context& c):definitions(c),goals(c),auxiliaries(c){}
};
inline z3::expr fresh_int(z3::context& c,Pattern& p){
    z3::expr e(c,Z3_mk_fresh_const(c,"esg",c.int_sort()));p.auxiliaries.push_back(e);return e;
}
inline Pattern encode_pattern(z3::expr const& expression,z3::expr const& reach,uint64_t mask,uint64_t desired){
    auto& c=expression.ctx();Pattern p(c);p.mask=mask;p.desired=desired&mask;
    if(!mask)return p;
    if(expression.is_bool()){
        if(mask!=1)throw std::runtime_error("Bool pattern outside bit zero");
        p.goals.push_back(reach&&((desired&1)?expression:!expression));p.bits.push_back(0);return p;
    }
    unsigned width=64-__builtin_clzll(mask);
    auto numeral=[&](Int const& i){return c.int_val(decimal(i).c_str());};
    auto quotient=fresh_int(c,p);auto sum=numeral(Int(1)<<width)*quotient;
    for(unsigned start=0;start<width;){
        bool selected=((mask>>start)&1)!=0;unsigned end=start+1;
        if(!selected)while(end<width&&!((mask>>end)&1))++end;
        unsigned size=end-start;auto digit=fresh_int(c,p);
        p.definitions.push_back(digit>=0);p.definitions.push_back(digit<numeral(Int(1)<<size));
        sum=sum+numeral(Int(1)<<start)*digit;
        if(selected){p.bits.push_back(start);p.goals.push_back(reach&&(digit==int((desired>>start)&1)));}
        start=end;
    }
    p.definitions.push_back(expression==sum);return p;
}
}
