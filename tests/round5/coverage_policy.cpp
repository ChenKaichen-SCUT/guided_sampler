#define main prior_kernel_main
#include "../round2/kernel.cpp"
#undef main
#include <fstream>
using CP=a2::r5::CoveragePolicy;
using P=a2::r4::Policy;
int main(int argc,char** argv){try{
 unsigned cases=0;
 for(bool complete:{false,true})for(unsigned s0=0;s0<4;++s0)for(unsigned s1=0;s1<4;++s1)for(unsigned b0=0;b0<4;++b0)for(unsigned b1=0;b1<4;++b1){
  a2::r4::PhaseEvidence e;e.complete=complete;e.support[0]=s0;e.support[1]=s1;e.block[0]=b0;e.block[1]=b1;
  auto full=a2::r5::choose_coverage(e,CP::Full),support=a2::r5::choose_coverage(e,CP::SupportOnly),ref=a2::r5::choose_coverage(e,CP::ReferenceOnly);
  check(!ref,"reference emitted coverage");check(bool(full)==bool(e.best()),"Full eligibility differs from R4");if(full)check(full->phase==*e.best(),"Full phase differs from R4");
  check(bool(support)==(complete&&s0!=s1),"support-only used block tie-break");if(support)check(support->phase==(s1>s0)&&!support->avoid,"support-only direction");++cases;
 }
 J executions=J::array();
 for(bool positive:{false,true})for(auto policy:{P::Reference,P::Coverage,P::SupportOnly}){
  z3::context c;auto solver=z3::tactic(c,"smt").mk_solver();auto idx=std::make_shared<a2::Index>();auto pref=std::make_shared<a2::r4::QueryPreferences>();pref->policy=policy;
  for(unsigned i=0;i<90;++i){auto a=c.bool_const(("x"+std::to_string(i)).c_str()),b=c.bool_const(("y"+std::to_string(i)).c_str());solver.add(a||b);
   for(auto atom:{a,b}){a2::Work work;auto n=a2::canonical(a2::HostView{},atom,work);auto& entry=idx->entries[n.key];entry.original_exact=n.exact;unsigned node=2*i+unsigned(atom.id()==b.id());if(positive)entry.rules.push_back({node,!n.negated,1,0,1,0});else entry.rules.push_back({node,n.negated,0,1,1,0});pref->reference[a2::HostView{}.identity(atom)]=0;}
  }
  idx->version=1;idx->preferences=pref;install(solver,idx,2,45,1000+unsigned(policy)+positive*10);check(solver.check()==z3::sat,"controlled policy SAT");auto st=stats(solver);clear(solver);
  check(st["suggestions"]==((policy==P::Reference||(!positive&&policy==P::SupportOnly))?0:4),"quota incorrect");
  for(auto const& action:st["actions"]){check(action["decision_id"].get<unsigned>()<=64,"window");check(action["native_var"]==action["actual_var"],"native var changed");if(policy==P::SupportOnly)check(action["preference_source"]!="avoid_direct_blocker","avoid leaked");}
  executions.push_back({{"positive",positive},{"policy",unsigned(policy)},{"stats",st}});
 }
 std::cout<<J({{"passed",true},{"pure_cases",cases},{"executions",executions}}).dump()<<'\n';
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
