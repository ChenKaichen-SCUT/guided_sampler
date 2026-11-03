#pragma once
#include "observations.hpp"
namespace refinement {
struct DependencyIndex {std::vector<std::vector<unsigned>> parents,variable_occurrences;};
struct ScratchMarks {
    std::vector<uint32_t> marks;uint32_t epoch=0;
    explicit ScratchMarks(size_t n):marks(n,0){}
    void next(WorkBudget& b){if(epoch==UINT32_MAX){if(b.trace)b.trace->scan(marks.size());for(auto& x:marks){b.check();x=0;}epoch=1;}else ++epoch;}
};
inline DependencyIndex build_reverse_index(Ast const& ast,WorkBudget& b){
    DependencyIndex idx;idx.parents.resize(ast.nodes.size());idx.variable_occurrences.resize(ast.variables.size());
    if(b.trace)b.trace->allocation(ast.nodes.size());
    for(unsigned i=0;i<ast.nodes.size();++i){b.check();if(b.trace)b.trace->node(i);auto const& n=ast.nodes[i];
        if(n.op==Op::Variable){idx.variable_occurrences.at(n.variable).push_back(i);if(b.trace)++b.trace->dependency_entries;}
        for(auto c:n.children){b.check();idx.parents[c].push_back(i);if(b.trace){b.trace->edges(1);++b.trace->dependency_entries;}}
    }return idx;
}
template<class Direction> inline std::vector<unsigned> collect_affected(DependencyIndex const& idx,Direction const& d,ScratchMarks& marks,WorkBudget& b){
    marks.next(b);std::vector<unsigned> todo,out;
    auto visit=[&](unsigned n){if(marks.marks[n]!=marks.epoch){marks.marks[n]=marks.epoch;todo.push_back(n);}};
    for(auto const& [v,s]:d){b.check();if(s!=0)for(auto n:idx.variable_occurrences.at(v))visit(n);}
    while(!todo.empty()){b.check();auto n=todo.back();todo.pop_back();out.push_back(n);if(b.trace)b.trace->node(n);for(auto p:idx.parents[n]){b.check();if(b.trace)b.trace->edges(1);visit(p);}}
    std::sort(out.begin(),out.end());b.check();return out;
}
inline bool depends_on_direction(unsigned node,std::vector<unsigned> const& affected){return std::binary_search(affected.begin(),affected.end(),node);}
using DirectionBits=std::array<uint64_t,4>;
struct InfluenceIndex {unsigned direction_count=0;std::vector<DirectionBits> node_directions;};
// Each node uses all syntactic children, including cancelled terms and unselected branches.
template<class Directions> inline InfluenceIndex build_direction_influence(Ast const& ast,Directions& dirs,WorkBudget& b){
    InfluenceIndex out;out.direction_count=dirs.size();if(dirs.size()>256)throw std::runtime_error("influence pool overflow");
    if(dirs.empty())return out;
    if(ast.nodes.size()>std::numeric_limits<size_t>::max()/sizeof(DirectionBits))throw std::length_error("influence allocation overflow");
    unsigned words=(dirs.size()+63)/64;out.node_directions.resize(ast.nodes.size());std::vector<DirectionBits> vars(ast.variables.size());
    if(b.trace){b.trace->allocation(ast.nodes.size());b.trace->influence_bytes+=(ast.nodes.size()+vars.size())*sizeof(DirectionBits);}
    for(auto const& d:dirs){b.check();for(auto const& [v,c]:d.values){b.check();if(c!=0)vars.at(v)[d.id/64]|=uint64_t(1)<<(d.id%64);}}
    for(auto n:ast.postorder){b.check();if(b.trace)b.trace->node(n);auto const& node=ast.nodes[n];auto& bits=out.node_directions[n];
        if(node.op==Op::Variable)bits=vars.at(node.variable);
        for(auto c:node.children){b.check();if(b.trace)b.trace->edges(1);for(unsigned w=0;w<words;++w){b.check();bits[w]|=out.node_directions[c][w];if(b.trace)++b.trace->influence_ors;}}
        if(b.trace)b.trace->influence_words+=words;
    }
    for(unsigned n=0;n<out.node_directions.size();++n){b.check();for(unsigned w=0;w<words;++w){b.check();uint64_t bits=out.node_directions[n][w];while(bits){b.check();auto k=std::countr_zero(bits);dirs.at(w*64+k).affected.push_back(n);if(b.trace)++b.trace->affected_entries;bits&=bits-1;}}}
    return out;
}
// A hard formula and a diagnostic combination have their own node space, never a borrowed pool ID.
template<class Direction> inline std::vector<unsigned> single_direction_affected(Ast const& ast,Direction const& d,WorkBudget& b){
    std::vector<unsigned char> affected(ast.nodes.size());if(b.trace)b.trace->allocation(ast.nodes.size());
    for(auto n:ast.postorder){b.check();auto const& node=ast.nodes[n];if(node.op==Op::Variable){auto it=d.find(node.variable);affected[n]=it!=d.end()&&it->second!=0;}
        for(auto c:node.children){b.check();affected[n]|=affected[c];}}
    std::vector<unsigned> out;for(unsigned n=0;n<affected.size();++n){b.check();if(affected[n])out.push_back(n);}return out;
}
}
