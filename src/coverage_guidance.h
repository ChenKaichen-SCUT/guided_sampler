#pragma once
#include "ast/ast.h"
#include <memory>
#include <vector>
#include <set>
#include <unordered_set>
#include <sstream>
#include <chrono>

/* Expressions own references, literals are always rebound in the live context.
   The shared record belongs to one solver and one external check epoch. */
struct coverage_guidance {
    expr_ref_vector predicates, atoms;
    std::vector<unsigned> ids, phases, indices;
    unsigned mode, epoch, version, ordinal=0, a_used=0, b_used=0;
    unsigned internalized=0, relevant=0, live=0, propagated=0, special=0;
    unsigned unsupported=0, backend=0, fallback=0, cap=0, deferred=0;
    unsigned changed=0, same=0, native_targets=0;
    double prepare_seconds=0, broker_seconds=0;
    std::set<unsigned> attempted;
    std::vector<unsigned> eligible, a_bound;
    std::vector<std::string> events;
    coverage_guidance(ast_manager& m,unsigned md,unsigned ep,unsigned v):
        predicates(m),atoms(m),mode(md),epoch(ep),version(v) {}
    std::string json() const {
        std::ostringstream o;
        o << "{\"epoch\":" << epoch << ",\"coverage_version\":" << version
          << ",\"backend\":" << backend << ",\"unsupported\":" << unsupported
          << ",\"fallback\":" << fallback << ",\"ordinary\":" << ordinal
          << ",\"a_used\":" << a_used << ",\"b_used\":" << b_used
          << ",\"a_live\":" << live << ",\"b_internalized\":" << internalized
          << ",\"b_relevant\":" << relevant << ",\"propagated\":" << propagated
          << ",\"special\":" << special << ",\"cap\":" << cap
          << ",\"deferred\":" << deferred << ",\"a_changed\":" << changed
          << ",\"a_same\":" << same << ",\"native_registered_targets\":" << native_targets
          << ",\"prepare_seconds\":" << prepare_seconds
          << ",\"broker_seconds\":" << broker_seconds << ",\"events\":[";
        for(unsigned i=0;i<events.size();++i){if(i)o<<',';o<<events[i];}
        return o.str()+"]}";
    }
};
