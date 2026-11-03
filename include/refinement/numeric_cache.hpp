#pragma once
#include "observations.hpp"
namespace refinement {
struct AnchorKey {Ast const* formula;std::string input_sha;uint64_t native_event;std::string complete_assignment;};
// Own the complete anchor. No reachability or observation state lives here.
class NumericEvalCache {
    Ast const& ast;Assignment assignment;AnchorKey key;
    std::vector<std::optional<Big>> values;
public:
    NumericEvalCache(Ast const& a,Assignment const& m,uint64_t event,WorkBudget& b):ast(a) {
        StageScope stage(b.trace,RepairStage::NumericValues);b.check();assignment=m;key={&a,a.input_sha,event,assignment_key(m)};
        if(m.size()!=a.variables.size())throw std::runtime_error("incomplete cache anchor");
        values.resize(a.nodes.size());if(b.trace){b.trace->allocation(a.nodes.size());b.trace->numeric_cache_bytes+=values.capacity()*sizeof(values[0]);}b.check();
    }
    NumericEvalCache(Ast&&,Assignment const&,uint64_t,WorkBudget&)=delete;
    bool matches(Ast const& a,Assignment const& m,uint64_t event)const{return key.formula==&a&&key.input_sha==a.input_sha&&key.native_event==event&&key.complete_assignment==assignment_key(m);}
    bool ready(unsigned n)const{return values.at(n).has_value();}
    Big const& value(unsigned root,WorkBudget& budget){
        StageScope stage(budget.trace,RepairStage::NumericValues);budget.check();if(budget.trace)budget.trace->hit(ready(root));
    struct Frame{unsigned id;size_t child;};std::vector<Frame> stack{{root,0}};
    while(!stack.empty()){
        budget.check();auto& f=stack.back();auto const& n=ast.nodes[f.id];if(budget.trace)budget.trace->node(f.id);if(values[f.id]){stack.pop_back();continue;}
        if(n.op==Op::Constant||n.op==Op::Variable){Big v=n.op==Op::Constant?n.constant:assignment.at(n.variable);if(n.boolean&&v!=0&&v!=1)throw std::runtime_error("invalid Boolean assignment");budget.integer(v);values[f.id]=v;stack.pop_back();continue;}
        auto value=[&](unsigned k)->Big const&{return *values[n.children.at(k)];};
        if(n.op==Op::Ite){unsigned cond=n.children.at(0);if(!values[cond]){stack.push_back({cond,0});continue;}unsigned child=n.children.at(value(0)!=0?1:2);if(!values[child]){stack.push_back({child,0});continue;}values[f.id]=*values[child];stack.pop_back();continue;}
        if(f.child&&(n.op==Op::And||n.op==Op::Or)){bool v=value(f.child-1)!=0;if((n.op==Op::And&&!v)||(n.op==Op::Or&&v)){values[f.id]=v;stack.pop_back();continue;}}
        if(f.child<n.children.size()){unsigned child=n.children[f.child++];if(!values[child])stack.push_back({child,0});continue;}
        Big result=0;switch(n.op){
        case Op::And:result=1;break;case Op::Or:result=0;break;case Op::Not:result=value(0)==0;break;
        case Op::Implies:result=value(0)==0||value(1)!=0;break;
        case Op::Xor:for(unsigned k=0;k<n.children.size();++k)result=Big((result!=0)!=(value(k)!=0));break;
        case Op::Eq:result=1;for(unsigned k=1;k<n.children.size();++k)if(value(k)!=value(0))result=0;break;
        case Op::Distinct:result=1;for(unsigned k=0;k<n.children.size();++k)for(unsigned l=k+1;l<n.children.size();++l){budget.check();if(value(k)==value(l))result=0;}break;
        case Op::Le:case Op::Lt:case Op::Ge:case Op::Gt:result=1;for(unsigned k=1;k<n.children.size();++k){bool ok=n.op==Op::Le?value(k-1)<=value(k):n.op==Op::Lt?value(k-1)<value(k):n.op==Op::Ge?value(k-1)>=value(k):value(k-1)>value(k);if(!ok)result=0;}break;
        case Op::Add:for(unsigned k=0;k<n.children.size();++k){budget.check();result+=value(k);budget.integer(result);}break;
        case Op::Mul:result=1;for(unsigned k=0;k<n.children.size();++k){budget.check();result*=value(k);budget.integer(result);}break;
        case Op::Sub:result=value(0);for(unsigned k=1;k<n.children.size();++k){budget.check();result-=value(k);budget.integer(result);}break;
        case Op::Neg:result=-value(0);break;
        case Op::Div:if(value(1)==0)throw Unsupported("integer_division_by_zero");result=value(1)>0?floor_div(value(0),value(1)):Big(-floor_div(value(0),-value(1)));break;
        case Op::Mod:if(value(1)==0)throw Unsupported("integer_modulo_by_zero");result=floor_mod(value(0),abs_big(value(1)));break;
        default:throw Unsupported("numeric_evaluation_unsupported");}
        budget.integer(result);values[f.id]=result;stack.pop_back();
    }
        return *values.at(root);
    }
};
inline Big const& evaluate_value_only(unsigned n,NumericEvalCache& cache,WorkBudget& b){return cache.value(n,b);}
}
