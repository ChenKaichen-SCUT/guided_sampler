
// Explicitly opt-in, thread-local request, active only around a host CDCL check.
// Definitions are installed inside the backend selected by native routing.
extern "C" {
Z3_API void Z3_expr_soft_begin(Z3_context c, unsigned n, Z3_ast const* goals, unsigned na, Z3_ast const* auxiliaries, unsigned window, unsigned nd, Z3_ast const* definitions) {
    expr_soft::active().reset();
    auto r = std::make_shared<expr_soft::request>(mk_c(c)->m());
    r->window = window;
    for(unsigned i=0;i<nd;++i)r->definitions.push_back(to_expr(definitions[i]));
    for (unsigned i = 0; i < n; ++i) {
        expr* e = to_expr(goals[i]);
        if (!r->manager->is_bool(e)) return;
        r->goals.push_back(e);
        r->working_goals.push_back(e);
    }
    for (unsigned i=0;i<na;++i) {
        expr* e=to_expr(auxiliaries[i]);
        if (!is_app(e) || to_app(e)->get_num_args()!=0) return;
        r->auxiliary_refs.push_back(e);
        r->auxiliary.insert(to_app(e)->get_decl());
    }
    expr_soft::active() = std::move(r);
}
Z3_API void Z3_expr_soft_stats(uint64_t* out) {
    auto r = expr_soft::active();
    for (unsigned i = 0; i < 12; ++i) out[i] = 0;
    if (!r) return;
    out[0] = r->prepared; out[1] = r->chosen;
    out[2] = r->already_true; out[3] = r->already_false;
    out[4] = r->decisions; out[5] = r->next;
    out[6] = r->auxiliary_map_skips; out[7] = r->window_skips;
    out[8] = r->tactic_routes; out[9] = r->incremental_routes;
    out[10] = r->mapped; out[11] = r->mapping_failures;
}
Z3_API void Z3_expr_soft_end() { auto r=expr_soft::active(); if(r&&r->cleanup)r->cleanup(); expr_soft::active().reset(); }
}
