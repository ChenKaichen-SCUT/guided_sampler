#pragma once
#include "history.hpp"
#include "numeric_cache.hpp"
#include "dependency_index.hpp"
#include "search_strategy.hpp"
namespace refinement {
struct Affine {bool supported=false;Big constant=0;std::map<unsigned,Big> coefficients;};
inline void clean(Affine& a){for(auto it=a.coefficients.begin();it!=a.coefficients.end();)if(it->second==0)it=a.coefficients.erase(it);else ++it;}
inline void add_scaled(Affine& dst,Affine const& src,Big const& scale,WorkBudget& b){b.integer(scale);dst.constant=checked_add(dst.constant,checked_mul(src.constant,scale,b),b);b.integer(dst.constant);for(auto const& [i,c]:src.coefficients){b.check();dst.coefficients[i]=checked_add(dst.coefficients[i],checked_mul(c,scale,b),b);b.integer(dst.coefficients[i]);}clean(dst);}
struct AffineIR {Ast ast;std::vector<Affine> terms;std::vector<std::vector<unsigned>> dependencies;DependencyIndex reverse;RepairMode mode=RepairMode::Legacy;SearchStrategies strategies;};
inline AffineIR compile_affine_ir(Ast ast,WorkBudget& b,SearchStrategies strategies){
    auto mode=strategies.numeric;
    AffineIR ir;ir.ast=std::move(ast);ir.terms.resize(ir.ast.nodes.size());ir.mode=mode;ir.strategies=strategies;
    {StageScope stage(b.trace,RepairStage::DependencyIndex);
    if(strategies.influence==InfluenceStrategy::ReverseParents)ir.reverse=build_reverse_index(ir.ast,b);else if(strategies.influence==InfluenceStrategy::TransitiveVariables){ir.dependencies.resize(ir.ast.nodes.size());
    for(unsigned i:ir.ast.postorder){b.check();if(b.trace)b.trace->node(i);auto const& n=ir.ast.nodes[i];auto& deps=ir.dependencies[i];std::set<unsigned> ds;
        if(n.op==Op::Variable)ds.insert(n.variable);for(auto c:n.children){b.check();if(b.trace)b.trace->edges(1);ds.insert(ir.dependencies[c].begin(),ir.dependencies[c].end());}deps.assign(ds.begin(),ds.end());if(b.trace)b.trace->dependency_entries+=deps.size();}}}
    StageScope terms(b.trace,RepairStage::CompileTerms);
    for(unsigned i:ir.ast.postorder){b.check();if(b.trace)b.trace->node(i);auto const& n=ir.ast.nodes[i];
        if(n.boolean)continue;auto& a=ir.terms[i];
        if(n.op==Op::Constant){a.supported=true;a.constant=n.constant;b.integer(a.constant);}
        else if(n.op==Op::Variable){a.supported=true;a.coefficients[n.variable]=1;}
        else if(n.op==Op::Add||n.op==Op::Sub||n.op==Op::Neg){a.supported=true;for(unsigned k=0;k<n.children.size();++k){auto const& t=ir.terms[n.children[k]];if(!t.supported){a.supported=false;break;}add_scaled(a,t,(n.op==Op::Neg||(n.op==Op::Sub&&k>0))?Big(-1):Big(1),b);}}
        else if(n.op==Op::Mul){Big factor=1;int variable_term=-1;a.supported=true;for(auto c:n.children){b.check();auto const& t=ir.terms[c];if(!t.supported){a.supported=false;break;}if(t.coefficients.empty()){factor=checked_mul(factor,t.constant,b);b.integer(factor);}else if(variable_term<0)variable_term=c;else{a.supported=false;break;}}if(a.supported){if(variable_term<0)a.constant=factor;else add_scaled(a,ir.terms[variable_term],factor,b);}}
        if(b.trace)b.trace->coefficient_entries+=a.coefficients.size();
    }return ir;
}
inline AffineIR compile_affine_ir(Ast ast,WorkBudget& b,RepairMode mode=RepairMode::Legacy){return compile_affine_ir(std::move(ast),b,historical_strategies(mode));}
struct EqualitySystem {std::vector<Affine> rows;std::vector<unsigned> nodes;};
inline EqualitySystem collect_mandatory_equalities(AffineIR const& ir,WorkBudget& b){StageScope stage(b.trace,RepairStage::CollectEqualities);EqualitySystem eq;std::vector<unsigned> todo{0};std::set<unsigned> seen;
    while(!todo.empty()){b.check();auto i=todo.back();todo.pop_back();if(!seen.insert(i).second)continue;auto const& n=ir.ast.nodes[i];if(n.op==Op::And){for(auto it=n.children.rbegin();it!=n.children.rend();++it)todo.push_back(*it);continue;}
        if(n.op!=Op::Eq||n.children.size()<2||ir.ast.nodes[n.children[0]].boolean)continue;
        bool supported=true;for(auto c:n.children)if(!ir.terms[c].supported)supported=false;if(!supported)continue;
        for(unsigned k=1;k<n.children.size();++k){Affine row;row.supported=true;add_scaled(row,ir.terms[n.children[0]],1,b);add_scaled(row,ir.terms[n.children[k]],-1,b);eq.rows.push_back(std::move(row));eq.nodes.push_back(i);}
    }return eq;
}
struct LineTerm{Big constant=0,slope=0;};
using IntegerVector=std::map<unsigned,Big>;
inline bool depends_on(std::vector<unsigned> const& deps,IntegerVector const& d){for(auto i:deps){auto it=d.find(i);if(it!=d.end()&&it->second!=0)return true;}return false;}
inline LineTerm affine_on_line(AffineIR const& ir,unsigned node,Assignment const& m,IntegerVector const& d,WorkBudget& b){
    StageScope line_stage(b.trace,RepairStage::LineTerms);if(b.trace)b.trace->node(node);auto const& a=ir.terms[node];if(!a.supported){bool varies=false;if(ir.strategies.influence==InfluenceStrategy::TransitiveVariables)varies=depends_on(ir.dependencies.at(node),d);else{auto affected=single_direction_affected(ir.ast,d,b);varies=depends_on_direction(node,affected);}if(varies)throw Unsupported("unsupported_on_direction");StageScope numeric(b.trace,RepairStage::NumericValues);auto ev=evaluate(ir.ast,m,b,false,node);return {*ev.values[node],0};}
    LineTerm out{a.constant,0};for(auto const& [i,c]:a.coefficients){b.check();out.constant=checked_add(out.constant,checked_mul(c,m.at(i),b),b);auto it=d.find(i);if(it!=d.end())out.slope=checked_add(out.slope,checked_mul(c,it->second,b),b);b.integer(out.constant);b.integer(out.slope);}return out;
}
// Per-anchor constants deliberately follow the coefficient dot-product order.
struct AnchorValues {
    NumericEvalCache numeric;std::vector<std::optional<Big>> constants;
    AnchorValues(AffineIR const& ir,Assignment const& m,uint64_t event,WorkBudget& b):numeric(ir.ast,m,event,b){
        StageScope stage(b.trace,RepairStage::LineTerms);b.check();constants.resize(ir.ast.nodes.size());if(b.trace){b.trace->allocation(constants.size());b.trace->numeric_cache_bytes+=constants.capacity()*sizeof(constants[0]);}b.check();
    }
};
class LineValues {
    AffineIR const& ir;Assignment const& anchor;IntegerVector const direction;AnchorValues& cache;std::vector<unsigned> affected;
    std::map<unsigned,LineTerm> lines;
public:
    LineValues(AffineIR const& a,Assignment const& m,IntegerVector const& d,AnchorValues& c,std::vector<unsigned> const& affected_nodes):ir(a),anchor(m),direction(d),cache(c),affected(affected_nodes){}
    LineTerm value(unsigned node,WorkBudget& b){
        StageScope stage(b.trace,RepairStage::LineTerms);b.check();if(b.trace)b.trace->node(node);auto found=lines.find(node);if(b.trace)b.trace->hit(found!=lines.end());if(found!=lines.end())return found->second;
        auto const& a=ir.terms[node];LineTerm out{a.constant,0};
        if(!a.supported){bool varies=ir.strategies.influence!=InfluenceStrategy::TransitiveVariables?depends_on_direction(node,affected):depends_on(ir.dependencies.at(node),direction);if(varies)throw Unsupported("unsupported_on_direction");out={cache.numeric.value(node,b),0};}
        else{
            bool known=cache.constants[node].has_value();if(known)out.constant=*cache.constants[node];
            for(auto const& [i,c]:a.coefficients){b.check();if(!known)out.constant=checked_add(out.constant,checked_mul(c,anchor.at(i),b),b);auto it=direction.find(i);if(it!=direction.end())out.slope=checked_add(out.slope,checked_mul(c,it->second,b),b);b.integer(out.constant);b.integer(out.slope);}
            if(!known)cache.constants[node]=out.constant;
        }
        lines.emplace(node,out);return out;
    }
};
}
