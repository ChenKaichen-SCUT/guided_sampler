#pragma once
// Included within a2 after PhaseEvidence. Pure policy, no state or RNG effects.
namespace r5 {
enum class CoveragePolicy { ReferenceOnly, Full, SupportOnly };
struct CoverageChoice {bool phase;bool avoid;};
inline std::optional<CoverageChoice> choose_coverage(r4::PhaseEvidence const& e,CoveragePolicy p){
 if(p==CoveragePolicy::ReferenceOnly||!e.complete)return std::nullopt;
 if(e.support[0]!=e.support[1])return CoverageChoice{e.support[1]>e.support[0],false};
 if(p==CoveragePolicy::Full&&e.block[0]!=e.block[1])return CoverageChoice{e.block[1]<e.block[0],true};
 return std::nullopt;
}
}
