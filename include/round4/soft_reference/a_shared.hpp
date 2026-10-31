#pragma once
// Pure owned data shared across the host and its pinned libz3 C++ ABI.
// No AST pointers, manager-local ids, solver handles or logical constraints.
#include <boost/multiprecision/cpp_int.hpp>
#include <map>
#include <vector>
#include <string>
#include <memory>
#include <chrono>
#include <stdexcept>
#include <atomic>
#include <algorithm>
#include <functional>
#include <optional>
#include <cstdlib>
#include <set>
namespace a2 {
using Big=boost::multiprecision::cpp_int;
using Clock=std::chrono::steady_clock;
inline double seconds(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
inline unsigned pop(uint64_t x){return __builtin_popcountll(x);}
inline std::string str(Big const& x){return x.convert_to<std::string>();}
inline Big absn(Big x){return x<0?-x:x;}
inline Big gcd(Big a,Big b){a=absn(a);b=absn(b);while(b!=0){Big t=a%b;a=b;b=t;}return a;}
enum Op {Var,Num,True,False,Not,Eq,Le,Lt,Ge,Gt,Add,Sub,Neg,Mul,And,Or,Ite,Other};
struct Work {
 unsigned steps=0,limit=16384; Clock::time_point deadline=Clock::now()+std::chrono::milliseconds(10);
 void check(){if(++steps>limit || ((steps&63)==0 && Clock::now()>=deadline))throw std::runtime_error("normalization_incomplete");}
};
#include "semantic_correspondence.hpp"
struct Norm {std::string key,exact,reason,kind,mapping_rule;bool negated=false,complete=false;};
struct Linear {
 std::map<std::string,Big> terms;Big constant=0;
 void add(Linear const& b,Big const& scale){constant+=b.constant*scale;for(auto const& kv:b.terms){terms[kv.first]+=kv.second*scale;if(terms[kv.first]==0)terms.erase(kv.first);}}
 void scale(Big const& f){constant*=f;for(auto& kv:terms)kv.second*=f;if(f==0)terms.clear();}
 std::string key() const {std::string s="C"+str(constant)+";";for(auto const& kv:terms)s+=std::to_string(kv.first.size())+":"+kv.first+"="+str(kv.second)+";";return s;}
 void primitive(){Big g=absn(constant);for(auto const& kv:terms)g=gcd(g,kv.second);if(g>1){constant/=g;for(auto& kv:terms)kv.second/=g;}}
};
// Adapter methods only READ expressions. Normal forms are strings/exact integers.
template<class View> Norm canonical(View const& v,typename View::Expr root,Work& w,bool allow_gate=r4::mapping_enabled()){
 using E=typename View::Expr;
 std::function<std::string(E,unsigned)> structural=[&](E e,unsigned depth)->std::string{
  w.check();if(depth>256)throw std::runtime_error("normalization_incomplete");
  auto op=v.op(e);if(op==Var)return v.identity(e);if(op==Num)return "N"+str(v.number(e))+";";
  if(op==Other)throw std::runtime_error("unsupported_normal_form");
  std::vector<std::string> children;for(unsigned i=0;i<v.size(e);++i)children.push_back(structural(v.child(e,i),depth+1));
  if(op==Eq)std::sort(children.begin(),children.end());
  std::string s=std::to_string(op)+v.sort(e)+"(";for(auto const& c:children)s+=std::to_string(c.size())+":"+c;return s+")";
 };
 std::function<Linear(E,unsigned)> lin=[&](E e,unsigned depth)->Linear{
  w.check();if(depth>256)throw std::runtime_error("normalization_incomplete");Linear r;auto op=v.op(e);
  if(op==Num){r.constant=v.number(e);return r;}
  if(op==Var){r.terms[v.identity(e)]=1;return r;}
  if(op==Add||op==Sub||op==Neg){for(unsigned i=0;i<v.size(e);++i){auto x=lin(v.child(e,i),depth+1);r.add(x,(op==Neg||(op==Sub&&i>0))?-1:1);}return r;}
  if(op==Mul){Big factor=1;bool nonconstant=false;for(unsigned i=0;i<v.size(e);++i){auto x=lin(v.child(e,i),depth+1);if(x.terms.empty())factor*=x.constant;else {if(nonconstant)throw std::runtime_error("unsupported_normal_form");r=x;nonconstant=true;}}if(!nonconstant)r.constant=1;r.scale(factor);return r;}
  // An unchanged integer subterm is a sound opaque basis; no domain inference.
  r.terms[structural(e,depth+1)]=1;return r;
 };
 Norm out;
 try {
  while(v.op(root)==Not){w.check();out.negated=!out.negated;root=v.child(root,0);}
  out.exact=structural(root,0);auto op=v.op(root);
  auto gate=allow_gate?r4::complementary_bounds(v,root,structural,w):std::nullopt;
  if(gate){auto l=lin(gate->term,0);l.constant-=gate->value;l.primitive();if(!l.terms.empty()&&l.terms.begin()->second<0)l.scale(-1);out.key="EQ:"+l.key();out.negated^=gate->negated;out.kind="verified_complementary_bounds";out.mapping_rule=gate->rule;}
  else if((op==Eq||op==Le||op==Lt||op==Ge||op==Gt)&&v.size(root)==2&&v.sort(v.child(root,0))=='I'){
   auto l=lin(v.child(root,0),0),r=lin(v.child(root,1),0);l.add(r,-1);
   if(op==Ge||op==Gt)l.scale(-1);
   if(op==Lt||op==Gt)++l.constant;
   if(op==Eq){l.primitive();if(!l.terms.empty()&&l.terms.begin()->second<0)l.scale(-1);out.key="EQ:"+l.key();}
   else {if(!l.terms.empty()&&l.terms.begin()->second<0){l.scale(-1);++l.constant;out.negated=!out.negated;}l.primitive();out.key="LE:"+l.key();}
   out.kind="exact_linear_equivalence";
  }else {out.key="EX:"+out.exact;out.kind="exact_structure";}
  out.complete=true;
 }catch(std::runtime_error const& ex){out.reason=ex.what();out.key.clear();out.complete=false;}
 return out;
}
#include "preference_types.hpp"
#include "reference_evaluation.hpp"
struct Rule {unsigned node;bool phase;uint64_t one,zero;uint64_t want_one=0,want_zero=0;};
struct OriginalCorrespondence {unsigned node;std::string fingerprint,exact;bool negated;};
struct Entry {std::vector<OriginalCorrespondence> originals;std::vector<Rule> rules;std::string original_exact;};
struct Index {
 std::shared_ptr<const r4::QueryPreferences> preferences;
 std::map<std::string,Entry> entries;std::vector<std::pair<uint64_t,uint64_t>> node_states;
 std::atomic<unsigned> active{0};unsigned version=0;
 uint64_t mappable_targets=0,single_sided=0;unsigned updates=0;
};
struct Support {unsigned node;uint64_t one=0,zero=0;};
#include "phase_evidence.hpp"
}
