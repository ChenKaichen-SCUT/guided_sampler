#pragma once
#include <z3++.h>
#include <cstdint>
#ifdef ESG_NO_KERNEL
inline void Z3_expr_soft_begin(Z3_context,unsigned,Z3_ast const*,unsigned,Z3_ast const*,unsigned,unsigned=0,Z3_ast const* =nullptr){throw std::runtime_error("baseline kernel has no guidance API");}
inline void Z3_expr_soft_stats(uint64_t*){}
inline void Z3_expr_soft_end(){}
inline void Z3_expr_ccss_begin(double ms){if(ms>0)throw std::runtime_error("baseline has no CCSS budget API");}
inline void Z3_expr_ccss_end(double* out){for(unsigned i=0;i<8;++i)out[i]=0;}
inline unsigned Z3_expr_exchange(Z3_context,unsigned,unsigned,char const*const*,char const*const*){return 0;}
inline char const* Z3_expr_exchange_value(Z3_context,char const*){return nullptr;}
#else
extern "C" {
void Z3_expr_soft_begin(Z3_context,unsigned,Z3_ast const*,unsigned,Z3_ast const*,unsigned,unsigned=0,Z3_ast const* =nullptr);
void Z3_expr_soft_stats(uint64_t*);
void Z3_expr_soft_end();
void Z3_expr_ccss_begin(double);
void Z3_expr_ccss_end(double*);
unsigned Z3_expr_exchange(Z3_context,unsigned,unsigned,char const*const*,char const*const*);
char const* Z3_expr_exchange_value(Z3_context,char const*);
}
#endif
