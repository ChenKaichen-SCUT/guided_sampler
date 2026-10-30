#define main kernel_test_main
#include "kernel.cpp"
#undef main
int main(){try{z3::context c;z3::solver s(c);s.set("timeout",2000u);s.set("phase_selection",0u);s.push();unsigned n=12,m=11;std::vector<std::vector<z3::expr>> p;std::vector<std::pair<z3::expr,bool>> atoms;
for(unsigned i=0;i<n;++i){p.emplace_back();z3::expr_vector row(c);for(unsigned j=0;j<m;++j){auto v=c.bool_const(("p_"+std::to_string(i)+"_"+std::to_string(j)).c_str());p.back().push_back(v);row.push_back(v);atoms.emplace_back(v,true);}s.add(z3::mk_or(row));}
for(unsigned j=0;j<m;++j)for(unsigned i=0;i<n;++i)for(unsigned k=i+1;k<n;++k)s.add(!p[i][j]||!p[k][j]);
auto idx=index_of(atoms);install(s,idx,2,0.2);auto result=s.check();auto st=stats(s);std::cout<<J({{"result",result==z3::unknown?"unknown":result==z3::sat?"sat":"unsat"},{"reason",s.reason_unknown()},{"stats",st}}).dump(2)<<'\n';
check(st["phase_overrides"].get<unsigned>()>0,"exposure test had no actual override");check(result==z3::unknown&&st["exposure_limit"].get<bool>(),"exposure did not cancel");check(s.reason_unknown()=="guidance_exposure_limit","exposure reason missing");clear(s);s.pop();auto x=c.int_const("x");s.add(x==3);check(s.check()==z3::sat,"exposure poisoned next check");
z3::params cfg(c);cfg.set("ls_sampling",true);cfg.set("auto_config",false);cfg.set("logic","QF_LIA");auto ls=z3::with(z3::tactic(c,"smt"),cfg).mk_solver();ls.add(x==3);check(ls.check()==z3::sat,"exposure poisoned CCSS");check(stats(ls).empty(),"A request leaked into CCSS");std::cerr<<"exposure cancellation, sticky fallback guard, reuse and CCSS passed\n";
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
