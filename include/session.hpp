#pragma once
#include "guidance_bridge.hpp"
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
    Clock::time_point start=Clock::now();z3::context& c;double wall;std::optional<size_t> limit;
    size_t test_query_limit=0;
    std::string dir;std::vector<z3::expr> variables;std::set<unsigned> original_decls;
    std::set<std::string> unique;size_t formal=0,raw=0,query=0;std::string source="CDCL",status="finished";
    std::ofstream receipts,models,queries;std::unique_ptr<GuidanceBridge> guidance;
    std::atomic<bool> done=false;std::thread watchdog;Json last_guidance;
    double query_begin=0,prepare_seconds=0,extract_seconds=0;unsigned requested=0,granted=0;Json assumptions;unsigned highdiv_seed=0;
    Session(z3::context& c,double wall,std::optional<size_t> limit,std::string dir):c(c),wall(wall),limit(limit),dir(dir),
        receipts(dir+"/sample_receipts.jsonl"),models(dir+"/models.jsonl"),queries(dir+"/queries.jsonl") {
        if(!receipts||!models||!queries)throw std::runtime_error("Cannot create session logs");
        if(auto v=std::getenv("HIGHDIV_TEST_MAX_QUERIES"))test_query_limit=std::stoull(v);
        std::signal(SIGTERM,signal_handler);std::signal(SIGINT,signal_handler);
        watchdog=std::thread([this]{while(!done.load()){if(interrupted||elapsed()>=this->wall){this->c.interrupt();return;}std::this_thread::sleep_for(std::chrono::milliseconds(10));}});
    }
    ~Session(){done=true;if(watchdog.joinable())watchdog.join();}
    double elapsed()const{return std::chrono::duration<double>(Clock::now()-start).count();}
    bool stop()const{return (test_query_limit&&query>=test_query_limit)||interrupted||elapsed()>=wall||(limit&&formal>=*limit);}
    double remaining()const{return std::max(0.0,wall-elapsed());}
    void load(z3::expr const& formula,unsigned mode) {
        std::set<unsigned> seen;std::vector<z3::expr> stack{formula};std::set<std::string> names;
        while(!stack.empty()) {
            auto e=stack.back();stack.pop_back();if(!seen.insert(e.id()).second)continue;
            if(!e.is_app())throw std::runtime_error("Unsupported original AST");
            if(e.is_const()&&e.decl().decl_kind()==Z3_OP_UNINTERPRETED) {
                if(!e.is_int()&&!e.is_bool())throw std::runtime_error("Only Int/Bool free variables supported");
                auto name=e.decl().name().str();
                if(name.find_first_of(":;\n\r")!=std::string::npos||!names.insert(name).second)throw std::runtime_error("Original name incompatible with official metric");
                variables.push_back(e);original_decls.insert(e.decl().id());
            }
            for(unsigned i=e.num_args();i>0;--i)stack.push_back(e.arg(i-1));
        }
        std::sort(variables.begin(),variables.end(),[](auto const& a,auto const& b){return a.decl().name().str()<b.decl().name().str();});
        if(mode) {auto t=Clock::now();guidance=std::make_unique<GuidanceBridge>(formula,mode,wall,dir);guidance->cost+=std::chrono::duration<double>(Clock::now()-t).count();}
        else {std::ofstream(dir+"/guidance_events.jsonl");std::ofstream(dir+"/target_catalog.jsonl");}
    }
    void begin_query(std::string const& phase,z3::expr_vector const& asms,unsigned request,unsigned grant) {
        source=phase;++query;requested=request;granted=grant;assumptions=Json::array();for(auto e:asms)assumptions.push_back(e.to_string());query_begin=elapsed();
    }
    void end_query(z3::solver& solver,z3::check_result result,Json stats=Json::object(),double check_end=-1) {
        double end=check_end<0?elapsed():check_end;std::ostringstream ss;ss<<solver.statistics();
        queries<<Json({{"query",query},{"source",source},{"start",query_begin},{"end",end},{"check_seconds",end-query_begin},{"guidance_prepare_seconds",prepare_seconds},
            {"requested_timeout",requested},{"granted_timeout",granted},{"timeout_unit",source=="CDCL"?"milliseconds":"seconds"},
            {"assumptions",assumptions},{"highdiv_ls_seed",source=="CCSS"?Json(highdiv_seed):Json(nullptr)},{"result",result==z3::sat?"sat":result==z3::unsat?"unsat":"unknown"},
            {"reason_unknown",result==z3::unknown?solver.reason_unknown():""},{"statistics_cumulative",ss.str()},{"guidance",stats}}).dump()<<'\n';queries.flush();last_guidance=stats;
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
        if(guidance){auto t=Clock::now();ev=guidance->ast.evaluate(assignment);if(!ev->values[0]||*ev->values[0]==0)throw std::runtime_error("Observer/model validation disagreement");guidance->cost+=std::chrono::duration<double>(Clock::now()-t).count();}
        samples<<raw<<": "<<line<<'\n';samples.flush();if(!samples)throw std::runtime_error("Raw sample flush failed");
        rec["output_complete"]=elapsed();rec["raw_index"]=raw++;rec["formal_index"]=formal;rec["typed"]=typed;
        rec["new_observed"]=ev?Json(ev->observed):Json(nullptr);rec["new_covered"]=ev?Json(ev->covered):Json(nullptr);
        rec["coverage_version"]=guidance?Json(guidance->ast.version+1):Json(nullptr);
        rec["covered"]=guidance?Json(guidance->ast.covered+ev->covered):Json(nullptr);
        if(ev)rec["target_outcomes"]=guidance->outcomes(*ev);
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
        unique.insert(key);++formal;if(guidance)guidance->ast.commit(*ev);return true;
    }
    void finish() {
        done=true;if(watchdog.joinable())watchdog.join();
        if(status=="finished")status=limit&&formal>=*limit?"complete100":elapsed()>=wall?"deadline":interrupted?"cancelled":formal?"finished":"no_model";
        std::ofstream f(dir+"/summary.json");f<<Json({{"status",status},{"formal_count",formal},{"raw_count",raw},{"queries",query},{"elapsed",elapsed()},{"wall_limit",wall},{"sample_limit",limit?Json(*limit):Json(nullptr)},{"guidance_cost",guidance?guidance->cost:0},{"coverage",guidance?Json(guidance->ast.covered):Json(nullptr)},{"total",guidance?Json(guidance->ast.total):Json(nullptr)}}).dump(2)<<'\n';
    }
};
}
