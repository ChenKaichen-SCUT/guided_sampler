
namespace {
thread_local std::unordered_map<std::string,std::string> expr_exchange_saved;
thread_local ast_manager* expr_exchange_manager=nullptr;
}
extern "C" {
Z3_API void Z3_expr_ccss_begin(double budget_ms) { expr_ccss::begin(budget_ms); }
Z3_API void Z3_expr_ccss_end(double* stats) { expr_ccss::end(stats); }
// 0: size, 1: save before a guided query, 2: restore, 3: replace completely.
Z3_API unsigned Z3_expr_exchange(Z3_context c,unsigned action,unsigned n,char const*const* names,char const*const* values) {
    auto& m=mk_c(c)->m();auto& map=m.last_CDCL_model;
    if(action==1){expr_exchange_saved=map;expr_exchange_manager=&m;}
    if(action==2 && expr_exchange_manager==&m){map=std::move(expr_exchange_saved);expr_exchange_manager=nullptr;}
    if(action==3){map.clear();for(unsigned i=0;i<n;++i)map[names[i]]=values[i];}
    return unsigned(map.size());
}
Z3_API char const* Z3_expr_exchange_value(Z3_context c,char const* name) {
    auto& map=mk_c(c)->m().last_CDCL_model;auto it=map.find(name);
    return it==map.end()?nullptr:it->second.c_str();
}
}
