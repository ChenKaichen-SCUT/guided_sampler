#pragma once
// Included inside a2. Conservative exact evaluation on an existing expression.
namespace r4 {
template<class View> std::optional<bool> evaluate_reference_phase(View const& v,typename View::Expr atom,QueryPreferences const& q,Work& w,std::string& reason) {
 using E=typename View::Expr;
 std::function<Big(E,unsigned)> eval=[&](E e,unsigned depth)->Big {
  w.check();if(depth>256)throw std::runtime_error("reference_evaluation_incomplete");
  auto op=v.op(e);
  if(op==Var){auto i=q.reference.find(v.identity(e));if(i==q.reference.end())throw std::runtime_error("missing_reference_value");return i->second;}
  if(op==Num)return v.number(e);if(op==True)return 1;if(op==False)return 0;
  if(op==Other)throw std::runtime_error("unsupported_reference_mapping");
  std::vector<Big> xs;for(unsigned i=0;i<v.size(e);++i)xs.push_back(eval(v.child(e,i),depth+1));
  Big r=0;
  switch(op){
  case Not:if(xs.size()!=1)throw std::runtime_error("unsupported_reference_mapping");return xs[0]==0?1:0;
  case Eq:case Le:case Lt:case Ge:case Gt:
   if(xs.size()!=2)throw std::runtime_error("unsupported_reference_mapping");
   return (op==Eq?xs[0]==xs[1]:op==Le?xs[0]<=xs[1]:op==Lt?xs[0]<xs[1]:op==Ge?xs[0]>=xs[1]:xs[0]>xs[1])?1:0;
  case And:r=1;for(auto const& x:xs)r=(r!=0&&x!=0)?1:0;return r;
  case Or:for(auto const& x:xs)r=(r!=0||x!=0)?1:0;return r;
  case Ite:if(xs.size()!=3)throw std::runtime_error("unsupported_reference_mapping");return xs[0]!=0?xs[1]:xs[2];
  case Add:for(auto const& x:xs)r+=x;break;
  case Sub:if(xs.empty())throw std::runtime_error("unsupported_reference_mapping");r=xs[0];for(unsigned i=1;i<xs.size();++i)r-=xs[i];break;
  case Neg:if(xs.size()!=1)throw std::runtime_error("unsupported_reference_mapping");r=-xs[0];break;
  case Mul:r=1;for(auto const& x:xs){r*=x;if(r!=0&&boost::multiprecision::msb(absn(r))>65536)throw std::runtime_error("reference_value_size_limit");}break;
  default:throw std::runtime_error("unsupported_reference_mapping");
  }
  if(r!=0&&boost::multiprecision::msb(absn(r))>65536)throw std::runtime_error("reference_value_size_limit");return r;
 };
 try{if(v.sort(atom)!='B')throw std::runtime_error("unsupported_reference_mapping");auto x=eval(atom,0);reason.clear();return x!=0;}
 catch(std::runtime_error const& e){reason=e.what();return std::nullopt;}
}
}
