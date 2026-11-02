#include "sampler/sampler.h"
#include "util/memory_manager.h"
namespace sampler {__int128_t string_to_int128(std::string const&);std::string processNegNumber(std::string const&);__int128_t floor_div(__int128_t,__int128_t,bool);__int128_t ceil_div(__int128_t,__int128_t,bool);}
int main(int argc,char** argv){
 if(argc==2&&std::string(argv[1])=="--self-test"){
  try{
   for(auto raw:{"0","-17","(- 17)","170141183460469231731687303715884105727","-170141183460469231731687303715884105728"}){auto parsed=sampler::string_to_int128(sampler::processNegNumber(raw));if(sampler::string_to_int128(r5::decimal(parsed))!=parsed)throw std::runtime_error("128-bit roundtrip");}
   for(auto raw:{"","(-)","true","170141183460469231731687303715884105728","-170141183460469231731687303715884105729"}){bool rejected=false;try{sampler::string_to_int128(sampler::processNegNumber(raw));}catch(std::exception const&){rejected=true;}if(!rejected)throw std::runtime_error("invalid/overflow accepted");}
   for(int n=-7;n<=7;++n)for(int d=-3;d<=3;++d)if(d){auto f=sampler::floor_div(n,d,false),c=sampler::ceil_div(n,d,false);if(f!=(__int128_t)std::floor(double(n)/d)||c!=(__int128_t)std::ceil(double(n)/d))throw std::runtime_error("signed integer division");}
   std::mt19937 mt(0),before=mt;auto text=r5::rng(mt);std::mt19937 restored;std::istringstream(text)>>restored;if(mt!=before||mt!=restored)throw std::runtime_error("RNG serialization consumed/changed state");
   r5::Probe probe(0,1,mt);probe.active=true;for(unsigned i=0;i<8194;++i)probe.point({{"step",i}});if(probe.progress.size()!=8192||probe.rows_dropped!=2)throw std::runtime_error("bounded progress overflow");
   std::cout<<"{\"passed\":true,\"checks\":[\"exact128_roundtrip\",\"invalid_and_overflow\",\"negative_division\",\"RNG_no_consumption\",\"bounded_progress_overflow\"]}\n";return 0;
  }catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}
 }
 if(argc!=6){std::cerr<<"recipe map output id initialize_only\n";return 2;}
 setenv("GUIDED_R6_TRACE_DIR",argv[3],1);setenv("GUIDED_R5_EXCHANGE_DIR",argv[3],1);setenv("GUIDED_R5_ROLE","independent_replay",1);
 r5::J recipe,map;try{std::ifstream(argv[1])>>recipe;std::ifstream(argv[2])>>map;}catch(std::exception const& e){r5::file(std::string(argv[4])+"_input_failure.json",{{"status","malformed_or_truncated_input"},{"error",e.what()}});return 2;}
 setenv("GUIDED_R6_QUERY",std::to_string(recipe.value("query",0)).c_str(),1);
 auto started=r5::Clock::now();memory::initialize(0);int rc=0;
 try{
  sampler::ls_sampler native(recipe.at("seed"),recipe.at("cutoff_seconds"));
  native.r5_begin_replay(recipe,argv[4],std::string(argv[5])=="1");
  native.r6_begin(map.get<std::unordered_map<std::string,std::string>>());
  if(std::string(argv[5])=="off"){
   native.m_r5.reset();native.make_lits_space(recipe.at("make_lits_space"));
   for(auto const& l:recipe.at("build_lits")){std::string text=l;native.build_lits(text);}
   auto clauses=recipe.at("clause_vec").get<std::vector<std::vector<int>>>();
   native.build_instance(clauses,map.get<std::unordered_map<std::string,std::string>>());
   r5::file(std::string(argv[4])+"_R2.json",native.r5_state(false));native.initialize();r5::file(std::string(argv[4])+"_R3.json",native.r5_state(true));
   native.r6_finish("initialization_only_probe_off",false);return 0;
  }
  try{
   native.make_lits_space(recipe.at("make_lits_space"));
   for(auto const& l:recipe.at("build_lits")){std::string text=l;native.build_lits(text);}
   auto clauses=recipe.at("clause_vec").get<std::vector<std::vector<int>>>();
   auto values=map.get<std::unordered_map<std::string,std::string>>();
   native.m_r5->recipe=recipe;native.m_r5->recipe["exchange"]["map"]=map;
   native.build_instance(clauses,values);
   bool sat=native.ls_sampling();
   if(sat){auto solution=native.r5_solution();native.m_r5->save("solution",solution);if(!solution.at("native_check_solution").get<bool>()||solution.at("unsat_count")!=0||solution.at("overflow").get<bool>())throw std::runtime_error("illegal native solution");native.m_r5->exit="sat_ccss_solution_only";native.m_r6.reason="sat_ccss_solution_only";}
   else if(native.m_r5->exit=="not_finished")native.m_r5->exit="native_failure_unclassified";
  }catch(r5::InitializationOnly const&){native.m_r5->exit="initialization_only";native.m_r6.reason="initialization_only";}
  catch(std::exception const& e){native.m_r6.error=e.what();native.m_r6.reason=dynamic_cast<std::out_of_range const*>(&e)?"arith_unknown":"exception";native.m_r5->exit=std::string("exception:")+e.what();rc=1;}
  native.m_r5->flush();native.r6_finish(native.m_r6.reason,native.m_r6.reason=="sat_ccss_solution_only");
 }catch(std::exception const& e){r5::file(std::string(argv[4])+"_outer_failure.json",{{"error",e.what()}});rc=1;}
 r5::file(std::string(argv[4])+"_process.json",{{"exit_code",rc},{"wall_seconds",r5::seconds(started)},{"fresh_object",true},{"SMT_calls",0}});return rc;
}
