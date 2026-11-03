#pragma once
#include "line_domain.hpp"
namespace refinement {
class RecordedDomainEvidence:public DomainEvidenceSink {
public:
    Json nodes=Json::array();size_t accounted_bytes=0,limit=64u*1024u*1024u;
    void completed(unsigned id,Node const& n,IntervalUnion const& u,bool invariant,Json atoms,WorkBudget& b) override{
        b.check();Json row={{"node",id},{"operation",op_names()[unsigned(n.op)]},{"children",n.children},{"invariant",invariant},{"domain",domain_json(u)},{"comparisons",std::move(atoms)},{"complete",true}};
        // Deliberately conservative certificate storage allowance (JSON DOM + serialized form).
        size_t bytes=row.dump().size();if(bytes>(limit-accounted_bytes)/32)b.exhausted("evidence_limit");accounted_bytes+=bytes*32;nodes.push_back(std::move(row));b.check();
    }
};
inline bool singleton_zero(IntervalUnion const& u){return u.size()==1&&u[0].lo&&u[0].hi&&*u[0].lo==0&&*u[0].hi==0;}
inline std::optional<Big> nearest_nonzero(IntervalUnion const& u){
    std::optional<Big> best;auto consider=[&](Big t){if(t==0)return;if(!best||abs_big(t)<abs_big(*best)||(abs_big(t)==abs_big(*best)&&t<*best))best=t;};
    for(auto const& i:u){if(!i.hi||*i.hi>=1){Big t=i.lo?std::max(Big(1),*i.lo):Big(1);if(!i.hi||t<=*i.hi)consider(t);}
        if(!i.lo||*i.lo<=-1){Big t=i.hi?std::min(Big(-1),*i.hi):Big(-1);if(!i.lo||t>=*i.lo)consider(t);}}
    return best;
}
inline IntegerVector combine_direction(IntegerVector const& a,IntegerVector const& c,int sign,WorkBudget& b){
    IntegerVector out=a;for(auto const& [v,x]:c){b.check();out[v]=checked_add(out[v],checked_mul(sign,x,b),b);if(out[v]==0)out.erase(v);}
    Big gcd=0;for(auto const& [v,x]:out)gcd=checked_gcd(gcd,x,b);if(out.empty())return out;Big orientation=out.begin()->second<0?-1:1;
    for(auto& [v,x]:out){b.check();x=orientation*(x/gcd);b.integer(x);}return out;
}
inline Json full_equality_dots(EqualitySystem const& eq,IntegerVector const& d,WorkBudget& b){
    Json dots=Json::array();for(auto const& row:eq.rows){Big value=0;for(auto const& [v,c]:row.coefficients){b.check();auto it=d.find(v);if(it!=d.end())value=checked_add(value,checked_mul(c,it->second,b),b);}dots.push_back(value.str());if(value!=0)throw std::runtime_error("diagnostic direction violates equality");}return dots;
}
}
