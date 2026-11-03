    std::string input_sha="synthetic_fixture";
    std::unique_ptr<refinement::NativeOutputSplit> split;
    std::unique_ptr<OriginalAst> fallback_ast;
    std::vector<z3::expr> real_hard;
    double native_started_wall=0,native_started_cpu=0;
    OriginalAst& native_ast(){return guidance?guidance->ast:*fallback_ast;}
    void native_begin(){native_started_wall=refinement::wall_now();native_started_cpu=refinement::cpu_now();}
    void native_end(){split->budget.native_wall+=refinement::wall_now()-native_started_wall;split->budget.native_cpu+=refinement::cpu_now()-native_started_cpu;}
    void state_trace(std::mt19937 const& mt,z3::model const& m_ls,std::string const& boundary){
        if(!std::getenv("REFINEMENT_STATE_TRACE"))return;
        std::ostringstream rng;rng<<mt;Json entries=Json::array();
        for(unsigned j=0;j<m_ls.size();++j){auto d=m_ls[j];entries.push_back({{"index",j},{"decl_id",d.id()},{"name",d.name().str()},{"value",d.is_const()?m_ls.get_const_interp(d).to_string():"function"}});}
        std::ofstream f(dir+"/native_state.jsonl",std::ios::app);f<<Json({{"boundary",boundary},{"query",query},{"rng",rng.str()},{"m_ls",entries},{"native_count",split->native.accepted_count},{"coverage_version",guidance?guidance->ast.version:0}}).dump()<<'\n';
        if(!f)throw std::runtime_error("native state trace failed");
    }
