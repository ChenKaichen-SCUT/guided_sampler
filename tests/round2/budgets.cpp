#define main kernel_test_main
#include "kernel.cpp"
#undef main
int main(){try{J rows=J::array();for(unsigned mode:{1u,2u})for(bool same:{false,true}){z3::context c;z3::solver s(c);s.push();s.set("phase_selection",0u);auto p=c.bool_const("p"),q=c.bool_const("q");s.add(p||q);auto idx=index_of({{p,!same},{q,!same}});install(s,idx,mode,0.0);check(s.check()==z3::sat,"zero exposure must retain native SAT");auto st=stats(s);check(st["phase_overrides"]==0,"zero exposure override");check(!st["exposure_limit"].get<bool>(),"unchanged query charged exposure");if(mode==1||same)check(st["suggestions"].get<unsigned>()>0,"same/observe suggestion missing");rows.push_back(st);clear(s);}
 {z3::context c;z3::solver s(c);s.push();auto p=c.bool_const("p"),q=c.bool_const("q");s.add(p||q);auto idx=index_of({{p,true},{q,true}});Z3_solver_set_A_guidance(c,s,&idx,1,1,2,45,0,1);check(s.check()==z3::sat,"zero explicit budget SAT");auto st=stats(s);check(st["phase_overrides"]==0,"zero explicit budget override");rows.push_back(st);clear(s);}
 std::cout<<J({{"passed",true},{"tests",rows}}).dump(2)<<'\n';
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
