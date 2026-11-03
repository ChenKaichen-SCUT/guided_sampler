#pragma once
#include "observations.hpp"
namespace refinement {
struct DependencyIndex {std::vector<std::vector<unsigned>> parents,variable_occurrences;};
struct ScratchMarks {
    std::vector<uint32_t> marks;uint32_t epoch=0;
    explicit ScratchMarks(size_t n):marks(n,0){}
    void next(WorkBudget& b){if(++epoch==0){if(b.trace)b.trace->scan(marks.size());for(auto& x:marks){b.check();x=0;}epoch=1;}}
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
}
