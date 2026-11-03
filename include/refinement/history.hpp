#pragma once
#include "observations.hpp"
namespace refinement {
struct ObservationHistory {std::vector<uint64_t> zero,one;uint64_t version=0;explicit ObservationHistory(size_t n=0):zero(n,0),one(n,0){}
    void commit(ObservationTrace const& t){if(zero.size()!=t.zero.size())throw std::runtime_error("observation universe changed");for(size_t i=0;i<zero.size();++i){zero[i]|=t.zero[i];one[i]|=t.one[i];}++version;}
    uint64_t covered()const{uint64_t c=0;for(size_t i=0;i<zero.size();++i)c+=std::popcount(zero[i]&one[i]);return c;}
    uint64_t observed()const{uint64_t c=0;for(size_t i=0;i<zero.size();++i)c+=std::popcount(zero[i])+std::popcount(one[i]);return c;}
};
struct ProtectedObservations{std::vector<uint64_t> zero,one;uint64_t count=0;};
struct CoverageGain {uint64_t covered=0,observed=0;auto operator<=>(CoverageGain const&)const=default;};
inline ProtectedObservations make_protected(ObservationTrace const& base,ObservationHistory const& h,WorkBudget& b){ProtectedObservations p;p.zero.resize(h.zero.size());p.one.resize(h.one.size());for(size_t i=0;i<h.zero.size();++i){b.check();p.zero[i]=base.zero.at(i)&~h.zero[i];p.one[i]=base.one.at(i)&~h.one[i];p.count+=std::popcount(p.zero[i])+std::popcount(p.one[i]);}return p;}
inline Json missing(ProtectedObservations const& p,ObservationTrace const& t,WorkBudget& b){Json j=Json::array();for(unsigned i=0;i<p.zero.size();++i){b.check();auto z=p.zero[i]&~t.zero.at(i),o=p.one[i]&~t.one.at(i);while(z){unsigned bit=std::countr_zero(z);j.push_back({i,bit,0});z&=z-1;}while(o){unsigned bit=std::countr_zero(o);j.push_back({i,bit,1});o&=o-1;}}return j;}
inline bool preserves(ProtectedObservations const& p,ObservationTrace const& t,WorkBudget& b){for(size_t i=0;i<p.zero.size();++i){b.check();if((p.zero[i]&~t.zero.at(i))||(p.one[i]&~t.one.at(i)))return false;}return true;}
inline CoverageGain marginal_gain(ObservationTrace const& t,ObservationHistory const& h,WorkBudget& b){CoverageGain g;for(size_t i=0;i<h.zero.size();++i){b.check();g.observed+=std::popcount(t.zero.at(i)&~h.zero[i])+std::popcount(t.one.at(i)&~h.one[i]);g.covered+=std::popcount((h.zero[i]|t.zero[i])&(h.one[i]|t.one[i]))-std::popcount(h.zero[i]&h.one[i]);}return g;}
inline bool contains(ObservationHistory const& h,ObservationHistory const& other){if(h.zero.size()!=other.zero.size())return false;for(size_t i=0;i<h.zero.size();++i)if((other.zero[i]&~h.zero[i])||(other.one[i]&~h.one[i]))return false;return true;}
struct OutputLedger {std::set<std::string> unique;uint64_t committed_count=0;ObservationHistory observations;explicit OutputLedger(size_t n=0):observations(n){}
    void commit(Assignment const& a,ObservationTrace const& t){auto key=assignment_key(a);if(unique.count(key))throw std::runtime_error("duplicate output commit");unique.insert(key);observations.commit(t);++committed_count;}
};
struct NativeLedger {std::set<std::string> unique;uint64_t accepted_count=0;ObservationHistory observations;explicit NativeLedger(size_t n=0):observations(n){}
    bool accept(Assignment const& a,ObservationTrace const& t){if(!t.legal)throw std::runtime_error("illegal native model");if(!unique.insert(assignment_key(a)).second)return false;observations.commit(t);++accepted_count;return true;}
};
}
