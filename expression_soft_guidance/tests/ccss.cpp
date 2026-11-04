#include "kernel_api.hpp"
#include <nlohmann/json.hpp>
#include <chrono>
#include <iostream>
void require(bool v,char const* why){if(!v)throw std::runtime_error(why);}
int main(){
    z3::context c;char const* names[]={"x","stale"};char const* values[]={"7","99"};
    require(Z3_expr_exchange(c,3,2,names,values)==2,"seed install");
    Z3_expr_exchange(c,1,0,nullptr,nullptr);
    char const* updated[]={"11"};
    require(Z3_expr_exchange(c,3,1,names,updated)==1,"replace must clear stale entries");
    require(!Z3_expr_exchange_value(c,"stale"),"stale entry survived replacement");
    require(std::string(Z3_expr_exchange_value(c,"x"))=="11","wrong new value");
    require(Z3_expr_exchange(c,2,0,nullptr,nullptr)==2,"held snapshot lost entries");
    require(std::string(Z3_expr_exchange_value(c,"x"))=="7","held map mixed old/new values");
    Z3_expr_exchange(c,3,0,nullptr,nullptr);
    auto x=c.int_const("x"),y=c.int_const("y");auto f=x>=0&&y>=0&&x+y==10;
    z3::params p(c);p.set("ls_sampling",true);p.set("auto_config",false);p.set("logic","QF_LIA");
    nlohmann::json runs=nlohmann::json::array();
    for(unsigned i=0;i<8;++i){
        auto s=z3::with(z3::tactic(c,"smt"),p).mk_solver();s.add(f);
        Z3_expr_ccss_begin(0.000001);auto start=std::chrono::steady_clock::now();auto r=s.check();double stats[8];Z3_expr_ccss_end(stats);
        double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        require(r==z3::unknown&&stats[6]==1,"CCSS deadline did not return unknown");
        require(elapsed<1.0,"tiny-budget call stalled");
        Z3_expr_ccss_begin(0);require(s.check()==z3::sat,"timeout polluted next CCSS call");
        require(s.get_model().eval(f,true).is_true(),"post-timeout model illegal");Z3_expr_ccss_end(stats);
        require(stats[6]==0,"expiry state leaked");runs.push_back({{"expired_wall",elapsed}});
    }
    std::cout<<nlohmann::json({{"passed",true},{"exchange_checks",7},{"deadline_recovery_checks",runs}}).dump(2)<<"\n";
}
