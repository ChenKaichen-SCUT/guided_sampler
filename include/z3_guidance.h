#pragma once
#include "z3.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Metadata only. mode: 0=passive diagnostics, 1=A, 2=B, 3=AB. Each hint supports exactly one
   window index; duplicate (atom, phase, target) entries are rejected. */
void Z3_API Z3_solver_set_coverage_guidance(Z3_context c, Z3_solver s,
    unsigned mode, unsigned epoch, unsigned version,
    unsigned nt, Z3_ast const predicates[], unsigned const target_ids[],
    unsigned nh, Z3_ast const atoms[], unsigned const phases[], unsigned const target_indices[]);
void Z3_API Z3_solver_clear_coverage_guidance(Z3_context c, Z3_solver s);
Z3_string Z3_API Z3_solver_get_coverage_guidance_stats(Z3_context c, Z3_solver s);
#ifdef __cplusplus
}
#endif
