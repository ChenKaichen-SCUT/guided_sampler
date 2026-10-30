#include "a_guidance_bridge.hpp"
#define main kernel_test_main
#include "kernel.cpp"
#undef main
#include <filesystem>
int main(int argc,char** argv){try{if(argc!=2)return 2;std::filesystem::create_directories(argv[1]);z3::context c;auto x=c.int_const("x");auto f=(x==0||x==10)&&(10==x||x==0);guided::AGuidanceBridge a(f,2,900,argv[1]);
 for(auto const& kv:a.index->entries)for(auto const& r:kv.second.rules)check(!(r.want_one|r.want_zero),"unobserved bit scored");
 auto first=a.ast.evaluate({{"x",0}});check(first.covered==0,"first observation counted as covered");a.commit(first);unsigned xn=a.ast.ids.at(x.id());unsigned integer_rules=0;
 for(auto const& kv:a.index->entries)for(auto const& r:kv.second.rules)if(r.node==xn){++integer_rules;check(r.phase,"false integer equality incorrectly supports a bit");}
 check(integer_rules==2,"alias integer targets were duplicated");auto second=a.ast.evaluate({{"x",10}});a.commit(second);
 for(auto [entry,k]:a.reverse[xn]){auto const& r=entry->rules[k];check(!(r.one&r.want_one&10)&&!(r.zero&r.want_zero&10),"covered bits still scored");}
 auto p=c.bool_const("p"),q=c.bool_const("q");z3::solver s(c);s.push();s.set("phase_selection",0u);s.add(p||q);auto idx=index_of({{p,true},{q,true}});for(auto& kv:idx->entries){auto r=kv.second.rules.front();kv.second.rules.push_back(r);kv.second.rules.push_back(r);}install(s,idx);check(s.check()==z3::sat,"duplicate rule solve");auto st=stats(s);for(auto const& action:st["actions"])check(action["support"].size()==1,"duplicate support was not merged");clear(s);
 a.disable("finite_tail_test");a.prepare(s,4);check(s.check()==z3::sat,"disabled SAT");check(stats(s).empty(),"disabled registration");s.push();s.add(!p&&!q);check(s.check()==z3::unsat,"disabled UNSAT");s.pop();check(s.check()==z3::sat,"disabled pop SAT");check(stats(s).empty(),"disabled path revived");
 std::cout<<J({{"passed",true},{"integer_rules",integer_rules},{"duplicate_rule_stats",st},{"disabled_tail_checks",3}}).dump(2)<<'\n';
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
