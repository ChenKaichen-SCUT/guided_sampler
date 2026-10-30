#include "a_guidance_bridge.hpp"
#include <filesystem>
#include <iostream>
#include <sstream>
using namespace guided;
Json load(char const* p){std::ifstream f(p);Json j;f>>j;return j;}
void save(std::string const& p,Json const& j){std::ofstream f(p);f<<j.dump(2)<<'\n';}
std::map<std::string,Big> parse_sample(std::string line){std::map<std::string,Big> a;line=line.substr(line.find(':')+2);std::stringstream s(line);std::string pair;while(std::getline(s,pair,';'))if(!pair.empty()){auto k=pair.rfind(':');a[pair.substr(0,k)]=Big(pair.substr(k+1));}return a;}
int main(int argc,char** argv){try{
 if(argc!=6)return 2;std::string command=argv[1],dir=argv[5];auto spec=load(argv[2]);z3::context c;auto forms=c.parse_file(argv[3]);auto f=z3::mk_and(forms);OriginalAst ast(f);
 if(command=="snapshot"){
  std::ifstream samples(argv[4]);std::string line;unsigned count=spec["history_models"];for(unsigned i=0;i<count;++i){if(!std::getline(samples,line))throw std::runtime_error("short history");auto ev=ast.evaluate(parse_sample(line));if(!ev.values[0]||*ev.values[0]!=1)throw std::runtime_error("illegal historical sample");ast.commit(ev);}
  Json nodes=Json::array();for(auto const& n:ast.nodes)nodes.push_back({std::to_string(n.seen0),std::to_string(n.seen1)});
  save(dir,{{"version",ast.version},{"covered",ast.covered},{"observed",ast.observed},{"nodes",nodes},{"solver_calls",0}});return 0;
 }
 auto snapshot=load(argv[4]);std::unique_ptr<AGuidanceBridge> bridge;unsigned mode=command=="a_off_test"?0:command=="a_observe_test"?1:2;
 auto start=Clock::now();if(mode){bridge=std::make_unique<AGuidanceBridge>(f,mode,900,dir);auto& a=bridge->ast;if(a.nodes.size()!=snapshot["nodes"].size())throw std::runtime_error("snapshot AST mismatch");
  for(unsigned i=0;i<a.nodes.size();++i){auto& n=a.nodes[i];n.seen0=std::stoull(snapshot["nodes"][i][0].get<std::string>());n.seen1=std::stoull(snapshot["nodes"][i][1].get<std::string>());bridge->index->single_sided+=std::popcount(n.seen0^n.seen1);bridge->index->mappable_targets+=std::popcount((n.seen0&~n.seen1)&bridge->known[i].first)+std::popcount((n.seen1&~n.seen0)&bridge->known[i].second);for(auto [entry,k]:bridge->reverse[i]){entry->rules[k].want_one=n.seen0&~n.seen1&n.mask();entry->rules[k].want_zero=n.seen1&~n.seen0&n.mask();}}
  a.version=snapshot["version"];a.covered=snapshot["covered"];a.observed=snapshot["observed"];bridge->index->version=a.version;
 }
 double initialization=AGuidanceBridge::seconds(start);
 // Reuse the original declarations while parsing historical assumptions; they
 // remain assumptions, never additional assertions or newly invented targets.
 std::vector<Z3_symbol> names;std::vector<Z3_func_decl> decls;for(auto const& v:ast.vars){names.push_back(v.decl().name());decls.push_back(v.decl());}
 std::string text;for(auto const& a:spec["query"]["assumptions"])text+="(assert "+a.get<std::string>()+")\n";
 Z3_ast_vector raw=Z3_parse_smtlib2_string(c,text.c_str(),0,nullptr,nullptr,names.size(),names.data(),decls.data());c.check_error();z3::expr_vector asms(c,raw);
 z3::solver s(c);s.add(f);s.set("timeout",2000u);if(bridge)bridge->prepare(s,spec["query"]["query"]);
 auto query_start=Clock::now();auto result=s.check(asms);double elapsed=AGuidanceBridge::seconds(query_start);auto st=bridge?bridge->end_check(s):Json::object();
 Json out={{"mode",command},{"case_id",spec["case_id"]},{"solver_calls",1},{"timeout_ms",2000},{"result",result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown"},{"reason_unknown",result==z3::unknown?s.reason_unknown():""},{"check_seconds",elapsed},{"initialization_seconds",initialization},{"stats",st},{"reconstructed_learned_state",false}};
 if(result==z3::sat){auto model=s.get_model();std::map<std::string,Big> values;Json projection=Json::object();for(auto const& v:ast.vars){auto value=model.eval(v,true);auto n=v.decl().name().str();values[n]=v.is_bool()?Big(value.is_true()):numeral(value);projection[n]=values[n].str();}auto ev=(bridge?bridge->ast:ast).evaluate(values);if(!ev.values[0]||*ev.values[0]!=1)throw std::runtime_error("illegal micro model");out["projection"]=projection;if(bridge){out["outcomes"]=bridge->outcomes(ev);out["new_covered"]=ev.covered;}}
 save(dir+"/result.json",out);std::cout<<out.dump()<<'\n';
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
