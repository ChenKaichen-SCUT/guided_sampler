#pragma once
// Included inside a2. Counts are deduplicated original (node,bit,desired).
namespace r4 {
using Masks=std::map<unsigned,std::pair<uint64_t,uint64_t>>;
struct PhaseEvidence {
 Masks supports[2],blocks[2];unsigned support[2]={0,0},block[2]={0,0};bool complete=true;
 std::optional<bool> best()const {
  if(!complete)return std::nullopt;
  if(support[0]!=support[1])return support[1]>support[0];
  if(block[0]!=block[1])return block[1]<block[0];
  return std::nullopt;
 }
};
inline PhaseEvidence score_phase_evidence(Entry const& entry,Work& w){
 PhaseEvidence out;
 try{for(auto const& r:entry.rules){w.check();auto& s=out.supports[r.phase][r.node];s.first|=r.one&r.want_one;s.second|=r.zero&r.want_zero;auto& b=out.blocks[r.phase][r.node];b.first|=r.zero&r.want_one;b.second|=r.one&r.want_zero;}
 for(unsigned p=0;p<2;++p){for(auto const& kv:out.supports[p])out.support[p]+=pop(kv.second.first)+pop(kv.second.second);for(auto const& kv:out.blocks[p])out.block[p]+=pop(kv.second.first)+pop(kv.second.second);}}
 catch(std::runtime_error const&){out.complete=false;}return out;
}
inline Masks advice_targets(PhaseEvidence const& ev,bool phase,bool avoid){
 if(!avoid)return ev.supports[phase];Masks out;
 for(auto const& kv:ev.blocks[!phase]){auto i=ev.blocks[phase].find(kv.first);auto same=i==ev.blocks[phase].end()?std::pair<uint64_t,uint64_t>{0,0}:i->second;out[kv.first]={kv.second.first&~same.first,kv.second.second&~same.second};}return out;
}
inline std::string advice_identity(std::string const& key,bool phase,char const* kind,unsigned node,unsigned bit,bool desired){return std::to_string(key.size())+":"+key+":"+std::to_string(phase)+":"+kind+":"+std::to_string(node)+":"+std::to_string(bit)+":"+std::to_string(desired);}
}
