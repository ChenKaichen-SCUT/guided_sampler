#pragma once
#include "util/a_state.h"
#include "ast/ast_smt2_pp.h"
#include "model/model.h"
#include <fstream>
#include <set>
namespace s3 {
using Json=a2::Json;
inline bool enabled(){static bool x=std::getenv("GUIDED_SEMANTIC_TRACE_DIR")!=nullptr;return x;}
inline std::string directory(){auto p=std::getenv("GUIDED_SEMANTIC_TRACE_DIR");return p?p:"";}
inline void write(Json const& j){if(!enabled())return;static std::mutex mx;std::lock_guard<std::mutex> l(mx);std::ofstream f(directory()+"/semantic.jsonl",std::ios::app);f<<j.dump()<<'\n';}
inline std::string text(expr* e,ast_manager& m){std::ostringstream o;o<<mk_ismt2_pp(e,m);return o.str();}
inline std::string sort_text(sort* s,ast_manager& m){std::ostringstream o;o<<mk_ismt2_pp(s,m);return o.str();}
inline Json identity(std::shared_ptr<a2::Run> const& r,unsigned b,unsigned g){auto p=std::getenv("GUIDED_SEMANTIC_RUN_ID");return {{"run_id",p?p:directory()},{"external_query_id",r->query},{"backend_call_id",b},{"context_generation",g},{"coverage_version",r->version}};}
// Bounded converter output: never first allocate an unbounded display string.
struct BoundedBuffer:std::streambuf {std::string value;size_t cap;bool truncated=false;explicit BoundedBuffer(size_t n):cap(n){};int overflow(int c)override {if(c!=EOF){if(value.size()<cap)value.push_back(char(c));else truncated=true;}return c;}};
struct Watch {unsigned var,decision;expr* atom;uint64_t token=0;bool active=false;int relevant=-1;Json action;};
// All expression references belong to this manager. No lookup by printed names.
struct PendingSemanticSnapshot {
 ast_manager& m;expr_ref_vector refs;std::weak_ptr<a2::Run> run;Json id;unsigned backend,generation;uint64_t serial=0;
 std::vector<Watch> watches;Json events=Json::array(),encounters=Json::array();bool overflow=false,flushed=false;unsigned causal_watch=~0u;
 std::map<std::tuple<unsigned,unsigned,unsigned,bool>,std::vector<std::pair<unsigned,uint64_t>>> theory_causes;
 PendingSemanticSnapshot(ast_manager& m,std::shared_ptr<a2::Run> r,unsigned b,unsigned g):m(m),refs(m),run(r),id(identity(r,b,g)),backend(b),generation(g){}
 Json base()const{return id;}
 void add(unsigned v,expr* e,unsigned d,Json a){refs.push_back(e);watches.push_back({v,d,e,0,false,-1,std::move(a)});}
 void event(unsigned i,char const* kind,unsigned level,unsigned trail,int truth=-1,int relevant=-1){if(events.size()>=8192){overflow=true;return;}auto const& w=watches[i];events.push_back({{"kind",kind},{"watch",i},{"decision_id",w.decision},{"assignment_token",w.token},{"level",level},{"trail_index",trail},{"truth",truth<0?Json(nullptr):Json(bool(truth))},{"relevant",relevant<0?Json(nullptr):Json(bool(relevant))}});}
 Json ast(expr* e){Json ds=Json::array();std::set<unsigned> seen,decls;std::vector<expr*> todo{e};while(!todo.empty()){expr* n=todo.back();todo.pop_back();if(!seen.insert(n->get_id()).second||!is_app(n))continue;auto* a=to_app(n);auto* f=a->get_decl();if(f->get_family_id()==null_family_id&&decls.insert(f->get_id()).second){Json dom=Json::array();for(unsigned j=0;j<f->get_arity();++j)dom.push_back(sort_text(f->get_domain(j),m));ds.push_back({{"decl_id",f->get_id()},{"name",f->get_name().str()},{"skolem",f->is_skolem()},{"arity",f->get_arity()},{"domain",dom},{"range",sort_text(f->get_range(),m)}});}for(expr* c:*a)todo.push_back(c);}return {{"expr",text(e,m)},{"sort",sort_text(e->get_sort(),m)},{"ast_id",e->get_id()},{"manager_identity",reinterpret_cast<uintptr_t>(&m)},{"declarations",ds}};}
 void flush(){if(flushed)return;flushed=true;Json row=base();row["kind"]="semantic_snapshot";row["overflow"]=overflow;row["encounters"]=encounters;row["events"]=events;row["watches"]=Json::array();for(unsigned i=0;i<watches.size();++i){auto const& w=watches[i];Json a=w.action;a["watch"]=i;a["decision_id"]=w.decision;a["native_var"]=w.var;a["actual_atom"]=ast(w.atom);a["last_assignment_token"]=w.token;a["token_active"]=w.active;row["watches"].push_back(a);}row["direct_entry_hooks_complete"]=true;row["indirect_euf_causal_association"]="only_synchronously_originating_queue_entries";write(row);}
 void model_layer(model* mdl,char const* layer,unsigned provider,std::string const& chain){if(!mdl)return;Json row=base();row["kind"]="model_layer";row["layer"]=layer;row["model_provider_backend_id"]=provider;row["converter_chain_id"]=chain;row["same_manager"]=(&mdl->get_manager()==&m);if(&mdl->get_manager()!=&m){row["status"]="manager_identity_mismatch";write(row);return;}Json vals=Json::array();model_ref copy;for(unsigned i=0;i<watches.size();++i){expr_ref value(m);bool ok=mdl->eval_expr(watches[i].atom,value,false);Json v={{"watch",i},{"without_completion",ok?Json(text(value,m)):Json(nullptr)},{"truth",ok&&m.is_true(value)?Json(true):ok&&m.is_false(value)?Json(false):Json(nullptr)}};if(v["truth"].is_null()){if(!copy)copy=mdl->copy();expr_ref completed(m);bool c=copy->eval_expr(watches[i].atom,completed,true);v["copy_completion"]=c?Json(text(completed,m)):Json(nullptr);}vals.push_back(v);}row["values"]=vals;write(row);}
};
inline std::set<std::string>& unmapped_keys(){static std::set<std::string> keys;return keys;}
inline bool select_unmapped(std::string const& key){static std::mutex mutex;std::lock_guard<std::mutex> lock(mutex);auto p=std::getenv("GUIDED_SEMANTIC_UNMAPPED_LIMIT");unsigned limit=p?std::stoul(p):8;auto& keys=unmapped_keys();if(keys.size()>=limit||keys.count(key))return false;keys.insert(key);return true;}
inline void outer(std::shared_ptr<a2::Run> const& r,model* mdl){if(!r||!enabled())return;unsigned provider=r->semantic_provider;for(auto const& p:r->semantic_snapshots){auto s=std::static_pointer_cast<PendingSemanticSnapshot>(p);if(s->backend==provider)s->model_layer(mdl,"M_outer",provider,r->semantic_chain);else {auto j=s->base();j["kind"]="leaf_discarded";j["model_provider_backend_id"]=provider;write(j);}}r->semantic_snapshots.clear();}
struct ConverterTrace {
 std::shared_ptr<a2::Run> run;Json entries=Json::array();size_t bytes=0;bool overflow=false;
 explicit ConverterTrace(std::shared_ptr<a2::Run> r):run(std::move(r)){}
 void finish(){Json row=identity(run,run->semantic_provider,0);row["kind"]="converter_definitions";row["converter_chain_id"]=run->semantic_chain;row["model_provider_backend_id"]=run->semantic_provider;row["entries"]=entries;row["overflow"]=overflow;write(row);}
};
inline ConverterTrace*& converter_trace(){static thread_local ConverterTrace* t=nullptr;return t;}
struct ConverterTraceScope {ConverterTrace trace;ConverterTrace* old;explicit ConverterTraceScope(std::shared_ptr<a2::Run> r):trace(std::move(r)),old(converter_trace()){converter_trace()=&trace;}~ConverterTraceScope(){converter_trace()=old;trace.finish();}};
inline void converter_entry(ast_manager& m,func_decl* f,expr* def,bool hide,char const* origin){auto* t=converter_trace();if(!t)return;if(t->entries.size()>=1024||t->bytes>=1048576){t->overflow=true;return;}PendingSemanticSnapshot view(m,t->run,t->run->semantic_provider,0);Json row={{"origin",origin},{"instruction",hide?"hide":"add"},{"manager_identity",reinterpret_cast<uintptr_t>(&m)},{"decl_id",f->get_id()},{"name",f->get_name().str()},{"skolem",f->is_skolem()},{"arity",f->get_arity()},{"range",sort_text(f->get_range(),m)}};if(def)row["definition"]=view.ast(def);auto size=row.dump().size();if(t->bytes+size>1048576){t->overflow=true;return;}t->bytes+=size;t->entries.push_back(std::move(row));}

}
