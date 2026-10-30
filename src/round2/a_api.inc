    void Z3_API Z3_solver_set_A_guidance(Z3_context c,Z3_solver s,void const* shared_index,
        unsigned query,unsigned version,unsigned mode,double exposure,double explicit_cost,unsigned diagnostic) {
        Z3_TRY;
        RESET_ERROR_CODE();
        if(!shared_index||mode<1||mode>2||exposure<0||explicit_cost<0){SET_ERROR_CODE(Z3_INVALID_ARG,nullptr);return;}
        auto index=*static_cast<std::shared_ptr<a2::Index> const*>(shared_index);
        if(!index||index->version!=version||index->active){SET_ERROR_CODE(Z3_INVALID_ARG,nullptr);return;}
        auto run=std::make_shared<a2::Run>(index,query,version,mode,exposure,explicit_cost,diagnostic);
        init_solver(c,s);to_solver(s)->m_solver->set_A_guidance(run);
        Z3_CATCH;
    }
    Z3_string Z3_API Z3_solver_get_A_guidance_stats(Z3_context c,Z3_solver s) {
        Z3_TRY;RESET_ERROR_CODE();
        auto r=to_solver(s)->m_solver?to_solver(s)->m_solver->m_A:nullptr;
        return mk_c(c)->mk_external_string(r?r->json().dump():"{}");
        Z3_CATCH_RETURN("");
    }
    void Z3_API Z3_solver_clear_A_guidance(Z3_context c,Z3_solver s) {
        Z3_TRY;RESET_ERROR_CODE();
        if(to_solver(s)->m_solver){auto r=to_solver(s)->m_solver->m_A;if(r)r->close();to_solver(s)->m_solver->set_A_guidance(nullptr);}
        Z3_CATCH;
    }
