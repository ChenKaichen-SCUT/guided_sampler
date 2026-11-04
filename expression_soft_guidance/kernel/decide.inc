    // The preferred expression is an actual normal decision. Propagation,
    // arithmetic reasoning, conflict analysis, and unassignment remain native.
    if (auto* pref = expr_soft::for_manager(m); pref && pref->mapping_ok && pref->owner == this) {
        ++pref->decisions;
        if (pref->decisions <= pref->window) {
            // A conflict can undo earlier decisions. Revisit unassigned goals;
            // native propagation/learned clauses decide which goals must yield.
            pref->next = 0;
            while (pref->next < pref->working_goals.size()) {
                expr* goal = pref->working_goals.get(pref->next++);
                literal target = get_literal(goal);
                lbool current = get_assignment(target);
                if (current == l_true) { ++pref->already_true; continue; }
                if (current == l_false) { ++pref->already_false; continue; }
                ++m_stats.m_num_decisions;
                push_scope();
                mark_as_relevant(goal);
                assign(target, b_justification::mk_axiom(), true);
                ++pref->chosen;
                return true;
            }
        } else if (pref->next < pref->working_goals.size()) {
            ++pref->window_skips;
        }
    }
