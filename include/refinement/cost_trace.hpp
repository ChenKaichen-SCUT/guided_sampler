#pragma once
#include <array>
#include <chrono>
#include <ctime>
#include <exception>
#include <cstdint>
#include <nlohmann/json.hpp>
namespace refinement {
enum class RepairMode {Legacy,ValueCache,Shared};
inline RepairMode repair_mode(std::string const& name){if(name=="Legacy")return RepairMode::Legacy;if(name=="ValueCache")return RepairMode::ValueCache;if(name=="Shared")return RepairMode::Shared;throw std::runtime_error("invalid repair mode");}
inline char const* repair_name(RepairMode m){return m==RepairMode::Legacy?"Legacy":m==RepairMode::ValueCache?"ValueCache":"Shared";}
enum class RepairStage:unsigned {ParseInput,CopyAst,CompileTerms,DependencyIndex,CollectEqualities,Components,Elimination,VerifyDirections,BuildAffected,Metadata,Protect,ScoreBase,RankDirections,NumericValues,LineTerms,FormulaDomain,TargetSelection,ModularHits,CandidateBuild,ValidateFormula,OfficialObserve,PreserveAndScore,SerializeResult,MandatoryDelivery,BuildScoreIndex,ScoreSyncNodes,ScoreSyncGroups,ScorePublish,SaveCandidate,DeliveryCleanup,Count};
inline constexpr std::array<char const*,unsigned(RepairStage::Count)> stage_names={"ParseInput","CopyAst","CompileTerms","DependencyIndex","CollectEqualities","Components","Elimination","VerifyDirections","BuildAffected","Metadata","Protect","ScoreBase","RankDirections","NumericValues","LineTerms","FormulaDomain","TargetSelection","ModularHits","CandidateBuild","ValidateFormula","OfficialObserve","PreserveAndScore","SerializeResult","MandatoryDelivery","BuildScoreIndex","ScoreSyncNodes","ScoreSyncGroups","ScorePublish","SaveCandidate","DeliveryCleanup"};
inline double trace_wall()noexcept{return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();}
inline double trace_cpu()noexcept{timespec t{};clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return t.tv_sec+t.tv_nsec*1e-9;}
struct StageRecord {
    uint64_t calls=0,completed=0,incomplete=0,nodes=0,edges=0,cache_hits=0,cache_misses=0,full_size_allocations=0,allocation_slots=0,full_size_scans=0,scan_slots=0,budget_checks=0;
    double inclusive_cpu=0,inclusive_wall=0,exclusive_cpu=0,exclusive_wall=0;
    int64_t current_node=-1,current_direction=-1;
};
class StageScope;
struct CostTrace {
    std::array<StageRecord,unsigned(RepairStage::Count)> records{};
    StageScope* active=nullptr;RepairStage stage=RepairStage::Count,last_incomplete=RepairStage::Count;
    int64_t current_node=-1,current_direction=-1,last_node=-1,last_direction=-1;
    int64_t current_component=-1,current_local_direction=-1;
    nlohmann::json verified_directions=nlohmann::json::array();
    uint64_t equality_rows=0,verify_slots=0,verify_full_scans=0,verify_touched=0,verify_multiply_adds=0,influence_words=0,influence_ors=0,influence_bytes=0,affected_storage_bytes=0,score_index_bytes=0,score_state_bytes=0,rank_sync_nodes=0,changed_covered_bits=0,dirty_groups=0,score_updates=0;
    uint64_t dependency_entries=0,coefficient_entries=0,affected_entries=0,elimination_ops=0,numeric_cache_bytes=0,completed_domains=0,completed_candidates=0;
    StageRecord* record()noexcept{return stage==RepairStage::Count?nullptr:&records[unsigned(stage)];}
    void node(unsigned n)noexcept{current_node=n;if(auto r=record()){++r->nodes;r->current_node=n;r->current_direction=current_direction;}}
    void edges(uint64_t n)noexcept{if(auto r=record())r->edges+=n;}
    void allocation(uint64_t n,uint64_t arrays=1)noexcept{if(auto r=record()){r->full_size_allocations+=arrays;r->allocation_slots+=n*arrays;}}
    void scan(uint64_t n)noexcept{if(auto r=record()){++r->full_size_scans;r->scan_slots+=n;}}
    void hit(bool yes)noexcept{if(auto r=record())++(yes?r->cache_hits:r->cache_misses);}
    nlohmann::json json()const{nlohmann::json j={{"stages",nlohmann::json::object()},{"dependency_entries",dependency_entries},{"coefficient_entries",coefficient_entries},{"affected_entries",affected_entries},{"elimination_ops",elimination_ops},{"numeric_cache_bytes",numeric_cache_bytes},{"completed_domains",completed_domains},{"completed_candidates",completed_candidates},{"last_incomplete_stage",last_incomplete==RepairStage::Count?nlohmann::json(nullptr):nlohmann::json(stage_names[unsigned(last_incomplete)])},{"last_incomplete_node",last_node},{"last_incomplete_direction",last_direction}};
        j["current_component"]=current_component;j["current_local_direction"]=current_local_direction;j["verified_directions"]=verified_directions;
        j["work"]={{"equality_rows",equality_rows},{"verify_slots",verify_slots},{"verify_full_scans",verify_full_scans},{"verify_touched",verify_touched},{"verify_multiply_adds",verify_multiply_adds},{"influence_words",influence_words},{"influence_ors",influence_ors},{"influence_bytes",influence_bytes},{"affected_storage_bytes",affected_storage_bytes},{"score_index_bytes",score_index_bytes},{"score_state_bytes",score_state_bytes},{"rank_sync_nodes",rank_sync_nodes},{"changed_covered_bits",changed_covered_bits},{"dirty_groups",dirty_groups},{"score_updates",score_updates}};
        for(unsigned i=0;i<records.size();++i){auto const& r=records[i];if(!r.calls)continue;j["stages"][stage_names[i]]={{"calls",r.calls},{"completed",r.completed},{"incomplete",r.incomplete},{"nodes",r.nodes},{"edges",r.edges},{"cache_hits",r.cache_hits},{"cache_misses",r.cache_misses},{"full_size_allocations",r.full_size_allocations},{"allocation_slots",r.allocation_slots},{"full_size_scans",r.full_size_scans},{"scan_slots",r.scan_slots},{"budget_checks",r.budget_checks},{"inclusive_cpu",r.inclusive_cpu},{"inclusive_wall",r.inclusive_wall},{"exclusive_cpu",r.exclusive_cpu},{"exclusive_wall",r.exclusive_wall},{"current_node",r.current_node},{"current_direction",r.current_direction}};}return j;}
};
class StageScope {
    CostTrace* trace;StageScope* parent=nullptr;RepairStage stage,previous;double w=0,c=0,child_w=0,child_c=0;int exceptions=0;bool forced_incomplete=false;
public:
    StageScope(CostTrace* t,RepairStage s)noexcept:trace(t),stage(s){if(!trace)return;parent=trace->active;previous=trace->stage;trace->active=this;trace->stage=s;w=trace_wall();c=trace_cpu();exceptions=std::uncaught_exceptions();++trace->records[unsigned(s)].calls;}
    void mark_incomplete()noexcept{forced_incomplete=true;if(parent)parent->mark_incomplete();}
    ~StageScope()noexcept{if(!trace)return;double ew=trace_wall()-w,ec=trace_cpu()-c;auto& r=trace->records[unsigned(stage)];r.inclusive_wall+=ew;r.inclusive_cpu+=ec;r.exclusive_wall+=ew-child_w;r.exclusive_cpu+=ec-child_c;bool failed=forced_incomplete||std::uncaught_exceptions()>exceptions;if(failed&&parent)parent->mark_incomplete();if(failed){++r.incomplete;if(trace->last_incomplete==RepairStage::Count){trace->last_incomplete=stage;trace->last_node=trace->current_node;trace->last_direction=trace->current_direction;}}else ++r.completed;if(parent){parent->child_w+=ew;parent->child_c+=ec;}trace->active=parent;trace->stage=previous;}
    StageScope(StageScope const&)=delete;StageScope& operator=(StageScope const&)=delete;
};
}
