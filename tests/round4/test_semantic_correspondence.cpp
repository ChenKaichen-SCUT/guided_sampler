#include "a_guidance_bridge.hpp"
#include <cassert>
#include <iostream>
a2::Norm norm(z3::expr const& e,bool enabled=true){a2::Work w;w.deadline=a2::Clock::now()+std::chrono::seconds(5);auto n=a2::canonical(a2::HostView{},e,w,enabled);assert(n.complete);return n;}
int main(int argc,char** argv){try{z3::context c;auto x=c.int_const("r4_x"),y=c.int_const("r4_y");unsigned calls=0,checks=0;
 for(int k:{-17,-1,0,10})for(unsigned compound=0;compound<2;++compound)for(unsigned gate=0;gate<2;++gate)for(unsigned swap=0;swap<2;++swap){
  auto t=compound?x+2*y:x;auto a=swap?(c.int_val(k)>=t):(t<=k),b=swap?(c.int_val(k)<=t):(t>=k);auto e=gate?(!a||!b):(a&&b),target=gate?!(t==k):(t==k);
  auto n=norm(e),expected=norm(target);assert(n.key==expected.key&&n.negated==expected.negated&&!n.mapping_rule.empty());auto neg=norm(!e),double_neg=norm(!(!e));assert(neg.key==n.key&&neg.negated!=n.negated);assert(double_neg.key==n.key&&double_neg.negated==n.negated);auto flipped=gate?(!b||!a):(b&&a);assert(norm(flipped).key==n.key&&norm(flipped).negated==n.negated);assert(norm(e,false).mapping_rule.empty());checks+=5;
  z3::solver solver(c);solver.set("timeout",2000u);solver.add(e!=target);assert(solver.check()==z3::unsat);++calls;
 }
 for(auto e:{(x<=0)&&(x>=1),(!(x<=0))||(!(x>=1)),(x<0)&&(x>=0),(x<=0)&&(y>=0),(x<=0)&&(x<=0),c.bool_const("r4_x")||!c.bool_const("r4_x")}){assert(norm(e).mapping_rule.empty());++checks;}
 auto original=a2::r4::declaration_identity('I',false,"same",false),helper=a2::r4::declaration_identity('I',false,"same",true);assert(original!=helper);assert(original!=a2::r4::declaration_identity('B',false,"same",false));assert(original!=a2::r4::declaration_identity('I',true,"same",false));checks+=3;
 assert(norm(c.bool_const("same")).key!=norm(c.int_const("same")==0).key);++checks;
 // Disabling the mapping preserves old canonical behavior; no source model is injected online.
 auto f=(x==0)||(x==10);guided::AGuidanceBridge bridge(f,2,60,argv[1]);assert(bridge.ast.version==0);for(auto const& kv:bridge.index->entries)for(auto const& r:kv.second.rules)assert(!r.want_one&&!r.want_zero);
 bridge.commit(bridge.ast.evaluate({{"r4_x",0}}));assert(bridge.ast.version==1);auto key=norm((x<=0)&&(x>=0)).key;assert(bridge.index->entries.count(key));bool missing=false;for(auto const& r:bridge.index->entries.at(key).rules)missing|=(r.want_one|r.want_zero)!=0;assert(missing);
 bridge.commit(bridge.ast.evaluate({{"r4_x",10}}));unsigned xid=bridge.ast.ids.at(x.id());for(auto const& kv:bridge.index->entries)for(auto const& r:kv.second.rules)if(r.node==xid)assert(!(r.want_one&2)&&!(r.want_zero&2));
 std::cout<<guided::Json({{"passed",true},{"pure_checks",checks},{"independent_XOR_checks",calls},{"seed",0},{"unrestricted_formula_space",true},{"version_zero_no_demand",true},{"both_seen_bit_no_reward",true}}).dump()<<'\n';
 }catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
