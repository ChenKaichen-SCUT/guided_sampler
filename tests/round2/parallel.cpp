#define main kernel_test_main
#include "kernel.cpp"
#undef main
int main(){try{z3::context c;auto p=c.bool_const("p"),q=c.bool_const("q");auto f=p||q;z3::tactic ts[2]={z3::tactic(c,"smt"),z3::tactic(c,"smt")};auto s=z3::par_or(2,ts).mk_solver();s.add(f);auto idx=index_of({{p,true},{q,true}});install(s,idx);check(s.check()==z3::sat,"translated parallel goal SAT");auto st=stats(s);std::cout<<st.dump(2)<<'\n';check(st["suggestions"].get<unsigned>()<=4,"parallel quota multiplied");check(st["phase_overrides"].get<unsigned>()>0,"sidecar did not reach translated goal");check(!st["backend_calls"].empty(),"no translated backend");clear(s);check(idx->active==0,"parallel ownership leak");
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
