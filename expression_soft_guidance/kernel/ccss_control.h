#pragma once
#include <chrono>
#include <array>
#include <stdexcept>

// Only the explicit host CCSS call enables this clock. No RNG or solver
// decision is touched when budgeting is disabled.
namespace expr_ccss {
using clock = std::chrono::steady_clock;
struct control {
    bool active=false, bounded=false, expired=false;
    unsigned phase=0;
    uint64_t visits=0;
    clock::time_point start,mark,deadline;
    std::array<double,6> seconds{}; // setup, mapping, build, init, search, model
};
inline control& state() { static thread_local control s; return s; }
inline void checkpoint(bool force=false) {
    auto& s=state();
    if (!s.active || !s.bounded) return;
    if (!force && (++s.visits & 63)) return;
    if (clock::now() >= s.deadline) {
        s.expired=true;
        throw std::runtime_error("CCSS phase budget exhausted");
    }
}
inline void phase(unsigned p) {
    auto& s=state(); if(!s.active)return;
    auto now=clock::now();s.seconds[s.phase]+=std::chrono::duration<double>(now-s.mark).count();
    s.mark=now;s.phase=p;
}
struct phase_scope {
    unsigned previous;
    explicit phase_scope(unsigned p):previous(state().phase){phase(p);checkpoint(true);}
    ~phase_scope(){phase(previous);}
};
inline void begin(double ms) {
    auto& s=state();s=control{};s.active=true;s.bounded=ms>0;
    s.start=s.mark=clock::now();
    s.deadline=s.start+std::chrono::duration_cast<clock::duration>(std::chrono::duration<double,std::milli>(ms));
}
inline void end(double* out) {
    auto& s=state();phase(s.phase);
    for(unsigned i=0;i<6;++i)out[i]=s.seconds[i];
    out[6]=s.expired;out[7]=double(s.visits);s.active=false;
}
}
