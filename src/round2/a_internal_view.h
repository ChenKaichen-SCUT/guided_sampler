#pragma once
#include "util/a_shared.hpp"
#include "ast/arith_decl_plugin.h"
namespace a2 {
struct InternalView {
 using Expr=expr*;ast_manager& m;arith_util arith;
 explicit InternalView(ast_manager& m):m(m),arith(m){}
 Op op(Expr e)const {
  if(!is_app(e))return Other;auto a=to_app(e);auto k=a->get_decl_kind();auto f=a->get_family_id();
  if(f==null_family_id)return a->get_num_args()==0?Var:Other;
  if(f==basic_family_id)switch(k){case OP_TRUE:return True;case OP_FALSE:return False;case OP_NOT:return Not;case OP_EQ:return Eq;case OP_AND:return And;case OP_OR:return Or;case OP_ITE:return Ite;default:return Other;}
  if(f==arith.get_family_id())switch(k){case OP_NUM:return Num;case OP_LE:return Le;case OP_LT:return Lt;case OP_GE:return Ge;case OP_GT:return Gt;case OP_ADD:return Add;case OP_SUB:return Sub;case OP_UMINUS:return Neg;case OP_MUL:return Mul;default:return Other;}
  return Other;
 }
 unsigned size(Expr e)const{return to_app(e)->get_num_args();}Expr child(Expr e,unsigned i)const{return to_app(e)->get_arg(i);}
 char sort(Expr e)const{return arith.is_int(e)?'I':m.is_bool(e)?'B':'?';}
 Big number(Expr e)const{rational r;if(!arith.is_numeral(e,r)||!r.is_int())throw std::runtime_error("unsupported_normal_form");return Big(r.to_string());}
 std::string identity(Expr e)const{auto s=to_app(e)->get_decl()->get_name();std::string name=s.str();return std::string(to_app(e)->get_decl()->is_skolem()?"SKOLEM:":"")+std::string(1,sort(e))+(s.is_numerical()?"#":"$")+std::to_string(name.size())+":"+name;}
};
}
namespace a2 {
struct ContextCache {
 struct Track {unsigned var;expr* e;unsigned action;uint64_t token;bool active;};
 expr_ref_vector refs;std::map<expr*,Norm> cache;std::vector<Track> tracks;
 explicit ContextCache(ast_manager& m):refs(m){}
};
}
