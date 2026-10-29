#include <z3++.h>
#include "z3_guidance.h"
#include <nlohmann/json.hpp>
#include <iostream>
#include <vector>
#include <set>
#include <stdexcept>
using J=nlohmann::json;
void require(bool v,char const* msg){if(!v)throw std::runtime_error(msg);}
void install(z3::solver& s,unsigned mode,std::vector<z3::expr> const& goals,std::vector<z3::expr> const& atoms={},std::vector<unsigned> phase={},std::vector<unsigned> index={},unsigned epoch=1){
 std::vector<Z3_ast> p,a;std::vector<unsigned> ids;
 for(unsigned i=0;i<goals.size();++i){p.push_back(goals[i]);ids.push_back(100+i);}
 for(auto e:atoms)a.push_back(e);
 Z3_solver_set_coverage_guidance(s.ctx(),s,mode,epoch,1,p.size(),p.data(),ids.data(),a.size(),a.data(),phase.data(),index.data());s.ctx().check_error();
}
J stats(z3::solver& s){return J::parse(Z3_solver_get_coverage_guidance_stats(s.ctx(),s));}
z3::expr bit(z3::expr x,unsigned j,bool desired=true){
 // exact decimal power, including 2^64
 std::string p="1",h="1";auto twice=[](std::string v){int c=0;for(auto i=v.rbegin();i!=v.rend();++i){int d=(*i-'0')*2+c;*i='0'+d%10;c=d/10;}if(c)v.insert(v.begin(),'1');return v;};
 for(unsigned k=0;k<j;++k)h=twice(h);p=twice(h);auto rem=z3::mod(x,x.ctx().int_val(p.c_str()));auto half=x.ctx().int_val(h.c_str());return desired?rem>=half:rem<half;
}
int main(){try{
 z3::context c;auto x=c.int_const("x"),y=c.int_const("y");J evidence=J::array();
 {
  z3::solver s(c);s.add(x>=0&&x<=15);install(s,2,{bit(x,3)});auto n=s.assertions().size();require(s.check()==z3::sat,"route sat");auto st=stats(s);require(st["backend"]==1&&st["unsupported"]==1,"metadata must not switch tactic route");require(s.assertions().size()==n,"metadata changed assertions");evidence.push_back({{"test","metadata_route"},{"stats",st}});
  z3::expr_vector a(c);a.push_back(x>=0);install(s,2,{bit(x,3)}, {}, {}, {},2);require(s.check(a)==z3::sat,"guided bounded sat");st=stats(s);require(st["backend"]==2,"native assumption must use SMT");require(st["b_used"].get<unsigned>()>0,"B did not reach ordinary decision");require(s.get_model().eval(bit(x,3)).is_true(),"B bit goal missing");evidence.push_back({{"test","bounded_B"},{"stats",st}});
 }
 {
  z3::solver s(c);s.add(x==0);z3::expr_vector a(c);a.push_back(x>=0);install(s,2,{bit(x,0)});require(s.check(a)==z3::sat,"infeasible preference made F UNSAT");require(s.get_model().eval(x).get_numeral_int()==0,"wrong model");evidence.push_back({{"test","infeasible_B"},{"stats",stats(s)}});
 }
 {
  z3::solver s(c);s.add(x>=0&&x<=2);z3::expr_vector a(c);a.push_back(x>=0);install(s,2,{bit(x,0),bit(x,1)});require(s.check(a)==z3::sat,"incompatible soft goals lost solution");evidence.push_back({{"test","incompatible_targets"},{"stats",stats(s)}});
  for(unsigned i=0;i<2;++i){install(s,2,{bit(x,i)}, {}, {}, {},i+2);require(s.check(a)==z3::sat,"later target banned");require(s.get_model().eval(bit(x,i)).is_true(),"target not retryable across epoch");}
 }
 {
  z3::solver s(c);s.add(x==0||x==10);z3::expr_vector a(c);a.push_back(x==0);install(s,2,{bit(x,1)});require(s.check(a)==z3::sat,"fixed preference conflict broke SAT");require(s.get_model().eval(x).get_numeral_int()==0,"fixed x not obeyed");
  install(s,2,{bit(x,1)}, {}, {}, {},2);require(s.check()==z3::sat,"released assumption sat");require(s.get_model().eval(x).get_numeral_int()==10,"fixed-condition preference permanently lost");evidence.push_back({{"test","fixed_then_released"},{"stats",stats(s)}});
 }
 {
  z3::solver s(c);auto atom=x==10;s.add(x==0||atom);z3::expr_vector a(c);a.push_back(x>=0);install(s,1,{bit(x,1)},{atom},{1},{0});require(s.check(a)==z3::sat,"A sat");auto st=stats(s);require(st["a_used"].get<unsigned>()>0,"A no real ordinary decision");require(st["b_used"]==0,"A used B");evidence.push_back({{"test","A_phase"},{"stats",st}});
 }
 {
  for(unsigned mode=1;mode<=3;++mode)for(int value=0;value<4;++value){z3::solver s(c);s.add(x>=0&&x<4);z3::expr_vector a(c);a.push_back(x==value);install(s,mode,{bit(x,0),bit(x,1)},{x==0},{1},{0});require(s.check(a)==z3::sat,"projected legal solution lost");require(s.get_model().eval(x).get_numeral_int()==value,"projection wrong");}
  evidence.push_back({{"test","all_modes_projection"},{"assignments",12}});
 }
 {
  z3::solver one(c),two(c);one.add(x>=0&&x<=15);two.add(x==0);z3::expr_vector a(c);a.push_back(x>=0);install(one,2,{bit(x,3)});require(two.check()==z3::sat,"other solver affected");require(stats(two).empty(),"guidance leaked across same context");
  one.push();one.add(x==0);require(one.check(a)==z3::sat,"push SAT");one.pop();install(one,2,{bit(x,3)}, {}, {}, {},2);require(one.check(a)==z3::sat,"pop stale handle");one.reset();one.add(x==1);install(one,2,{bit(x,3)}, {}, {}, {},3);require(one.check(a)==z3::sat,"reset stale handle");Z3_solver_clear_coverage_guidance(c,one);require(stats(one).empty(),"clear failed");
  evidence.push_back({{"test","pop_reset_solver_isolation"},{"pass",true}});
 }
 {
  z3::solver s(c);s.add(x>=-20&&x<=20);z3::expr_vector a(c);a.push_back(x>=-20);install(s,2,{bit(x,63)});s.set("rlimit",1u);require(s.check(a)==z3::unknown,"expected canceled check");s.set("rlimit",0u);install(s,2,{bit(x,0)}, {}, {}, {},2);require(s.check(a)==z3::sat,"unknown then reuse");evidence.push_back({{"test","unknown_reuse"},{"stats",stats(s)}});
 }
 {
  z3::solver s(c);s.add(x>=0);std::vector<z3::expr> goals;
  for(unsigned i=0;i<90;++i){auto a=c.bool_const(("native_a_"+std::to_string(i)).c_str()),b=c.bool_const(("native_b_"+std::to_string(i)).c_str());s.add(a||b);}
  for(unsigned i=0;i<8;++i)goals.push_back(c.bool_const(("target_"+std::to_string(i)).c_str()));
  z3::expr_vector a(c);a.push_back(x>=0);
  for(unsigned epoch=1;epoch<=5;++epoch){install(s,2,goals,{}, {}, {},epoch);require(s.check(a)==z3::sat,"budget test SAT");auto st=stats(s);require(st["b_used"].get<unsigned>()<=4,"B quota replenished");std::set<unsigned> seen;
   for(auto const& event:st["events"]){require(event["ordinary"].get<unsigned>()<=64,"outside decision window");for(auto const& id:event["targets"])require(seen.insert(id.get<unsigned>()).second,"target attempted twice");}
   require(st["ordinary"].get<unsigned>()>64,"did not exercise decision window exhaustion");
   if(epoch==5)evidence.push_back({{"test","quota_and_window_exhaustion"},{"stats",st}});
  }
  Z3_solver_set_coverage_guidance(c,s,0,6,1,0,nullptr,nullptr,0,nullptr,nullptr,nullptr);
  require(s.check(a)==z3::sat,"passive monitor SAT");auto st=stats(s);require(st["a_used"]==0&&st["b_used"]==0,"passive monitor intervened");evidence.push_back({{"test","passive_history_monitor"},{"stats",st}});
 }
 std::cout<<J({{"passed",true},{"tests",evidence}}).dump(2)<<'\n';return 0;
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
