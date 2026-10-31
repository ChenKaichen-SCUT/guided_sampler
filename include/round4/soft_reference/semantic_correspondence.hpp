#pragma once
// Included inside namespace a2 after the pure Op/Big definitions.
namespace r4 {
inline bool mapping_enabled(){return std::getenv("GUIDED_R4_MAPPING_OFF")==nullptr;}
inline std::string fingerprint(std::string const& s){uint64_t h=1469598103934665603ull;for(unsigned char c:s){h^=c;h*=1099511628211ull;}return std::to_string(h);}
template<class E> struct GateMatch {E term;Big value;bool negated;std::string rule;};
template<class View,class Structural> std::optional<GateMatch<typename View::Expr>> complementary_bounds(View const& v,typename View::Expr e,Structural const& structural,Work& w){
 using E=typename View::Expr;auto op=v.op(e);if((op!=And&&op!=Or)||v.size(e)!=2)return std::nullopt;
 auto a=v.child(e,0),b=v.child(e,1);bool negated=op==Or;
 if(negated){if(v.op(a)!=Not||v.op(b)!=Not)return std::nullopt;a=v.child(a,0);b=v.child(b,0);}
 struct Bound {E term;Big c;bool upper;};
 auto bound=[&](E x)->std::optional<Bound>{w.check();auto k=v.op(x);if((k!=Le&&k!=Ge)||v.size(x)!=2)return std::nullopt;auto l=v.child(x,0),r=v.child(x,1);if(v.sort(l)!='I'||v.sort(r)!='I')return std::nullopt;
  if(v.op(r)==Num)return Bound{l,v.number(r),k==Le};
  if(v.op(l)==Num)return Bound{r,v.number(l),k==Ge};
  return std::nullopt;
 };
 auto x=bound(a),y=bound(b);if(!x||!y||x->upper==y->upper||x->c!=y->c||structural(x->term,0)!=structural(y->term,0))return std::nullopt;
 return GateMatch<E>{x->term,x->c,negated,negated?"negated_closed_bounds_to_disequality":"complementary_closed_bounds_to_equality"};
}
}
