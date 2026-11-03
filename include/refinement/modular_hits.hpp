#pragma once
#include "line_domain.hpp"
namespace refinement {
inline Big floor_sum(Big n,Big m,Big a,Big c,WorkBudget& b){
    if(n<0||m<=0)throw std::domain_error("invalid floor_sum domain");b.integer(n);b.integer(m);b.integer(a);b.integer(c);
    Big qa=floor_div(a,m),qc=floor_div(c,m);Big triangular=checked_mul(n,Big(n-1),b)/2;Big answer=checked_add(checked_mul(triangular,qa,b),checked_mul(n,qc,b),b);b.integer(answer);a=floor_mod(a,m);c=floor_mod(c,m);
    for(;;){b.check();if(a>=m){answer=checked_add(answer,checked_mul(checked_mul(n,Big(n-1),b)/2,Big(a/m),b),b);a%=m;}if(c>=m){answer=checked_add(answer,checked_mul(n,Big(c/m),b),b);c%=m;}b.integer(answer);Big top=checked_add(checked_mul(a,n,b),c,b);b.integer(top);if(top<m)break;n=top/m;c=top%m;std::swap(m,a);}return answer;
}
inline Big count_residue_lt(Big const& n,Big const& m,Big const& a,Big const& c,Big const& u,WorkBudget& b){if(u<0||u>m)throw std::domain_error("residue bound");return n-(floor_sum(n,m,a,c+m-u,b)-floor_sum(n,m,a,c,b));}
inline Big count_residue_interval(Big const& start,Big const& length,Big const& a,Big const& c,Big const& m,Big const& lo,Big const& hi,WorkBudget& b){if(length<0||m<=0||lo<0||hi>=m||hi<lo)throw std::domain_error("residue interval");b.check();Big a0=floor_mod(a,m),c0=floor_mod(checked_add(c,checked_mul(a,start,b),b),m);return count_residue_lt(length,m,a0,c0,hi+1,b)-count_residue_lt(length,m,a0,c0,lo,b);}
inline std::optional<Big> first_hit_in_finite_interval(Big const& start,Big const& length,Big const& a,Big const& c,Big const& m,Big const& lo,Big const& hi,WorkBudget& b){
    if(length<=0||count_residue_interval(start,length,a,c,m,lo,hi,b)==0)return std::nullopt;Big left=1,right=length;
    while(left<right){b.check();Big mid=(left+right)/2;if(count_residue_interval(start,mid,a,c,m,lo,hi,b)>0)right=mid;else left=mid+1;}return start+left-1;
}
struct HitResult{std::vector<Big> parameters;std::string status="complete_no_hit_in_domain";bool search_complete=true;};
inline HitResult nearest_modular_hits(LineTerm const& term,unsigned bit,bool desired,IntervalUnion const& legal,WorkBudget& b){
    if(bit>63)throw std::domain_error("official bit index");HitResult out;DomainBudget db{b};Big half=Big(1)<<bit,m=half*2,lo=desired?half:Big(0),hi=desired?Big(m-1):Big(half-1);Big period=term.slope==0?Big(1):Big(m/gcd_big(term.slope,m));
    bool any_nonempty=false,period_unreachable=false;
    for(int sign:{1,-1}){
        auto u=sign==1?legal:reflect(legal,db);u=intersect(u,{{Big(1),std::nullopt}},db);Big slope=sign==1?term.slope:Big(-term.slope);unsigned hits=0;
        for(auto const& interval:u){b.check();any_nonempty=true;Big cursor=*interval.lo;
            while(hits<2&&(!interval.hi||cursor<=*interval.hi)){
                b.check();Big length=period;if(interval.hi)length=std::min(length,Big(*interval.hi-cursor+1));auto hit=first_hit_in_finite_interval(cursor,length,slope,term.constant,m,lo,hi,b);
                if(!hit){if(length==period)period_unreachable=true;break;}out.parameters.push_back(sign==1?*hit:Big(-*hit));++hits;cursor=*hit+1;
            }if(hits==2)break;
        }
    }
    std::sort(out.parameters.begin(),out.parameters.end(),[](Big const& a,Big const& c){Big x=abs_big(a),y=abs_big(c);return x!=y?x<y:a<c;});out.parameters.erase(std::unique(out.parameters.begin(),out.parameters.end()),out.parameters.end());
    out.status=!out.parameters.empty()?"bounded_hits_found":!any_nonempty?"no_nonzero_legal_parameter":period_unreachable?"exact_period_unreachable":"complete_no_hit_in_domain";return out;
}
inline HitResult nearest_boolean_hits(IntervalUnion const& matches,WorkBudget& b){HitResult out;DomainBudget db{b};for(int sign:{1,-1}){auto u=sign==1?matches:reflect(matches,db);u=intersect(u,{{Big(1),std::nullopt}},db);unsigned count=0;for(auto const& i:u){Big p=*i.lo;while(count<2&&(!i.hi||p<=*i.hi)){b.check();out.parameters.push_back(sign==1?p:Big(-p));++p;++count;}if(count==2)break;}}
    std::sort(out.parameters.begin(),out.parameters.end(),[](Big const& a,Big const& c){return abs_big(a)!=abs_big(c)?abs_big(a)<abs_big(c):a<c;});out.status=out.parameters.empty()?"complete_no_hit_in_domain":"bounded_hits_found";return out;}
}
