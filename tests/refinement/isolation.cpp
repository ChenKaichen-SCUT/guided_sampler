#include "session.hpp"
#include <filesystem>
#include <iostream>
#define REQUIRE(x) do {if(!(x))throw std::runtime_error(#x);}while(false)
int main(int argc,char** argv){
    REQUIRE(argc==3);std::string dir=argv[1],mode=argv[2];std::filesystem::create_directories(dir);
    setenv("REFINEMENT_MODE",mode.c_str(),1);setenv("REFINEMENT_STATE_TRACE","1",1);setenv("GUIDED_CCSS_STAGNATION_GUARD","1",1);
    setenv("GUIDED_R5_EXCHANGE_DIR",dir.c_str(),1);setenv("GUIDED_R5_DECISION_AUDIT","1",1);setenv("GUIDED_SEMANTIC_TRACE_DIR",dir.c_str(),1);setenv("GUIDED_R6_TRACE_DIR",dir.c_str(),1);
    z3::context c;auto x=c.int_const("x"),y=c.int_const("y");auto f=x>=0&&x<=31&&y>=0&&y<=31;
    guided::Session session(c,120,std::nullopt,dir);session.load(f,3);std::ofstream raw(dir+"/samples.raw");
    std::mt19937 mt(0);std::uniform_real_distribution<double> dist(0,1);z3::solver cdcl(c);cdcl.add(f);z3::model m_ls(c);
    // Fixed synthetic native checks earn real CPU credit; these calls exist only
    // in this correctness fixture and are identical across all three modes.
    session.native_begin();for(unsigned i=0;i<2000;++i)REQUIRE(cdcl.check()==z3::sat);session.native_end();
    z3::goal g(c);g.add(f);auto ar=z3::tactic(c,"simplify")(g);auto subgoal=ar[0];z3::params lp(c);lp.set("ls_sampling",true);lp.set("auto_config",false);lp.set("logic","QF_LIA");auto ls=z3::with(z3::tactic(c,"smt"),lp).mk_solver();for(unsigned k=0;k<subgoal.size();++k)ls.add(subgoal[k]);ls.set("ls_timeout",1u);ls.set("random_seed",0u);
    for(unsigned i=0;i<4;++i){
        session.state_trace(mt,m_ls,"query_input_before");guided::QueryInputs inputs(c);inputs.user_hard.push_back(x==c.int_val(i));inputs.reference=guided::collect_inherited_reference(m_ls,session.original_expressions,mt,0.5,dist,session.split->native.accepted_count!=0);session.register_inputs(inputs);session.state_trace(mt,m_ls,"query_input_after");
        session.guidance->prepare(cdcl,session.query+1);session.begin_query("CDCL",inputs.user_hard,50000,50000);session.native_begin();auto cr=cdcl.check(inputs.user_hard);session.native_end();auto stats=session.guidance->end_check(cdcl);session.end_query(cdcl,cr,stats);REQUIRE(cr==z3::sat);
        session.native_begin();auto m=cdcl.get_model();session.native_end();session.state_trace(mt,m_ls,"delivery_before");session.commit(m,f,raw);session.state_trace(mt,m_ls,"delivery_after");
        z3::expr_vector empty(c);session.begin_query("CCSS",empty,1,1);session.native_begin();auto lr=ls.check();session.native_end();session.end_query(ls,lr);REQUIRE(lr==z3::sat);session.native_begin();m_ls=subgoal.convert_model(ls.get_model());session.native_end();session.ls_reference_source(m_ls);session.state_trace(mt,m_ls,"delivery_before");session.commit(m_ls,f,raw);session.state_trace(mt,m_ls,"delivery_after");
    }
    session.finish();if(mode=="improve")REQUIRE(session.split->replacements>0);std::cout<<"PASS "<<mode<<" replacements "<<session.split->replacements<<"\n";
}
