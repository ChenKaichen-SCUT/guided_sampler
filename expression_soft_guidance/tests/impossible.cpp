#include "impossible.hpp"
#include <filesystem>
#include <iostream>
using namespace esg;
void require(bool v,char const* why){if(!v)throw std::runtime_error(why);}
int main(int argc,char** argv){
    std::string dir=argc>1?argv[1]:"/tmp/esg_impossible_test";std::filesystem::create_directories(dir);
    z3::context c;auto x=c.int_const("x"),y=c.int_const("y");
    auto product=c.int_val("-4294967296")*x;
    auto f=(x>=-8&&x<=7&&y>=-4&&y<=5)&&(product+x+y<c.int_val("1000000000000"))&&
        (z3::ite(x>0,4*y+1,8*x+1)<1000)&&(x-y<1000)&&(-x<1000);
    Observer o(f);ImpossibleBits filter(o,dir,1.0);uint64_t checks=0;
    for(int xv=-8;xv<=7;++xv)for(int yv=-4;yv<=5;++yv){
        z3::model m(o.context);auto xd=o.context.int_const("x").decl(),yd=o.context.int_const("y").decl();auto xx=o.context.int_val(xv),yy=o.context.int_val(yv);m.add_const_interp(xd,xx);m.add_const_interp(yd,yy);
        for(unsigned id=0;id<o.nodes.size();++id){auto const& n=o.nodes[id];auto v=m.eval(n.expr,true);Int value=n.boolean?Int(v.is_true()):parse_integer(v.to_string());auto const& fact=filter.get(id);
            require((low64(value)&fact.mask)==fact.value,"static filter removed a feasible bit side");
            if(fact.lower)require(value>=*fact.lower,"invalid lower bound");if(fact.upper)require(value<=*fact.upper,"invalid upper bound");++checks;
        }
    }
    bool product_checked=false;
    for(unsigned id=0;id<o.nodes.size();++id)if(o.nodes[id].expr.to_string()==product.to_string()){
        auto fact=filter.get(id);require((fact.mask&0xffffffffULL)==0xffffffffULL&&(fact.value&0xffffffffULL)==0,"multiple of 2^32 was not recognized");product_checked=true;}
    require(product_checked,"missing multiplication target");
    // x+y is even under F, but x itself can be either parity. There are no
    // inherited assumptions in the proof solver (including x=0 from history).
    Observer parity((x>=0&&x<=10&&y==x)&&(x+y>=0));ImpossibleBits solver_filter(parity,dir,1.0);
    unsigned sum_id=0,xid=0;for(unsigned id=0;id<parity.nodes.size();++id){if(parity.nodes[id].expr.to_string()==(x+y).to_string())sum_id=id;if(parity.nodes[id].symbol&&parity.nodes[id].name=="x")xid=id;}
    auto yes=parity.context.bool_val(true);
    require(solver_filter.probe(sum_id,1,1,yes,1,1.0)==0,"F-only parity impossibility not proven");
    require(solver_filter.eligible(sum_id,1,1,2)==0,"UNSAT result not cached");
    require(solver_filter.probe(xid,1,1,yes,2,1.0)==1,"historically zero x incorrectly considered unflippable");
    require(solver_filter.eligible(xid,1,1,3)==1,"SAT target incorrectly filtered");
    ImpossibleBits exhausted(parity,dir,0.0);require(exhausted.probe(sum_id,1,1,yes,1,1.0)==1,"unproved budget-exhausted target filtered");
    std::cout<<Json({{"passed",true},{"exhaustive_fact_checks",checks},{"F_only_unsat_cached",true},{"historical_assignment_not_used",true},{"budget_exhaustion_not_impossibility",true}}).dump(2)<<"\n";
}
