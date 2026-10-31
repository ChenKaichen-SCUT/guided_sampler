// Independent replay of the frozen HighDiv host RNG; no solver or online code.
#include <nlohmann/json.hpp>
#include <random>
#include <fstream>
#include <sstream>
#include <iostream>
#include <stdexcept>
using J=nlohmann::json;
void require(bool v){if(!v)throw std::runtime_error("host RNG replay mismatch");}
std::string hash(std::mt19937 const& mt){std::ostringstream s;s<<mt;uint64_t h=14695981039346656037ULL;for(unsigned char c:s.str()){h^=c;h*=1099511628211ULL;}std::ostringstream o;o<<std::hex<<h;return o.str();}
int main(int argc,char** argv){try{require(argc==2);std::string d=argv[1];std::ifstream input(d+"/query_inputs.jsonl"),queries(d+"/queries.jsonl");J r,q;std::string line;std::map<unsigned,J> refs;while(std::getline(input,line)){r=J::parse(line);refs[r["query_id"].get<unsigned>()]=r;}std::mt19937 mt(0);std::uniform_real_distribution<double> select(0,1);std::uniform_int_distribution<uint64_t> seed(0,UINT64_MAX);unsigned draws=0,seeds=0;
 while(std::getline(queries,line)){q=J::parse(line);if(q["source"]=="CCSS"){unsigned value=seed(mt);require(value==q["highdiv_ls_seed"].get<unsigned>());++seeds;}else{auto const& ref=refs.at(q["query"].get<unsigned>());require(hash(mt)==ref["rng_before"]);for(auto const& row:ref["selection_draws"]){double value=select(mt);require(value==row["draw"].get<double>());require((value<0.5)==row["selected"].get<bool>());++draws;}require(hash(mt)==ref["rng_after"]);}}
 std::cout<<J({{"passed",true},{"selection_draws",draws},{"CCSS_seed_draws",seeds},{"solver_calls",0}}).dump()<<'\n';
 }catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
