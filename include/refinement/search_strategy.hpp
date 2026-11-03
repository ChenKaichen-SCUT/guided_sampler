#pragma once
#include "cost_trace.hpp"
namespace refinement {
enum class EqualityVerifyStrategy { FullRows, SparseRows };
enum class InfluenceStrategy { TransitiveVariables, ReverseParents, DirectionBits };
enum class ScoreStrategy { AffectedScan, GroupedIncremental };
enum class StopPolicy { AuditAll, FirstCovered };
struct SearchStrategies {
    RepairMode numeric=RepairMode::Legacy;
    EqualityVerifyStrategy verify=EqualityVerifyStrategy::FullRows;
    InfluenceStrategy influence=InfluenceStrategy::TransitiveVariables;
    ScoreStrategy score=ScoreStrategy::AffectedScan;
};
inline SearchStrategies historical_strategies(RepairMode mode){SearchStrategies s;s.numeric=mode;if(mode==RepairMode::Shared)s.influence=InfluenceStrategy::ReverseParents;return s;}
inline SearchStrategies delivery_strategies(std::string const& name){
    SearchStrategies s;s.numeric=RepairMode::ValueCache;
    if(name!="V0"&&name!="V1"&&name!="V2"&&name!="V3")throw std::runtime_error("invalid delivery configuration");
    if(name!="V0")s.verify=EqualityVerifyStrategy::SparseRows;
    if(name=="V2"||name=="V3")s.influence=InfluenceStrategy::DirectionBits;
    if(name=="V3")s.score=ScoreStrategy::GroupedIncremental;
    return s;
}
}
