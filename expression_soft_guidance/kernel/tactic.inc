        // Carry preferences through the SAME model-conversion substitutions as
        // the original formula. Never decide an eliminated, unrelated variable.
        auto* preference = expr_soft::for_manager(m);
        if (preference) {
            preference->owner = nullptr;
            preference->working_goals.reset();
            preference->mapping_ok = true;
            for (expr* original : preference->goals) {
                expr_ref rewritten(original, m);
                if (in->mc() && !in->mc()->expr_soft_rewrite(rewritten)) {
                    preference->mapping_ok = false;
                    ++preference->mapping_failures;
                    break;
                }
                preference->working_goals.push_back(rewritten);
                ++preference->mapped;
            }
        }
