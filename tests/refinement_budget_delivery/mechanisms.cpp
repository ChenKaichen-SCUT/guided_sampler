#include "refinement/budgeted_delivery.hpp"
#include "refinement/line_blocking.hpp"
#include <fstream>
#include <iostream>
using namespace refinement;
#define REQUIRE(x) do{if(!(x))throw std::runtime_error(std::string("require: ")+#x+":"+std::to_string(__LINE__));}while(false)
static Json canonical(Json j){if(j.is_object()){for(auto i=j.begin();i!=j.end();){auto key=i.key();if(key=="wall"||key=="cpu"||key.ends_with("_wall")||key.ends_with("_cpu")||key=="work_counters_at_cancel")i=j.erase(i);else{i.value()=canonical(i.value());++i;}}}else if(j.is_array())for(auto& v:j)v=canonical(v);return j;}
static Node node(Op op,bool boolean,std::vector<unsigned> children={},int var=-1,Big value=0){Node n;n.op=op;n.boolean=boolean;n.children=children;n.variable=var;n.constant=value;return n;}
static Ast finish(std::vector<Node> ns,unsigned vars){Ast a;a.input_sha="synthetic";a.nodes=std::move(ns);for(unsigned v=0;v<vars;++v)a.variables.push_back({"v"+std::to_string(v),false});WorkBudget b;a.finalize(b);return a;}
int main(int argc,char** argv){try{REQUIRE(argc==3);Json all_fixtures;{std::ifstream f(argv[1]);f>>all_fixtures;}Json fixtures=all_fixtures.at("search");Json evidence=Json::array();uint64_t checks=0;
for(auto const& f:fixtures){WorkBudget b;auto ast=ast_from_json(f.at("ast"),b);std::vector<std::unique_ptr<Refiner>> rs;for(auto mode:{RepairMode::Legacy,RepairMode::ValueCache,RepairMode::Shared})rs.push_back(std::make_unique<Refiner>(ast,b,mode));REQUIRE(rs[0]->metadata()==rs[1]->metadata());REQUIRE(rs[0]->metadata()==rs[2]->metadata());
    // Exact syntactic closure for every support subset, including duplicate
    // occurrences and algebraically canceled variables.
    for(unsigned mask=0;mask<(1u<<ast.variables.size());++mask){IntegerVector d;for(unsigned v=0;v<ast.variables.size();++v)if(mask>>v&1)d[v]=1;ScratchMarks scratch(ast.nodes.size());auto ns=collect_affected(rs[2]->ir.reverse,d,scratch,b);for(unsigned n=0;n<ast.nodes.size();++n){REQUIRE(depends_on(rs[0]->ir.dependencies[n],d)==depends_on_direction(n,ns));++checks;}}
    OutputLedger history(ast.nodes.size());uint64_t event=0;
    for(auto const& mj:f.at("models")){auto m=assignment_from(mj);auto native=observe_official(ast,m,b);REQUIRE(native.legal);++event;
        Json expected;for(unsigned mode=0;mode<3;++mode){auto out=canonical(refinement_json(rs[mode]->try_refine(m,native,history,event,b)));if(mode==0)expected=out;else REQUIRE(out==expected);++checks;}
        evidence.push_back({{"fixture",f.at("name")},{"event",event},{"ast",ast_json(ast)},{"history_assignments",Json::array()},{"native",mj},{"result",expected}});
        for(auto const& prior:f.at("models")){if(evidence.back()["history_assignments"].size()+1>=event)break;evidence.back()["history_assignments"].push_back(prior);}
        // Completed domain + LineTerm requests compare both order-independent
        // values and exact intervals on every pool direction.
        AnchorValues cache(rs[1]->ir,m,event,b),shared(rs[2]->ir,m,event,b);
        for(auto const& d:rs[0]->pool.directions){LineDomain old(rs[0]->ir,m,d.values,b),value(rs[1]->ir,m,d.values,b,&cache,&d.affected),both(rs[2]->ir,m,d.values,b,&shared,&d.affected);try{auto u=old.formula();REQUIRE(domain_json(u)==domain_json(value.formula()));REQUIRE(domain_json(u)==domain_json(both.formula()));for(unsigned n=0;n<ast.nodes.size();++n)if(!ast.nodes[n].boolean&&rs[0]->ir.terms[n].supported){auto o=old.line_term(n),v=value.line_term(n),s=both.line_term(n);REQUIRE(o.constant==v.constant&&o.slope==v.slope&&o.constant==s.constant&&o.slope==s.slope);++checks;}}catch(Unsupported const&){bool v=false,s=false;try{value.formula();}catch(Unsupported const&){v=true;}try{both.formula();}catch(Unsupported const&){s=true;}REQUIRE(v&&s);}}
        history.commit(m,native);
    }
}

Json four_evidence=Json::array(),blocking_evidence=Json::array();uint64_t first_covered_checks=0;
for(auto const& f:fixtures){WorkBudget b;auto ast=ast_from_json(f.at("ast"),b);std::vector<std::unique_ptr<Refiner>> refs;std::vector<ScoreState> score_states(4);
 for(unsigned k=0;k<4;++k){refs.push_back(std::make_unique<Refiner>(ast,b,delivery_strategies("V"+std::to_string(k))));REQUIRE(refs[0]->metadata()==refs[k]->metadata());if(refs[k]->score_index)score_states[k]=initial_score_state(refs[k]->ir.ast,*refs[k]->score_index,b);}
 OutputLedger history(ast.nodes.size());uint64_t event=0;
 for(auto const& mj:f.at("models")){auto anchor=assignment_from(mj);auto base=observe_official(ast,anchor,b);++event;Json expected,first_expected;
  for(unsigned k=0;k<4;++k){auto& r=*refs[k];auto all=r.try_refine(anchor,base,history,event,b,false,{},StopPolicy::AuditAll,&score_states[k],"synthetic_L1");auto packed=canonical(refinement_json(all));if(k==0)expected=packed;else REQUIRE(expected==packed);
   auto early=r.try_refine(anchor,base,history,event,b,false,{},StopPolicy::FirstCovered,&score_states[k],"synthetic_L1");auto ep=canonical(refinement_json(early));if(k==0)first_expected=ep;else REQUIRE(ep==first_expected);
   std::optional<Json> first;for(auto const& c:all.candidates)if(c.value("kind","")=="candidate"&&c.value("reason","")=="eligible_strict_improvement"&&c.at("gain_covered").get<uint64_t>()>all.base_gain.covered){first=c;break;}
   if(first){REQUIRE(early.chosen);REQUIRE(assignment_json(early.chosen->assignment)==first->at("assignment"));REQUIRE(early.cancellation=="first_covered");++first_covered_checks;}
   else REQUIRE(early.cancellation!="first_covered");
   // The same real hard condition has its own AST node space and original variable map.
   Ast hard=finish({node(Op::Eq,true,{1,2}),node(Op::Variable,false,{},0),node(Op::Constant,false,{},-1,anchor[0])},ast.variables.size());hard.variables=ast.variables;auto hir=compile_affine_ir(hard,b,r.ir.strategies);
   auto constrained=r.try_refine(anchor,base,history,event,b,false,{hir},StopPolicy::AuditAll,&score_states[k],"synthetic_L1");
   for(auto const& c:constrained.candidates)if(c.value("kind","")=="candidate"&&c.contains("gain_covered"))REQUIRE(c.at("assignment")[0]==anchor[0].str());
  }
  four_evidence.push_back({{"fixture",f.at("name")},{"ast",ast_json(ast)},{"event",event},{"native",mj},{"result",expected},{"first_covered",first_expected},{"metadata",refs[0]->metadata()},{"history_assignments",Json::array()}});
  for(auto const& prior:f.at("models")){if(four_evidence.back()["history_assignments"].size()+1>=event)break;four_evidence.back()["history_assignments"].push_back(prior);}
  history.commit(anchor,base);
 }
}
REQUIRE(first_covered_checks>0);
// Sparse rows: empty rows, independent components, damage, cancellation and epoch wrap.
{WorkBudget b;EqualitySystem eq;Affine a;a.supported=true;a.coefficients={{0,1},{1,-1}};eq.rows={a,Affine{true,0,{}},Affine{true,0,{{2,3},{3,-3}}}};EqualityIncidence uses(4);for(unsigned r=0;r<eq.rows.size();++r)for(auto const& [v,c]:eq.rows[r].coefficients)uses[v].push_back({r,c});validate_incidence(eq,uses,b);SparseRowAccumulator acc(3,b);
 for(auto d:{IntegerVector{{0,1},{1,1}},IntegerVector{{2,1},{3,1}},IntegerVector{}}){acc.verify(d,uses,b);full_equality_dots(eq,d,b);}
 // Interrupt epoch clearing itself: the next call must retry the full clear before publishing epoch 1.
 acc.epoch=UINT32_MAX;unsigned wrap_calls=0;b.cancelled=[&](){return ++wrap_calls==2;};bool wrap_cancel=false;try{acc.verify({{0,1},{1,1}},uses,b);}catch(Exhausted const&){wrap_cancel=true;}REQUIRE(wrap_cancel&&acc.epoch==UINT32_MAX);b.cancelled={};acc.verify({{0,1},{1,1}},uses,b);
 acc.epoch=UINT32_MAX;acc.verify({{0,1},{1,1}},uses,b);bool failed=false;try{acc.verify({{0,1}},uses,b);}catch(std::runtime_error const&){failed=true;}REQUIRE(failed);
 auto damaged=uses;damaged[0].push_back(damaged[0][0]);failed=false;try{validate_incidence(eq,damaged,b);}catch(std::runtime_error const&){failed=true;}REQUIRE(failed);damaged=uses;damaged[1].clear();failed=false;try{validate_incidence(eq,damaged,b);}catch(std::runtime_error const&){failed=true;}REQUIRE(failed);
 for(unsigned cancel_at:{1,3,6}){unsigned c=0;b.cancelled=[&](){return ++c==cancel_at;};try{acc.verify({{0,1},{1,1}},uses,b);}catch(Exhausted const&){}b.cancelled={};acc.verify({{0,2},{1,2}},uses,b);}
}
// All support sets, separate occurrences, x-x and both branches; deep DAG and empty pool.
{auto ast=finish({node(Op::Ite,false,{1,2,3}),node(Op::Ge,true,{4,5}),node(Op::Sub,false,{4,6}),node(Op::Add,false,{7,8}),node(Op::Variable,false,{},0),node(Op::Constant,false),node(Op::Variable,false,{},0),node(Op::Variable,false,{},1),node(Op::Variable,false,{},2)},3);WorkBudget b;auto old=compile_affine_ir(ast,b);std::vector<IntegerDirection> ds;
 for(unsigned mask=0;mask<8;++mask){IntegerDirection d;d.id=ds.size();for(unsigned v=0;v<3;++v)if(mask>>v&1)d.values[v]=v%2?-2:1;ds.push_back(d);}auto influence=build_direction_influence(ast,ds,b);
 for(auto const& d:ds)for(unsigned n=0;n<ast.nodes.size();++n)REQUIRE(depends_on(old.dependencies[n],d.values)==depends_on_direction(n,d.affected));
 std::vector<IntegerDirection> empty;REQUIRE(build_direction_influence(ast,empty,b).node_directions.empty());
 std::vector<Node> nodes;for(unsigned n=0;n<12000;++n)nodes.push_back(node(Op::Neg,false,{n+1}));nodes.push_back(node(Op::Variable,false,{},0));auto deep=finish(nodes,1);std::vector<IntegerDirection> one{{0,0,0,{{0,1}}, {}}};auto bits=build_direction_influence(deep,one,b);REQUIRE(one[0].affected.size()==12001);
}
// Exact integer scores, every-event sync, identities, cancellation/recovery and extreme signatures.
for(unsigned count:{0,3,7,9,16,32})for(bool same:{false,true}){
 WorkBudget b;std::vector<Node> ns(128,node(Op::Constant,false));ns[0]=node(Op::Constant,true,{},-1,1);Ast ast=finish(ns,0);DirectionPool pool;pool.influence.direction_count=count;pool.influence.node_directions.resize(ns.size());
 for(unsigned d=0;d<count;++d){IntegerDirection dir;dir.id=d;for(unsigned n=0;n<ns.size();++n)if(same||((n+17*d)%37)<20){dir.affected.push_back(n);pool.influence.node_directions[n][d/64]|=uint64_t(1)<<(d%64);}pool.directions.push_back(dir);}
 auto index=build_score_index(ast,pool,b);auto state=initial_score_state(ast,index,b);ObservationHistory history(ns.size());
 auto check=[&](std::string id,uint64_t event){sync_scores(ast,history,id,index,state,b);std::vector<uint64_t> expected;auto selected=select_directions(pool,ast,history,event,b,&expected);REQUIRE(expected==state.direction_score);REQUIRE(selected==select_scores(state.direction_score,event,b));};
 check("L1",0);for(unsigned n=0;n<ns.size();++n)history.zero[n]=ast.nodes[n].mask();++history.version;check("L1",2);auto before=state.direction_score;history.version++;check("L1",UINT64_MAX);REQUIRE(state.direction_score==before);
 for(unsigned n=0;n<ns.size();n+=3)history.one[n]=3&ast.nodes[n].mask();++history.version;check("L1",3);check("L2",3);
 history=ObservationHistory(ns.size());check("L2",4);for(unsigned n=0;n<ns.size();++n){history.zero[n]=ast.nodes[n].mask();history.one[n]=ast.nodes[n].mask();}++history.version;
 for(auto stage:{RepairStage::ScoreSyncNodes,RepairStage::ScoreSyncGroups,RepairStage::ScorePublish}){auto old=state;CostTrace tr;b.trace=&tr;bool fired=false;b.cancelled=[&](){if(tr.stage==stage){fired=true;return true;}return false;};try{sync_scores(ast,history,"L2",index,state,b);REQUIRE(false);}catch(Exhausted const&){}REQUIRE(fired&&state.direction_score==old.direction_score&&state.covered_snapshot==old.covered_snapshot&&state.version==old.version);b.cancelled={};b.trace=nullptr;check("L2",5);state=old;}
 check("rebuilt_session",8);auto other=ast;sync_scores(other,history,"L2",index,state,b);REQUIRE(state.formula==&other);
}
// A fake clock is for correctness only. The 18ms view shares the 20ms origin.
{WorkBudget budget(.020,.020);double elapsed=0;budget.wall_clock=[&](){return budget.start_wall+elapsed;};budget.cpu_clock=[&](){return budget.start_cpu+elapsed;};auto search=budget.view(.018,.018);elapsed=.017;search.check();elapsed=.019;bool exhausted=false;try{search.check();}catch(Exhausted const&){exhausted=true;}REQUIRE(exhausted);
 auto ast=finish({node(Op::Ge,true,{1,2}),node(Op::Variable,false,{},0),node(Op::Constant,false)},1);WorkBudget unbounded;OutputLedger h(ast.nodes.size());auto n=observe_official(ast,{0},unbounded);h.commit({0},n);Candidate c{{1},observe_official(ast,{1},unbounded),{1,1},0,1};auto original=h.observations;
 elapsed=.017;BudgetedDeliveryTransaction transaction(h);transaction.prepare(c,budget);elapsed=.021;transaction.decide(budget,true,false);REQUIRE(!transaction.delivered&&h.observations.version==original.version);
 elapsed=.017;BudgetedDeliveryTransaction tail(h);tail.prepare(c,budget);tail.decide(budget,true,false);REQUIRE(tail.delivered);elapsed=.021;tail.recheck(budget);REQUIRE(!tail.delivered&&h.observations.zero==original.zero&&h.observations.one==original.one&&h.unique.size()==1);
 h.commit({2},observe_official(ast,{2},unbounded));REQUIRE(h.unique.count(assignment_key({1}))==0);
}

for(auto const& fixture:all_fixtures.at("blocking")){
 WorkBudget b;auto ast=ast_from_json(fixture.at("ast"),b);auto ir=compile_affine_ir(ast,b,RepairMode::ValueCache);auto m=assignment_from(fixture.at("anchor"));auto eq=collect_mandatory_equalities(ir,b);Json domains=Json::array();
 for(auto const& dj:fixture.at("directions")){IntegerVector d;for(auto const& v:dj)d[v[0].get<unsigned>()]=Big(v[1].get<std::string>());AnchorValues values(ir,m,0,b);RecordedDomainEvidence sink;LineDomain domain(ir,m,d,b,&values,nullptr,&sink);auto u=domain.formula();Json row={{"fixture",fixture.at("name")},{"ast",ast_json(ast)},{"anchor",fixture.at("anchor")},{"coefficients",dj},{"root_domain",domain_json(u)},{"certificate",sink.nodes},{"all_equality_dots",full_equality_dots(eq,d,b)}};blocking_evidence.push_back(row);domains.push_back(domain_json(u));
  RecordedDomainEvidence limited;limited.limit=1;LineDomain limit(ir,m,d,b,&values,nullptr,&limited);bool caught=false;try{limit.formula();}catch(Exhausted const& e){caught=std::string(e.what())=="evidence_limit";}REQUIRE(caught);
 }
 auto name=fixture.at("name").get<std::string>();if(name=="coordinated"){REQUIRE(domains[0]==Json::parse(R"([["0","0"]])")&&domains[1]==Json::parse(R"([["0","0"]])"));REQUIRE(domains[2]!=Json::parse(R"([["0","0"]])"));}
 if(name=="integer_rounding"||name=="opposite_tight")REQUIRE(domains[0]==Json::parse(R"([["0","0"]])"));
 if(name=="or_far")REQUIRE(domains[0]==Json::parse(R"([["0","0"],["2","2"]])"));
 if(name=="three_way"){for(unsigned i=0;i<6;++i)REQUIRE(domains[i]==Json::parse(R"([["0","0"]])"));REQUIRE(domains[6]!=Json::parse(R"([["0","0"]])"));}
}

// New cancellation boundaries: no stale score, no partially saved candidate, and no late commit.
{WorkBudget b;auto ast=ast_from_json(fixtures[0]["ast"],b);auto m0=assignment_from(fixtures[0]["models"][0]),m1=assignment_from(fixtures[0]["models"][1]);auto native=observe_official(ast,m1,b);OutputLedger output(ast.nodes.size());output.commit(m0,observe_official(ast,m0,b));
 for(auto st:{RepairStage::VerifyDirections,RepairStage::BuildAffected,RepairStage::BuildScoreIndex}){WorkBudget timed;CostTrace tr;timed.trace=&tr;bool fired=false;timed.cancelled=[&](){if(tr.stage==st){fired=true;return true;}return false;};try{Refiner r(ast,timed,delivery_strategies("V3"));REQUIRE(false);}catch(Exhausted const&){}REQUIRE(fired);}
 Refiner r(ast,b,delivery_strategies("V3"));auto state=initial_score_state(r.ir.ast,*r.score_index,b);
 for(auto st:{RepairStage::ScoreSyncNodes,RepairStage::FormulaDomain,RepairStage::ValidateFormula,RepairStage::OfficialObserve,RepairStage::SaveCandidate}){WorkBudget timed;CostTrace tr;timed.trace=&tr;bool fired=false;timed.cancelled=[&](){if(tr.stage==st){fired=true;return true;}return false;};auto result=r.try_refine(m1,native,output,2,timed,false,{},StopPolicy::FirstCovered,&state,"cancel_test");REQUIRE(fired&&result.cancellation=="cancelled");REQUIRE(!result.chosen);REQUIRE(output.committed_count==1);}
 for(auto st:{RepairStage::SerializeResult,RepairStage::DeliveryCleanup}){CostTrace tr;WorkBudget timed;timed.trace=&tr;timed.cancelled=[&](){return tr.stage==st;};bool canceled=false;try{StageScope phase(&tr,st);timed.check();}catch(Exhausted const&){canceled=true;}REQUIRE(canceled);REQUIRE(output.committed_count==1);}
}
// Handled local exhaustion is incomplete even without exception unwinding.
{CostTrace tr;WorkBudget w(60,60,4096);w.trace=&tr;{StageScope outer(&tr,RepairStage::FormulaDomain);{StageScope inner(&tr,RepairStage::ModularHits);try{w.integer(Big(1)<<4096);REQUIRE(false);}catch(Exhausted const&){} }}REQUIRE(tr.records[unsigned(RepairStage::ModularHits)].incomplete==1&&tr.records[unsigned(RepairStage::ModularHits)].completed==0);REQUIRE(tr.records[unsigned(RepairStage::FormulaDomain)].incomplete==1);{StageScope domain(&tr,RepairStage::FormulaDomain);DomainBudget work{w};work.operations=200000;try{work.tick();REQUIRE(false);}catch(Exhausted const&){} }REQUIRE(tr.records[unsigned(RepairStage::FormulaDomain)].completed==0);}
// Separate AST occurrences of the same original variable and mark wraparound.
{auto a=finish({node(Op::Add,false,{1,2,3,4}),node(Op::Sub,false,{5,6}),node(Op::Mul,false,{5,7}),node(Op::Variable,false,{},2),node(Op::Variable,false,{},3),node(Op::Variable,false,{},0),node(Op::Variable,false,{},0),node(Op::Variable,false,{},1)},4);WorkBudget w;auto old=compile_affine_ir(a,w),fresh=compile_affine_ir(a,w,RepairMode::Shared);ScratchMarks marks(a.nodes.size());marks.epoch=UINT32_MAX;std::fill(marks.marks.begin(),marks.marks.end(),1);for(unsigned support=0;support<16;++support){IntegerVector d;for(unsigned v=0;v<4;++v)d[v]=(support>>v&1)?Big(v%2?-3:2):Big(0);auto affected=collect_affected(fresh.reverse,d,marks,w);for(unsigned n=0;n<a.nodes.size();++n){REQUIRE(depends_on(old.dependencies[n],d)==depends_on_direction(n,affected));++checks;}}}
{WorkBudget b;ScratchMarks marks(4);marks.epoch=UINT32_MAX;std::fill(marks.marks.begin(),marks.marks.end(),1);unsigned calls=0;b.cancelled=[&](){return ++calls==2;};try{marks.next(b);REQUIRE(false);}catch(Exhausted const&){}REQUIRE(marks.epoch==UINT32_MAX);b.cancelled={};marks.next(b);REQUIRE(marks.epoch==1&&std::all_of(marks.marks.begin(),marks.marks.end(),[](auto n){return n==0;}));}
// A 12000-deep DAG must not use C++ recursion, including canceled requests.
std::vector<Node> ns;for(unsigned i=0;i<12000;++i)ns.push_back(node(Op::Neg,false,{i+1}));ns.push_back(node(Op::Variable,false,{},0));auto deep=finish(ns,1);WorkBudget b;CostTrace ct;b.trace=&ct;NumericEvalCache cache(deep,Assignment{Big(-7)},1,b);REQUIRE(cache.value(0,b)==-7);auto allocations=ct.records[unsigned(RepairStage::NumericValues)].full_size_allocations;auto nodes=ct.records[unsigned(RepairStage::NumericValues)].nodes;for(int i=0;i<20;++i)REQUIRE(cache.value(0,b)==-7);REQUIRE(ct.records[unsigned(RepairStage::NumericValues)].full_size_allocations==allocations);REQUIRE(ct.records[unsigned(RepairStage::NumericValues)].nodes-nodes==20);REQUIRE(ct.records[unsigned(RepairStage::NumericValues)].full_size_scans==0);
NumericEvalCache interrupted(deep,Assignment{Big(-7)},2,b);unsigned calls=0;b.cancelled=[&](){return ++calls==18020;};bool canceled=false;try{interrupted.value(0,b);}catch(Exhausted const&){canceled=true;}REQUIRE(canceled&&!interrupted.ready(0));unsigned ready=0;for(unsigned i=0;i<deep.nodes.size();++i)ready+=interrupted.ready(i);REQUIRE(ready>0&&ready<deep.nodes.size());b.cancelled={};REQUIRE(interrupted.value(0,b)==-7);
// Short circuit never evaluates an unselected invalid operation.
auto branch=finish({node(Op::Ite,false,{1,2,3}),node(Op::Constant,true,{},-1,1),node(Op::Variable,false,{},0),node(Op::Div,false,{2,4}),node(Op::Constant,false)},1);NumericEvalCache shortc(branch,Assignment{Big(-9)},1,b);REQUIRE(shortc.value(0,b)==-9&&!shortc.ready(3));branch.nodes[3].op=Op::Unknown;NumericEvalCache shortc2(branch,Assignment{Big(-9)},2,b);REQUIRE(shortc2.value(0,b)==-9&&!shortc2.ready(3));
// Different complete anchors, event identities and formula identities.
auto two=finish({node(Op::Add,false,{1,2}),node(Op::Variable,false,{},0),node(Op::Variable,false,{},1)},2);unsigned event=0;for(Assignment m:{Assignment{0,1},Assignment{2,-3},Assignment{-1,Big(1)<<63}}){NumericEvalCache c(two,m,++event,b);REQUIRE(c.value(0,b)==m[0]+m[1]);REQUIRE(c.matches(two,m,event));REQUIRE(!c.matches(two,m,event+1));auto other=two;REQUIRE(!c.matches(other,m,event));auto changed=m;++changed[0];REQUIRE(!c.matches(two,changed,event));}
// AST intermediates and merged-affine intermediates deliberately differ.
auto bitast=finish({node(Op::Sub,false,{1,2}),node(Op::Add,false,{2,3}),node(Op::Variable,false,{},0),node(Op::Constant,false,{},-1,1)},1);WorkBudget limited(60,60,4096);Assignment huge{(Big(1)<<4096)-1};auto ir=compile_affine_ir(bitast,limited,RepairMode::ValueCache);AnchorValues values(ir,huge,1,limited);IntegerVector step{{0,1}};LineValues line(ir,huge,step,values,{});REQUIRE(line.value(0,limited).constant==1);bool overflow=false;try{values.numeric.value(0,limited);}catch(Exhausted const& e){overflow=std::string(e.what())=="integer_bit_limit";}REQUIRE(overflow);REQUIRE(line.value(0,limited).constant==affine_on_line(ir,0,huge,step,limited).constant);
// Cached hidden y cannot satisfy official Reach-sensitive protection.
auto visibility=finish({node(Op::Or,true,{1,4}),node(Op::Eq,true,{2,3}),node(Op::Variable,false,{},0),node(Op::Constant,false),node(Op::Ge,true,{5,3}),node(Op::Variable,false,{},1)},2);Assignment m{1,0},q{0,0};auto native=observe_official(visibility,m,b);ObservationHistory empty(visibility.nodes.size());auto protect=make_protected(native,empty,b);NumericEvalCache hidden(visibility,q,1,b);REQUIRE(hidden.value(5,b)==0);auto observed=observe_official(visibility,q,b);REQUIRE(!observed.values[5]);REQUIRE(!missing(protect,observed,b).empty());
// Cancellation at each required stage, plus no false completed direction.
auto f=fixtures.at(0);WorkBudget unlimited;auto ast=ast_from_json(f.at("ast"),unlimited);Refiner r(ast,unlimited,RepairMode::Shared);auto m0=assignment_from(f.at("models").at(0)),m1=assignment_from(f.at("models").at(1));auto base=observe_official(ast,m1,unlimited);OutputLedger history(ast.nodes.size());history.commit(m0,observe_official(ast,m0,unlimited));Json cancellation=Json::array();
for(auto stage:{RepairStage::DependencyIndex,RepairStage::FormulaDomain,RepairStage::ModularHits,RepairStage::ValidateFormula}){WorkBudget w;CostTrace t;w.trace=&t;bool fired=false;w.cancelled=[&](){if(t.stage==stage){fired=true;return true;}return false;};if(stage==RepairStage::DependencyIndex){try{Refiner fail(ast,w,RepairMode::Shared);REQUIRE(false);}catch(Exhausted const&){}}else{auto rr=r.try_refine(m1,base,history,2,w);REQUIRE(rr.cancellation=="cancelled");if(stage==RepairStage::FormulaDomain)REQUIRE(rr.directions[0]["status"]=="incomplete");}REQUIRE(fired&&t.last_incomplete==stage);if(stage!=RepairStage::DependencyIndex)REQUIRE(t.last_direction>=0);cancellation.push_back(t.json());}
std::ofstream out(argv[2]);out<<Json{{"passed",true},{"semantic_checks",checks},{"cancellation_stages",cancellation},{"deep_nodes",deep.nodes.size()},{"ready_after_cancel",ready},{"numeric_trace",ct.json()},{"fixed_workload",evidence},{"four_configurations",four_evidence},{"first_covered_checks",first_covered_checks},{"blocking",blocking_evidence}}.dump(2)<<'\n';std::cout<<"PASS mechanisms "<<checks<<"\n";
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
