#pragma once
#include "native_output_split.hpp"
#include "observation.hpp"
namespace refinement {
inline Op from_z3_kind(Z3_decl_kind k){switch(k){
case Z3_OP_ANUM:case Z3_OP_TRUE:case Z3_OP_FALSE:return Op::Constant;
case Z3_OP_UNINTERPRETED:return Op::Variable;
case Z3_OP_AND:return Op::And;case Z3_OP_OR:return Op::Or;case Z3_OP_NOT:return Op::Not;
case Z3_OP_IMPLIES:return Op::Implies;case Z3_OP_XOR:return Op::Xor;case Z3_OP_ITE:return Op::Ite;
case Z3_OP_EQ:return Op::Eq;case Z3_OP_DISTINCT:return Op::Distinct;
case Z3_OP_LE:return Op::Le;case Z3_OP_LT:return Op::Lt;case Z3_OP_GE:return Op::Ge;case Z3_OP_GT:return Op::Gt;
case Z3_OP_ADD:return Op::Add;case Z3_OP_MUL:return Op::Mul;case Z3_OP_SUB:return Op::Sub;case Z3_OP_UMINUS:return Op::Neg;
case Z3_OP_IDIV:return Op::Div;case Z3_OP_MOD:return Op::Mod;default:return Op::Unknown;}}
inline Ast copy_original_ast(guided::OriginalAst const& source,std::vector<z3::expr> const& variables,std::string const& input_sha,WorkBudget& b){Ast a;a.input_sha=input_sha;std::map<unsigned,unsigned> ids;
    for(unsigned i=0;i<variables.size();++i){b.check();a.variables.push_back({variables[i].decl().name().str(),variables[i].is_bool()});ids[variables[i].decl().id()]=i;}
    for(auto const& old:source.nodes){b.check();Node n;n.boolean=old.boolean;n.op=from_z3_kind(old.e.decl().decl_kind());n.children=old.children;
        if(n.op==Op::Constant){n.constant=old.e.is_numeral()?guided::numeral(old.e):Big(old.e.is_true());b.integer(n.constant);}
        if(n.op==Op::Variable){if(!ids.count(old.e.decl().id()))throw Unsupported("nonoriginal_variable_in_hard_condition");n.variable=ids.at(old.e.decl().id());}a.nodes.push_back(std::move(n));}
    a.finalize(b);return a;
}
inline ObservationTrace trace_from_native(guided::OriginalAst const& ast,guided::Evaluation const& ev){ObservationTrace t;t.values=ev.values;t.zero.resize(ast.nodes.size());t.one.resize(ast.nodes.size());for(unsigned i=0;i<ast.nodes.size();++i)if(ev.values[i]){t.one[i]=guided::low64(*ev.values[i])&ast.nodes[i].mask();t.zero[i]=~t.one[i]&ast.nodes[i].mask();}t.legal=t.values[0]&&*t.values[0]!=0;return t;}
inline Json budget_json(BudgetLedger const& b){return {{"preprocess_wall",b.preprocess_wall},{"preprocess_cpu",b.preprocess_cpu},{"event_wall",b.event_wall},{"event_cpu",b.event_cpu},{"log_wall",b.log_wall},{"log_cpu",b.log_cpu},{"overrun_wall",b.overrun_wall},{"overrun_cpu",b.overrun_cpu},{"native_wall",b.native_wall},{"native_cpu",b.native_cpu},{"optional_wall",b.optional_wall},{"optional_cpu",b.optional_cpu},{"mandatory_delivery_wall",b.mandatory_wall},{"mandatory_delivery_cpu",b.mandatory_cpu},{"available_wall",b.available_wall()},{"available_cpu",b.available_cpu()},{"absolute_limit",0.05*b.session},{"earned_wall",0.10*b.native_wall},{"earned_cpu",0.10*b.native_cpu},{"preprocess_attempted",b.preprocess_attempted},{"disabled",b.disabled}};}
}
