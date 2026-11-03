#pragma once
#include "directions.hpp"
namespace refinement {
struct InfluenceGroup {DirectionBits directions{};uint64_t maximum_weight=0;};
struct ScoreIndex {
    std::vector<unsigned> node_group;std::vector<InfluenceGroup> groups;
    std::vector<uint64_t> initial_scores;uint64_t original_entries=0,group_entries=0;
};
struct ScoreState {
    Ast const* formula=nullptr;std::string history;uint64_t version=0;bool valid=false;
    std::vector<uint64_t> covered_snapshot,group_weight,direction_score;
};
inline ScoreIndex build_score_index(Ast const& ast,DirectionPool const& pool,WorkBudget& b){
    StageScope scope(b.trace,RepairStage::BuildScoreIndex);ScoreIndex idx;idx.node_group.resize(ast.nodes.size(),UINT_MAX);idx.initial_scores.resize(pool.directions.size());
    for(auto const& d:pool.directions){b.check();idx.original_entries+=d.affected.size();}
    std::map<DirectionBits,unsigned> groups;
    for(unsigned n=0;n<ast.nodes.size();++n){b.check();if(b.trace)b.trace->node(n);DirectionBits bits{};if(!pool.directions.empty())bits=pool.influence.node_directions.at(n);
        if(bits==DirectionBits{})continue;auto [it,inserted]=groups.emplace(bits,groups.size());if(inserted)idx.groups.push_back({bits,0});idx.node_group[n]=it->second;idx.groups[it->second].maximum_weight+=std::popcount(ast.nodes[n].mask());}
    for(auto const& group:idx.groups)for(unsigned w=0;w<4;++w){b.check();uint64_t bits=group.directions[w];while(bits){b.check();auto d=w*64+std::countr_zero(bits);idx.initial_scores.at(d)+=group.maximum_weight;++idx.group_entries;bits&=bits-1;}}
    if(b.trace)b.trace->score_index_bytes+=idx.node_group.capacity()*sizeof(unsigned)+idx.groups.capacity()*sizeof(InfluenceGroup)+idx.initial_scores.capacity()*sizeof(uint64_t);
    return idx;
}
inline ScoreState initial_score_state(Ast const& ast,ScoreIndex const& idx,WorkBudget& b){
    StageScope scope(b.trace,RepairStage::BuildScoreIndex);ScoreState s;s.formula=&ast;s.covered_snapshot.resize(ast.nodes.size());s.direction_score=idx.initial_scores;
    for(auto const& g:idx.groups){b.check();s.group_weight.push_back(g.maximum_weight);}b.check();s.valid=true;if(b.trace)b.trace->score_state_bytes+=(s.covered_snapshot.capacity()+s.group_weight.capacity()+s.direction_score.capacity())*sizeof(uint64_t);return s;
}
inline void sync_scores(Ast const& ast,ObservationHistory const& history,std::string const& identity,ScoreIndex const& idx,ScoreState& state,WorkBudget& b){
    if(history.zero.size()!=ast.nodes.size()||history.one.size()!=ast.nodes.size())throw std::runtime_error("score history universe mismatch");
    ScoreState next;std::vector<uint64_t> removed(idx.groups.size());bool compatible=state.valid&&state.formula==&ast&&(state.history==identity||(state.history.empty()&&state.version==0))&&history.version>=state.version;
    {StageScope stage(b.trace,RepairStage::ScoreSyncNodes);b.check();next=compatible?state:initial_score_state(ast,idx,b);next.formula=&ast;next.history=identity;next.version=history.version;
        bool decreased=false;
        for(unsigned n=0;n<ast.nodes.size();++n){b.check();if(b.trace){b.trace->node(n);++b.trace->rank_sync_nodes;}uint64_t cov=history.zero[n]&history.one[n]&ast.nodes[n].mask();uint64_t old=next.covered_snapshot[n];
            if(old&~cov)decreased=true;auto group=idx.node_group[n];if(group!=UINT_MAX)removed[group]+=std::popcount(cov&~old);
            if(b.trace)b.trace->changed_covered_bits+=std::popcount(cov^old);next.covered_snapshot[n]=cov;}
        if(decreased){ // A replacement history is a fresh state, never unsigned subtraction from stale weights.
            next.direction_score=idx.initial_scores;for(unsigned g=0;g<idx.groups.size();++g){b.check();next.group_weight[g]=idx.groups[g].maximum_weight;removed[g]=0;}
            for(unsigned n=0;n<ast.nodes.size();++n){b.check();if(idx.node_group[n]!=UINT_MAX)removed[idx.node_group[n]]+=std::popcount(next.covered_snapshot[n]);}
        }
    }
    {StageScope stage(b.trace,RepairStage::ScoreSyncGroups);b.check();for(unsigned g=0;g<idx.groups.size();++g){b.check();auto delta=removed[g];if(!delta)continue;if(b.trace)++b.trace->dirty_groups;
        if(delta>next.group_weight[g])throw std::runtime_error("nonmonotone score group");next.group_weight[g]-=delta;
        for(unsigned w=0;w<4;++w){b.check();uint64_t bits=idx.groups[g].directions[w];while(bits){b.check();auto d=w*64+std::countr_zero(bits);if(delta>next.direction_score.at(d))throw std::runtime_error("score underflow");next.direction_score[d]-=delta;if(b.trace)++b.trace->score_updates;bits&=bits-1;}}
    }}
    {StageScope stage(b.trace,RepairStage::ScorePublish);b.check();next.valid=true;std::swap(state,next);}
}
inline std::vector<unsigned> select_scores(std::vector<uint64_t> const& scores,uint64_t event,WorkBudget& b){
    std::vector<std::pair<uint64_t,unsigned>> ranked;for(unsigned d=0;d<scores.size();++d){b.check();ranked.emplace_back(scores[d],d);}
    std::sort(ranked.begin(),ranked.end(),[](auto a,auto c){return a.first!=c.first?a.first>c.first:a.second<c.second;});b.check();std::vector<unsigned> chosen;
    for(size_t i=0;i<std::min(size_t(8),ranked.size());++i)chosen.push_back(ranked[i].second);
    std::vector<unsigned> rest;for(unsigned d=0;d<scores.size();++d){b.check();if(std::find(chosen.begin(),chosen.end(),d)==chosen.end())rest.push_back(d);}
    for(size_t i=0;i<std::min(size_t(8),rest.size());++i)chosen.push_back(rest[(event+i)%rest.size()]);return chosen;
}
}
