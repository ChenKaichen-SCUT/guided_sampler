#include "a_guidance_bridge.hpp"
#include <filesystem>
#include <iostream>
void check(bool x,char const* msg){if(!x)throw std::runtime_error(msg);}
int main(int argc,char** argv){try{if(argc!=2)return 2;std::filesystem::create_directories(argv[1]);z3::context c;auto p=c.bool_const("p"),q=c.bool_const("q"),x=c.int_const("x");auto f=(p||q)&&(q||!q)&&(x>=0)&&(x<=10);guided::AGuidanceBridge a(f,2,900,argv[1]);
 auto history=a.ast.evaluate({{"p",1},{"q",0},{"x",0}});check(*history.values[0]==1,"invalid test history");a.commit(history);
 z3::solver s(c);s.push();s.add(f);a.prepare(s,1);auto result=s.check();check(result==z3::sat,"outcome SAT");auto st=a.end_check(s);a.query_finished("CDCL",1,st.value("actual_end",0.0),"sat",st);auto m=s.get_model();std::map<std::string,guided::Big> values;for(auto const& v:a.ast.vars){auto value=m.eval(v,true);values[v.decl().name().str()]=v.is_bool()?guided::Big(value.is_true()):guided::numeral(value);}auto ev=a.ast.evaluate(values);auto outcomes=a.outcomes(ev);unsigned hits=0;for(auto const& event:outcomes)for(auto const& t:event["targets"])hits+=t["new_covered_for_targets"].get<unsigned>();check(st["phase_overrides"].get<unsigned>()>0,"outcome lacked override");check(hits>0,"no true original-node new coverage witness");
 a.commit(ev);unsigned pn=a.ast.ids.at(q.id());for(auto [entry,k]:a.reverse[pn])check((entry->rules[k].want_one|entry->rules[k].want_zero)==0,"covered target was not removed");
 a.disable("test_explicit_disable");a.prepare(s,2);check(s.check()==z3::sat,"post-disable check");check(guided::Json::parse(Z3_solver_get_A_guidance_stats(c,s)).empty(),"disabled still registered");
 std::cout<<guided::Json({{"passed",true},{"stats",st},{"outcomes",outcomes},{"whole_model_new_covered",ev.covered},{"target_new_covered",hits}}).dump(2)<<'\n';
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
