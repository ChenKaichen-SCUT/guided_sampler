#pragma once
#include "a_guidance_bridge.hpp"
#include "inherited_reference.hpp"
#include <csignal>
#include <thread>
#include <atomic>
#include <iomanip>
#include <sstream>
#include <fstream>
namespace guided {
inline volatile sig_atomic_t interrupted=0;
inline void signal_handler(int){interrupted=1;}
inline std::string identity_hash(std::string const& key){uint64_t h=14695981039346656037ULL;for(unsigned char c:key){h^=c;h*=1099511628211ULL;}std::ostringstream o;o<<std::hex<<std::setw(16)<<std::setfill('0')<<h;return o.str();}
class Session {
public:
    unsigned host_mode=0,last_ls_query=0;OriginalDeclarations original_expressions;
    bool soft_reference()const{return host_mode==3||host_mode==4;}
    void register_inputs(QueryInputs const& inputs){
        if(!guidance)return;if(guidance->index->active)throw std::runtime_error("reference updated during active check");
        auto q=std::make_shared<a2::r4::QueryPreferences>();q->policy=host_mode==4?a2::r4::Policy::Coverage:a2::r4::Policy::Reference;q->reference=inputs.reference.values;q->source_query=last_ls_query;
        Json hard=Json::array();for(auto e:inputs.user_hard)hard.push_back(e.to_string());q->hard_count=hard.size();q->reference_count=inputs.reference.selected.size();q->hard_hash=reference_digest(hard.dump());q->reference_hash=reference_digest(inputs.reference.selected.dump());
        guidance->index->preferences=q;std::ofstream f(dir+"/query_inputs.jsonl",std::ios::app);f<<Json({{"query_id",query+1},{"policy",host_mode==4?"S_cov":"S_ref"},{"hard_assumptions",hard},{"hard_assumptions_count",q->hard_count},{"hard_assumptions_hash",q->hard_hash},{"reference",inputs.reference.selected},{"reference_count",q->reference_count},{"reference_defined_count",q->reference.size()},{"reference_hash",q->reference_hash},{"reference_source_query",last_ls_query},{"history_hard_blocker_removed",q->reference_count},{"selection_rate",0.5},{"selection_draws",inputs.reference.draws},{"rng_before",inputs.reference.rng_before},{"rng_after",inputs.reference.rng_after},{"rng_hash_algorithm","fnv1a64_stream_mt19937"}}).dump()<<'\n';
    }
    void ls_reference_source(z3::model const& model){
        last_ls_query=query;if(!soft_reference())return;auto started=Clock::now();Json entries=Json::array();for(unsigned j=0;j<model.size();++j){auto d=model[j];entries.push_back({{"model_index",j},{"decl_id",d.id()},{"name",d.name().str()},{"original",bool(original_decls.count(d.id()))},{"constant",d.is_const()},{"value",d.is_const()?Json(model.get_const_interp(d).to_string()):Json(nullptr)}});}
        std::ofstream f(dir+"/reference_sources.jsonl",std::ios::app);f<<Json({{"query_id",query},{"source","CCSS_converted_m_ls"},{"entries",entries}}).dump()<<'\n';f.flush();if(guidance)guidance->charge("reference_source_log_seconds",std::chrono::duration<double>(Clock::now()-started).count());
    }
    Clock::time_point start=Clock::now();z3::context& c;double wall;std::optional<size_t> limit;
    size_t test_query_limit=0,cdcl_limit=0,cdcl_count=0;
    bool semantic=std::getenv("GUIDED_SEMANTIC_TRACE_DIR")!=nullptr;
    bool cdcl_cap_reached()const{return cdcl_limit&&cdcl_count>=cdcl_limit;}
    std::string dir;std::vector<z3::expr> variables;std::set<unsigned> original_decls;
    std::set<std::string> unique;size_t formal=0,raw=0,query=0;std::string source="CDCL",status="finished";
    std::ofstream receipts,models,queries;std::unique_ptr<AGuidanceBridge> guidance;
    std::atomic<bool> done=false;std::thread watchdog;Json last_guidance;
    double query_begin=0,prepare_seconds=0,extract_seconds=0;unsigned requested=0,granted=0;Json assumptions;unsigned highdiv_seed=0;
    Session(z3::context& c,double wall,std::optional<size_t> limit,std::string dir):c(c),wall(wall),limit(limit),dir(dir),
        receipts(dir+"/sample_receipts.jsonl"),models(dir+"/models.jsonl"),queries(dir+"/queries.jsonl") {
        if(!receipts||!models||!queries)throw std::runtime_error("Cannot create session logs");
        if(auto v=std::getenv("HIGHDIV_TEST_MAX_QUERIES"))test_query_limit=std::stoull(v);
        if(auto v=std::getenv("GUIDED_SEMANTIC_CDCL_LIMIT"))cdcl_limit=std::stoull(v);
        std::signal(SIGTERM,signal_handler);std::signal(SIGINT,signal_handler);
        watchdog=std::thread([this]{while(!done.load()){if(interrupted||elapsed()>=this->wall){this->c.interrupt();return;}std::this_thread::sleep_for(std::chrono::milliseconds(10));}});
    }
    ~Session(){done=true;if(watchdog.joinable())watchdog.join();}
    double elapsed()const{return std::chrono::duration<double>(Clock::now()-start).count();}
    bool stop()const{return (test_query_limit&&query>=test_query_limit)||interrupted||elapsed()>=wall||(limit&&formal>=*limit);}
    double remaining()const{return std::max(0.0,wall-elapsed());}
    void load(z3::expr const& formula,unsigned mode) {
        host_mode=mode;
        std::set<unsigned> seen;std::vector<z3::expr> stack{formula};std::set<std::string> names;
        while(!stack.empty()) {
            auto e=stack.back();stack.pop_back();if(!seen.insert(e.id()).second)continue;
            if(!e.is_app())throw std::runtime_error("Unsupported original AST");
            if(e.is_const()&&e.decl().decl_kind()==Z3_OP_UNINTERPRETED) {
                if(!e.is_int()&&!e.is_bool())throw std::runtime_error("Only Int/Bool free variables supported");
                auto name=e.decl().name().str();
                if(name.find_first_of(":;\n\r")!=std::string::npos||!names.insert(name).second)throw std::runtime_error("Original name incompatible with official metric");
                variables.push_back(e);original_decls.insert(e.decl().id());original_expressions.emplace(e.decl().id(),e);
            }
            for(unsigned i=e.num_args();i>0;--i)stack.push_back(e.arg(i-1));
        }
        std::sort(variables.begin(),variables.end(),[](auto const& a,auto const& b){return a.decl().name().str()<b.decl().name().str();});
        if(mode) {auto t=Clock::now();guidance=std::make_unique<AGuidanceBridge>(formula,mode,wall,dir);guidance->charge("observer_initialization_seconds",std::max(0.0,std::chrono::duration<double>(Clock::now()-t).count()-guidance->cost));}
        if(semantic&&guidance){Json nodes=Json::array();for(unsigned i=0;i<guidance->ast.nodes.size();++i){auto const& n=guidance->ast.nodes[i];Json cs=Json::array();for(unsigned j=0;j<n.e.num_args();++j)cs.push_back(guidance->ast.ids.at(n.e.arg(j).id()));nodes.push_back({{"node",i},{"ast_id",n.e.id()},{"expr",n.e.num_args()?Json(nullptr):Json(n.e.to_string())},{"decl_id",n.e.decl().id()},{"sort",n.e.get_sort().to_string()},{"operator",n.e.decl().decl_kind()},{"children",cs}});}std::ofstream f(dir+"/original_nodes.json");f<<nodes.dump()<<'\n';}
        if(!mode) {std::ofstream(dir+"/guidance_events.jsonl");std::ofstream(dir+"/target_catalog.jsonl");}
    }
    void begin_query(std::string const& phase,z3::expr_vector const& asms,unsigned request,unsigned grant) {
        source=phase;if(phase=="CDCL")++cdcl_count;++query;requested=request;granted=grant;assumptions=Json::array();for(auto e:asms)assumptions.push_back(e.to_string());query_begin=elapsed();
        if(semantic&&guidance&&phase=="CDCL") {Json masks=Json::array();for(auto const& n:guidance->ast.nodes)masks.push_back({std::to_string(n.seen0),std::to_string(n.seen1)});std::ofstream f(dir+"/coverage_snapshots.jsonl",std::ios::app);f<<Json({{"query_id",query},{"coverage_version",guidance->ast.version},{"seen_masks",masks}}).dump()<<'\n';}
    }
    void end_query(z3::solver& solver,z3::check_result result,Json stats=Json::object(),double check_end=-1) {
        double end=check_end<0?elapsed():check_end;std::ostringstream ss;ss<<solver.statistics();
        queries<<Json({{"query",query},{"source",source},{"start",query_begin},{"end",end},{"check_seconds",end-query_begin},{"guidance_prepare_seconds",prepare_seconds},
            {"requested_timeout",requested},{"granted_timeout",granted},{"timeout_unit",source=="CDCL"?"milliseconds":"seconds"},
            {"assumptions",assumptions},{"highdiv_ls_seed",source=="CCSS"?Json(highdiv_seed):Json(nullptr)},{"result",result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown"},
            {"reason_unknown",result==z3::unknown?solver.reason_unknown():""},{"statistics_cumulative",ss.str()},{"guidance",stats}}).dump()<<'\n';queries.flush();last_guidance=stats;
        if(guidance)guidance->query_finished(source,query,end-query_begin,result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown",stats);
    }
    bool commit(z3::model const& m,z3::expr const& formula,std::ofstream& samples) {
        double begin=elapsed();if(stop())return false;
        // Evaluate without completion in the solver model; complete a separate
        // original-variable snapshot, never mutate m_ls or the solver model.
        z3::model snapshot(c);std::map<std::string,Big> assignment;Json typed=Json::array();std::string key,line;
        for(auto const& v:variables) {
            auto value=m.eval(v,false);
            if(v.is_int()&&!value.is_numeral())value=c.int_val(0);
            if(v.is_bool()&&!value.is_true()&&!value.is_false())value=c.bool_val(false);
            auto d=v.decl();snapshot.add_const_interp(d,value);
            auto name=v.decl().name().str();Big exact=v.is_int()?numeral(value):Big(value.is_true());std::string val=exact.convert_to<std::string>();
            assignment[name]=exact;key+=std::to_string(name.size())+":"+name+(v.is_int()?"I":"B")+std::to_string(val.size())+":"+val;
            line+=name+":"+val+";";typed.push_back({{"name",name},{"sort",v.is_int()?"Int":"Bool"},{"value",val}});
        }
        if(semantic){Json vars=Json::array();for(auto const& v:variables){auto value=m.eval(v,false);vars.push_back({{"name",v.decl().name().str()},{"decl_id",v.decl().id()},{"sort",v.get_sort().to_string()},{"without_completion",value.to_string()},{"defined",value.is_numeral()||value.is_true()||value.is_false()}});}std::ofstream f(dir+"/semantic_host.jsonl",std::ios::app);f<<Json({{"kind","M_original"},{"query_id",query},{"source",source},{"original_projection",typed},{"M_outer_variables",vars},{"completion_policy","undefined original Int -> 0 / Bool -> false in separate snapshot"}}).dump()<<'\n';}
        bool legal=snapshot.eval(formula,true).is_true();
        bool duplicate=unique.count(key);Json rec={{"candidate",raw},{"query",query},{"source",source},{"start",begin},{"model_extract_seconds",extract_seconds},{"model_hash",identity_hash(key)},{"hash_algorithm","fnv1a64_full_key_compared"},{"legal",legal},{"duplicate",duplicate}};
        if(!legal||duplicate){
            samples<<raw<<": "<<line<<'\n';samples.flush();
            rec["raw_index"]=raw++;rec["typed"]=typed;rec["output_complete"]=elapsed();
            rec["kind"]="reject";rec["status"]=legal?"duplicate":"invalid";
            receipts<<rec.dump()<<'\n';receipts.flush();models<<rec.dump()<<'\n';models.flush();
            if(!samples||!receipts||!models)throw std::runtime_error("Rejected-candidate archive flush failed");
            if(!legal){status="invalid";throw std::runtime_error("Sampler returned model violating original formula");}
            return false;
        }
        std::optional<Evaluation> ev;
        if(guidance&&guidance->observing()){auto t=Clock::now();ev=guidance->ast.evaluate(assignment);if(!ev->values[0]||*ev->values[0]==0)throw std::runtime_error("Observer/model validation disagreement");guidance->record_observer(std::chrono::duration<double>(Clock::now()-t).count());}
        samples<<raw<<": "<<line<<'\n';samples.flush();if(!samples)throw std::runtime_error("Raw sample flush failed");
        rec["output_complete"]=elapsed();rec["raw_index"]=raw++;rec["formal_index"]=formal;rec["typed"]=typed;
        rec["new_observed"]=ev?Json(ev->observed):Json(nullptr);rec["new_covered"]=ev?Json(ev->covered):Json(nullptr);
        rec["coverage_version"]=ev?Json(guidance->ast.version+1):Json(nullptr);
        rec["covered"]=ev?Json(guidance->ast.covered+ev->covered):Json(nullptr);
        if(ev&&source=="CDCL"){auto t=Clock::now();guidance->pending_outcomes=guidance->outcomes(*ev);guidance->charge("outcome_evaluation_seconds",std::chrono::duration<double>(Clock::now()-t).count());}
        // Prepare receipt and typed record precede the commit marker. Offline
        // finalizer requires BOTH receipts and a bounded completion interval.
        rec["kind"]="prepare";receipts<<rec.dump()<<'\n';receipts.flush();
        models<<rec.dump()<<'\n';models.flush();
        if(!receipts||!models)throw std::runtime_error("Receipt flush failed");
        double commit_begin=elapsed();bool timely=commit_begin<wall&&!interrupted;
        Json marker={{"kind","commit"},{"raw_index",rec["raw_index"]},{"formal_index",formal},{"commit_begin",commit_begin},{"timely",timely}};
        receipts<<marker.dump()<<'\n';receipts.flush();double complete=elapsed();
        // Confirmation timestamp is after the commit receipt flush. A finalizer
        // ignores any interrupted/truncated transaction without this confirm.
        receipts<<Json({{"kind","confirm"},{"raw_index",rec["raw_index"]},{"commit_complete",complete},{"timely",timely&&complete<wall}}).dump()<<'\n';receipts.flush();
        if(!receipts)throw std::runtime_error("Commit receipt flush failed");
        if(!timely||complete>=wall)return false;
        if(semantic){std::ofstream f(dir+"/semantic_host.jsonl",std::ios::app);f<<Json({{"kind","M_formal"},{"query_id",query},{"source",source},{"formal_index",formal},{"typed",typed},{"model_hash",rec["model_hash"]}}).dump()<<'\n';}
        unique.insert(key);++formal;if(guidance){guidance->formal_record(rec);if(ev)guidance->commit(*ev);}return true;
    }
    void finish() {
        done=true;if(watchdog.joinable())watchdog.join();
        if(status=="finished")status=cdcl_cap_reached()?"cdcl_query_limit":limit&&formal>=*limit?"complete100":elapsed()>=wall?"deadline":interrupted?"cancelled":formal?"finished":"no_model";
        std::ofstream f(dir+"/summary.json");f<<Json({{"status",status},{"formal_count",formal},{"raw_count",raw},{"queries",query},{"cdcl_queries",cdcl_count},{"cdcl_query_limit",cdcl_limit},{"elapsed",elapsed()},{"wall_limit",wall},{"sample_limit",limit?Json(*limit):Json(nullptr)},{"guidance_cost",guidance?guidance->cost:0},{"coverage",guidance&&!guidance->disabled?Json(guidance->ast.covered):Json(nullptr)},{"total",guidance?Json(guidance->ast.total):Json(nullptr)},{"A_disabled",guidance?guidance->disabled:false},{"A_disabled_reason",guidance?guidance->disabled_reason:""},{"last_online_version",guidance?guidance->ast.version:0},{"A_exposure",guidance?guidance->exposure:0}}).dump(2)<<'\n';
    }
};
}
