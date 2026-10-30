#include "observation.hpp"
#include <fstream>
#include <iostream>
int main(int argc,char** argv){try{
 if(argc!=3)return 2;z3::context c;auto forms=c.parse_file(argv[1]);guided::OriginalAst ast(z3::mk_and(forms));std::ifstream in(argv[2]);guided::Json rows;in>>rows;guided::Json out=guided::Json::array();
 for(auto const& row:rows){std::map<std::string,guided::Big> values;for(auto it=row.begin();it!=row.end();++it)values[it.key()]=guided::Big(it.value().get<std::string>());auto ev=ast.evaluate(values);ast.commit(ev);guided::Json nodes=guided::Json::array();for(unsigned i=0;i<ast.nodes.size();++i){auto const& n=ast.nodes[i];nodes.push_back({{"id",i},{"seen0",std::to_string(n.seen0)},{"seen1",std::to_string(n.seen1)},{"visited",ev.values[i].has_value()}});}out.push_back({{"covered",ast.covered},{"observed",ast.observed},{"new_covered",ev.covered},{"new_observed",ev.observed},{"total",ast.total},{"nodes",nodes}});}
 std::cout<<guided::Json({{"prefixes",out},{"targets_checked",guided::Json::array()},{"hints_checked",0},{"B_constructed",false}}).dump()<<'\n';
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
