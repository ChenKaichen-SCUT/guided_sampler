#pragma once
#include "a_guidance_bridge.hpp"
#include <random>
#include <sstream>
namespace guided {
using OriginalDeclarations=std::map<unsigned,z3::expr>;
inline std::string reference_digest(std::string const& value){uint64_t h=14695981039346656037ULL;for(unsigned char c:value){h^=c;h*=1099511628211ULL;}std::ostringstream o;o<<std::hex<<h;return o.str();}
struct InheritedReference {
 std::map<std::string,a2::Big> values;
 Json selected=Json::array(),draws=Json::array();std::string rng_before,rng_after;
};
struct QueryInputs {
 z3::expr_vector user_hard;InheritedReference reference;
 explicit QueryInputs(z3::context& c):user_hard(c){}
};
// Same eligibility, traversal, distribution and exactly one draw per eligible
// declaration as the frozen host. No equality expressions or missing-value fill.
inline InheritedReference collect_inherited_reference(z3::model const& model,OriginalDeclarations const& originals,std::mt19937& rng,double rate,std::uniform_real_distribution<double>& dist,bool have_sample){
 InheritedReference out;std::ostringstream before;before<<rng;out.rng_before=reference_digest(before.str());a2::HostView view;
 if(have_sample)for(unsigned j=0;j<model.size();++j){auto d=model[j];auto original=originals.find(d.id());
  if(original==originals.end()||!d.is_const()||d.decl_kind()==Z3_OP_TRUE||d.decl_kind()==Z3_OP_FALSE)continue;
  double draw=dist(rng);bool selected=draw<rate;out.draws.push_back({{"model_index",j},{"decl_id",d.id()},{"draw",draw},{"selected",selected}});if(!selected)continue;
  auto value=model.get_const_interp(d);bool defined=(original->second.is_int()&&value.is_numeral())||(original->second.is_bool()&&(value.is_true()||value.is_false()));auto key=view.identity(original->second);
  out.selected.push_back({{"model_index",j},{"decl_id",d.id()},{"name",d.name().str()},{"sort",original->second.get_sort().to_string()},{"identity",key},{"value",value.to_string()},{"defined",defined},{"origin","sampler_m_ls"}});
  if(defined)out.values.emplace(key,original->second.is_int()?a2::Big(Z3_get_numeral_string(value.ctx(),value)):a2::Big(value.is_true()));
 }
 std::ostringstream after;after<<rng;out.rng_after=reference_digest(after.str());return out;
}
}
