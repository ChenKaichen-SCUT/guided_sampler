    void Z3_API Z3_solver_set_coverage_guidance(Z3_context c,Z3_solver s,
        unsigned mode,unsigned epoch,unsigned version,
        unsigned nt,Z3_ast const preds[],unsigned const ids[],
        unsigned nh,Z3_ast const atoms[],unsigned const phases[],unsigned const indices[]) {
        Z3_TRY;
        RESET_ERROR_CODE();
        if(mode>3 || (mode==0 && (nt||nh)) || nt>8 || (nt && (!preds || !ids)) ||
           (nh && (!atoms || !phases || !indices))) { SET_ERROR_CODE(Z3_INVALID_ARG,nullptr);return; }
        auto p=std::make_shared<coverage_guidance>(mk_c(c)->m(),mode,epoch,version);
        for(unsigned i=0;i<nt;++i) {
            if(preds[i] && (!is_expr(to_ast(preds[i])) || !mk_c(c)->m().is_bool(to_expr(preds[i])))) {SET_ERROR_CODE(Z3_INVALID_ARG,nullptr);return;}
            p->predicates.push_back(preds[i]?to_expr(preds[i]):nullptr);p->ids.push_back(ids[i]);
        }
        std::set<std::tuple<expr*,unsigned,unsigned>> unique;
        for(unsigned i=0;i<nh;++i) {
            if(!atoms[i] || !is_expr(to_ast(atoms[i])) || !mk_c(c)->m().is_bool(to_expr(atoms[i])) || phases[i]>1 || indices[i]>=nt) {SET_ERROR_CODE(Z3_INVALID_ARG,nullptr);return;}
            if(!unique.emplace(to_expr(atoms[i]),phases[i],indices[i]).second)continue;
            p->atoms.push_back(to_expr(atoms[i]));p->phases.push_back(phases[i]);p->indices.push_back(indices[i]);
        }
        init_solver(c,s);
        to_solver(s)->m_solver->set_coverage(p);
        Z3_CATCH;
    }
    void Z3_API Z3_solver_clear_coverage_guidance(Z3_context c,Z3_solver s) {
        Z3_TRY;
        RESET_ERROR_CODE();
        if(to_solver(s)->m_solver)to_solver(s)->m_solver->set_coverage(nullptr);
        Z3_CATCH;
    }
    Z3_string Z3_API Z3_solver_get_coverage_guidance_stats(Z3_context c,Z3_solver s) {
        Z3_TRY;
        RESET_ERROR_CODE();
        auto p=to_solver(s)->m_solver?to_solver(s)->m_solver->m_coverage:nullptr;
        return mk_c(c)->mk_external_string(p?p->json():"{}");
        Z3_CATCH_RETURN("");
    }
