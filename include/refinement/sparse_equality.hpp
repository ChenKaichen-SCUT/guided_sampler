#pragma once
#include "affine_ir.hpp"
namespace refinement {
using EqualityIncidence=std::vector<std::vector<std::pair<unsigned,Big>>>;
inline void validate_incidence(EqualitySystem const& eq,EqualityIncidence const& uses,WorkBudget& b){
    for(unsigned v=0;v<uses.size();++v){unsigned previous=0;bool first=true;for(auto const& [r,c]:uses[v]){b.check();if(r>=eq.rows.size()||(!first&&r<=previous)||c==0)throw std::runtime_error("invalid equality incidence");
        auto it=eq.rows[r].coefficients.find(v);if(it==eq.rows[r].coefficients.end()||it->second!=c)throw std::runtime_error("wrong equality incidence");previous=r;first=false;}}
    size_t count=0,total=0;for(auto const& x:uses){b.check();count+=x.size();}for(auto const& row:eq.rows){b.check();for(auto const& [v,c]:row.coefficients){b.check();if(v>=uses.size()||c==0)throw std::runtime_error("invalid equality coefficient");++total;}}
    if(count!=total)throw std::runtime_error("missing equality incidence");
}
class SparseRowAccumulator {
    std::vector<Big> dots;std::vector<uint32_t> marks;std::vector<unsigned> touched;
public:
    uint32_t epoch=0;
    SparseRowAccumulator(size_t rows,WorkBudget& b):dots(rows),marks(rows){b.check();if(b.trace)b.trace->verify_slots+=rows;}
    void verify(IntegerVector const& d,EqualityIncidence const& uses,WorkBudget& b){
        touched.clear();if(epoch==UINT32_MAX){if(b.trace)b.trace->scan(marks.size());for(auto& x:marks){b.check();x=0;}epoch=1;}else ++epoch;
        for(auto const& [v,step]:d)for(auto const& [r,c]:uses.at(v)){
            if(marks.at(r)!=epoch){b.check();marks[r]=epoch;dots[r]=0;touched.push_back(r);if(b.trace)++b.trace->verify_touched;}
            dots[r]=checked_add(dots[r],checked_mul(c,step,b),b);if(b.trace)++b.trace->verify_multiply_adds;
        }
        std::sort(touched.begin(),touched.end());b.check();for(auto r:touched){b.check();if(dots[r]!=0)throw std::runtime_error("integer direction violates mandatory equality");}
        // Untouched rows have no coefficient in the direction support: their full dot product is identically zero.
    }
};
}
