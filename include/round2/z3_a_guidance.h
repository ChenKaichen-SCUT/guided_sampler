#pragma once
#include "z3.h"
#ifdef __cplusplus
extern "C" {
#endif
// shared_index points to std::shared_ptr<a2::Index>; the library takes ownership
// of a shared reference, never of host stack storage. Index has no AST pointers.
void Z3_API Z3_solver_set_A_guidance(Z3_context,Z3_solver,void const* shared_index,
 unsigned query,unsigned version,unsigned mode,double exposure_remaining,double explicit_remaining,unsigned diagnostic);
Z3_string Z3_API Z3_solver_get_A_guidance_stats(Z3_context,Z3_solver);
void Z3_API Z3_solver_clear_A_guidance(Z3_context,Z3_solver);
#ifdef __cplusplus
}
#endif
