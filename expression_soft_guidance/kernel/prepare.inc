            if (auto* pref = expr_soft::for_manager(m); pref && pref->mapping_ok) {
                if (!pref->owner) pref->owner = this;
                if (pref->owner == this) {
                    for (expr* goal : pref->working_goals) {
                        internalize(goal, false);
                        mark_as_relevant(goal);
                        ++pref->prepared;
                    }
                }
            }
