#define main kernel_test_main
#include "kernel.cpp"
#undef main
int main(){try{z3::context c;auto a=c.bool_const("a"),b=c.bool_const("b");auto f=(a||b)&&(a||!b)&&(!a||b);z3::solver s(c);s.set("phase_selection",1u);s.push();s.add(f);auto idx=index_of({{a,false},{b,false}});install(s,idx);check(s.check()==z3::sat,"incompatible preference lost SAT");auto st=stats(s);std::cout<<st.dump(2)<<'\n';auto m=s.get_model();check(m.eval(f,true).is_true(),"abandon illegal model");bool abandoned=false;for(auto const& action:st["actions"])abandoned|=action["phase_changed"].get<bool>()&&action["trailed_assignment_popped"].get<bool>();check(abandoned,"no popped override witness");clear(s);check(s.check()==z3::sat,"disabled history reuse");check(stats(s).empty(),"registration survived disable");std::cerr<<"incompatible preference backtracked; native history retained and reuse passed\n";
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
