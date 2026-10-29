// Included in smt_context.cpp inside namespace smt.
void context::prepare_coverage_targets() {
    if (!m_coverage || inconsistent()) return;
    auto start = std::chrono::steady_clock::now();
    auto& g=*m_coverage;
    g.backend=2;
    g.eligible.clear(); g.a_bound.clear();
    std::set<unsigned> reserved;
    // AB reserves only targets with a currently internalized original atom.
    // Propagated atoms still reserve their targets; they are not flipped by B.
    for(unsigned i=0;i<g.atoms.size();++i) {
        if(lit_internalized(g.atoms.get(i))) {
            g.a_bound.push_back(i); ++g.live;
            if(g.mode==3) reserved.insert(g.indices[i]);
        }
    }
    unsigned created=0;
    if(g.mode & 2) for(unsigned i=0;i<g.predicates.size();++i) {
        if(!g.predicates.get(i) || reserved.count(i)) continue;
        expr* e=g.predicates.get(i);
        bool registered=false;
        for(auto* old:m_coverage_registry) if(old==e){registered=true;break;}
        if(!registered && m_coverage_registry.size()>=2048){++g.cap;continue;}
        if(!registered && created>=2){++g.deferred;continue;}
        internalize(e, false); // definitional Tseitin proxy, NEVER assert e
        ++g.internalized;
        expr* proxy=bool_var2expr(get_literal(e).var());
        if(m_coverage_proxy_set.insert(proxy).second)m_coverage_proxies.push_back(proxy);
        mark_as_relevant(e);
        ++g.relevant;
        if(!registered){m_coverage_registry.push_back(e);++created;}
        g.eligible.push_back(i);
    }
    g.prepare_seconds += std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
}

bool context::coverage_decide(bool_var& var,bool& is_pos,bool ordinary) {
    if(!m_coverage) return false;
    auto& g=*m_coverage;
    if(!ordinary || m_user_propagator){++g.special;return false;}
    auto start=std::chrono::steady_clock::now();
    struct elapsed {double& out;std::chrono::steady_clock::time_point t;
        ~elapsed(){out+=std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();}
    } timer{g.broker_seconds,start};
    bool_var native=var; bool native_phase=is_pos;
    ++g.ordinal;
    if(var!=null_bool_var && m_coverage_proxy_set.count(bool_var2expr(var)))++g.native_targets;
    if(g.ordinal>64) return false;
    char source='N'; std::set<unsigned> supports;
    unsigned alim=g.mode==3?2:4, blim=g.mode==3?2:4;
    if((g.mode&1) && g.a_used<alim && var!=null_bool_var && get_assignment(var)==l_undef) {
        std::set<unsigned> pos,neg;
        for(auto i:g.a_bound) {
            if(g.attempted.count(g.indices[i]) || !lit_internalized(g.atoms.get(i)))continue;
            literal l=get_literal(g.atoms.get(i));
            if(l.var()!=var)continue;
            bool phase=bool(g.phases[i]) != l.sign();
            (phase?pos:neg).insert(g.indices[i]);
        }
        if(pos.size()!=neg.size()) {
            is_pos=pos.size()>neg.size();supports=is_pos?pos:neg;
            source='A';++g.a_used;
            if(is_pos==native_phase)++g.same;else ++g.changed;
        }
    }
    if(source=='N' && (g.mode&2) && g.b_used<blim) {
        for(auto i:g.eligible) {
            if(g.attempted.count(i) || !lit_internalized(g.predicates.get(i)))continue;
            literal l=get_literal(g.predicates.get(i));
            if(get_assignment(l)!=l_undef){++g.propagated;continue;}
            var=l.var();is_pos=!l.sign();supports.insert(i);source='B';++g.b_used;break;
        }
    }
    if(source=='N')return false;
    std::ostringstream o;
    o<<"{\"source\":\""<<source<<"\",\"ordinary\":"<<g.ordinal
      <<",\"level\":"<<m_scope_lvl<<",\"native_var\":"<<native
      <<",\"native_phase\":"<<native_phase<<",\"actual_var\":"<<var
      <<",\"actual_phase\":"<<is_pos<<",\"targets\":[";
    bool comma=false;
    for(auto i:supports){g.attempted.insert(i);if(comma)o<<',';comma=true;o<<g.ids[i];}
    o<<"]}";g.events.push_back(o.str());
    return var!=native;
}
