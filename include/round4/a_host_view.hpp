#pragma once
#include "a_shared.hpp"
#include "declaration_identity.hpp"
#include <z3++.h>
namespace a2 {
struct HostView {
 using Expr=z3::expr;
 Op op(Expr const& e) const {
  switch(e.decl().decl_kind()){
  case Z3_OP_UNINTERPRETED:return e.is_const()?Var:Other;
  case Z3_OP_ANUM:return Num;case Z3_OP_TRUE:return True;case Z3_OP_FALSE:return False;
  case Z3_OP_NOT:return Not;case Z3_OP_EQ:return Eq;case Z3_OP_LE:return Le;case Z3_OP_LT:return Lt;case Z3_OP_GE:return Ge;case Z3_OP_GT:return Gt;
  case Z3_OP_ADD:return Add;case Z3_OP_SUB:return Sub;case Z3_OP_UMINUS:return Neg;case Z3_OP_MUL:return Mul;
  case Z3_OP_AND:return And;case Z3_OP_OR:return Or;case Z3_OP_ITE:return Ite;default:return Other;}
 }
 unsigned size(Expr const& e)const{return e.num_args();}Expr child(Expr const& e,unsigned i)const{return e.arg(i);}
 char sort(Expr const& e)const{return e.is_int()?'I':e.is_bool()?'B':'?';}
 Big number(Expr const& e)const{return Big(Z3_get_numeral_string(e.ctx(),e));}
 std::string identity(Expr const& e)const{auto s=e.decl().name();auto name=s.str();return r4::declaration_identity(sort(e),s.kind()==Z3_INT_SYMBOL,name,false);}
};
}
