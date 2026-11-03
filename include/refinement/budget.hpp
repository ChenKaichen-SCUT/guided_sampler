#pragma once
#include <boost/multiprecision/cpp_int.hpp>
#include <chrono>
#include <ctime>
#include <functional>
#include <limits>
#include <stdexcept>
#include <algorithm>
#include "cost_trace.hpp"
namespace refinement {
using Big=boost::multiprecision::cpp_int;
using Clock=std::chrono::steady_clock;
inline double wall_now(){return std::chrono::duration<double>(Clock::now().time_since_epoch()).count();}
inline double cpu_now(){timespec t{};if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))throw std::runtime_error("thread CPU clock unavailable");return t.tv_sec+t.tv_nsec*1e-9;}
struct Exhausted:std::runtime_error{using std::runtime_error::runtime_error;};
struct Unsupported:std::runtime_error{using std::runtime_error::runtime_error;};
struct WorkBudget {
    double start_wall=wall_now(),start_cpu=cpu_now();
    double max_wall=std::numeric_limits<double>::infinity(),max_cpu=std::numeric_limits<double>::infinity();
    unsigned integer_bits=0;std::function<bool()> cancelled;CostTrace* trace=nullptr;
    WorkBudget()=default;
    WorkBudget(double w,double c,unsigned bits=4096):max_wall(w),max_cpu(c),integer_bits(bits){}
    double wall()const{return wall_now()-start_wall;}
    double cpu()const{return cpu_now()-start_cpu;}
    [[noreturn]] void exhausted(char const* why)const{if(trace){if(trace->active)trace->active->mark_incomplete();trace->last_incomplete=trace->stage;trace->last_node=trace->current_node;trace->last_direction=trace->current_direction;}throw Exhausted(why);}
    void check()const{if(trace)if(auto r=trace->record())++r->budget_checks;if(cancelled&&cancelled())exhausted("cancelled");if(wall()>=max_wall)exhausted("wall_budget_exhausted");if(cpu()>=max_cpu)exhausted("cpu_budget_exhausted");}
    void bits(Big const& v)const{if(integer_bits&&v!=0&&boost::multiprecision::msb(v<0?Big(-v):v)>=integer_bits)exhausted("integer_bit_limit");}
    void integer(Big const& v)const{check();bits(v);}
};
struct BudgetLedger {
    double session=120,native_wall=0,native_cpu=0,optional_wall=0,optional_cpu=0,mandatory_wall=0,mandatory_cpu=0;
    double preprocess_wall=0,preprocess_cpu=0,event_wall=0,event_cpu=0,log_wall=0,log_cpu=0,overrun_wall=0,overrun_cpu=0;
    std::function<bool()> cancelled;
    bool preprocess_attempted=false,disabled=false;
    explicit BudgetLedger(double s=120):session(s){}
    double available_wall()const{return std::max(0.0,std::min(0.05*session,0.10*native_wall)-optional_wall);}
    double available_cpu()const{return std::max(0.0,std::min(0.05*session,0.10*native_cpu)-optional_cpu);}
    bool can_start(double remaining)const{return !disabled&&remaining>=0.010&&available_wall()>0&&available_cpu()>0;}
    WorkBudget budget(bool preprocess,double remaining)const{WorkBudget b(std::min({preprocess?0.100:0.020,available_wall(),std::max(0.0,remaining-0.010)}),std::min(preprocess?0.100:0.020,available_cpu()));b.cancelled=cancelled;return b;}
    void charge(WorkBudget const& b,bool preprocess=false){double w=b.wall(),c=b.cpu();optional_wall+=w;optional_cpu+=c;(preprocess?preprocess_wall:event_wall)+=w;(preprocess?preprocess_cpu:event_cpu)+=c;overrun_wall+=std::max(0.0,w-b.max_wall);overrun_cpu+=std::max(0.0,c-b.max_cpu);}
};
inline Big abs_big(Big const& a){return a<0?Big(-a):a;}
inline Big gcd_big(Big a,Big b){a=abs_big(a);b=abs_big(b);while(b!=0){Big r=a%b;a=b;b=r;}return a;}
inline Big floor_div(Big const& a,Big const& b){if(b==0)throw std::domain_error("division by zero");Big q=a/b,r=a%b;if(r!=0&&((r<0)!=(b<0)))--q;return q;}
inline Big ceil_div(Big const& a,Big const& b){return -floor_div(-a,b);}
inline Big floor_mod(Big const& a,Big const& m){if(m<=0)throw std::domain_error("nonpositive modulus");Big r=a%m;return r<0?Big(r+m):r;}
inline uint64_t low64(Big const& v){return floor_mod(v,Big(1)<<64).convert_to<uint64_t>();}
inline Big checked_add(Big const& a,Big const& c,WorkBudget& b){b.check();b.bits(a);b.bits(c);Big r=a+c;b.bits(r);return r;}
inline Big checked_mul(Big const& a,Big const& c,WorkBudget& b){b.check();b.bits(a);b.bits(c);Big r=a*c;b.bits(r);return r;}
inline Big checked_gcd(Big a,Big c,WorkBudget& b){a=abs_big(a);c=abs_big(c);while(c!=0){b.check();Big r=a%c;a=c;c=r;}return a;}
}
