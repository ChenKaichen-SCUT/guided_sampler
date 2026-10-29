#include "observation.hpp"
#include <iostream>
#include <fstream>
int main(int argc,char**argv){try{
 if(argc<3)return 2;z3::context c;auto forms=c.parse_file(argv[1]);guided::OriginalAst ast(z3::mk_and(forms));guided::TargetEncoder encoder(ast);guided::AtomHintCatalog hints(ast);
 std::ifstream in(argv[2]);guided::Json rows;in>>rows;guided::Json out=guided::Json::array();
 for(auto const& row:rows){std::map<std::string,guided::Big> values;for(auto it=row.begin();it!=row.end();++it)values[it.key()]=guided::Big(it.value().get<std::string>());
 auto ev=ast.evaluate(values);ast.commit(ev);guided::Json nodes=guided::Json::array();
 for(unsigned i=0;i<ast.nodes.size();++i){auto const& n=ast.nodes[i];nodes.push_back({{"id",i},{"expr",n.e.to_string()},{"seen0",std::to_string(n.seen0)},{"seen1",std::to_string(n.seen1)},{"visited",ev.values[i].has_value()}});}
 out.push_back({{"covered",ast.covered},{"observed",ast.observed},{"new_covered",ev.covered},{"new_observed",ev.observed},{"total",ast.total},{"nodes",nodes}});
 }
 // Evaluate every exact target under complete synthetic assignments; model eval
 // needs no solver and verifies Reach as well as all integer bits.
 guided::Json target_results=guided::Json::array();
 for(auto const& row:rows){z3::model m(c);std::map<std::string,guided::Big> vals;
 for(auto v:ast.vars){auto name=v.decl().name().str();std::string value=row.at(name);auto e=v.is_int()?c.int_val(value.c_str()):c.bool_val(value!="0");auto d=v.decl();m.add_const_interp(d,e);vals[name]=guided::Big(value);}
 auto ev=ast.evaluate(vals);unsigned checked=0;
 for(unsigned i=0;i<ast.nodes.size();++i)for(unsigned j=0;j<(ast.nodes[i].boolean?1:64);++j)for(bool desired:{false,true}){
   bool want=ev.values[i]&&bool((guided::low64(*ev.values[i])>>j)&1)==desired;
   auto target=encoder.make({i,j,desired});bool actual=m.eval(target,true).is_true();
   if(actual!=want)throw std::runtime_error("Reach/bit mismatch");++checked;
 }
 target_results.push_back(checked);
 }
 // Catalog false equality cannot support opposite integer bits.
 unsigned matched=0;
 for(unsigned i=0;i<ast.nodes.size();++i)for(unsigned j=0;j<(ast.nodes[i].boolean?1:64);++j)for(bool desired:{false,true})for(auto const& h:hints.lookup({i,j,desired})){
 if(h.constant && (!h.phase || bool((*h.constant>>j)&1)!=desired))throw std::runtime_error("unsound equality hint");++matched;}
 std::cout<<guided::Json({{"prefixes",out},{"targets_checked",target_results},{"hints_checked",matched}}).dump()<<'\n';return 0;
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
