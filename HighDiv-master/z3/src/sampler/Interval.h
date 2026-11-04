#ifndef _INTERVAL_H
#define _INTERVAL_H
#include <iostream>
#include <random>
#include <vector>

namespace sampler {
struct Interval {
    int64_t start, end;
    Interval() : start(INT64_MIN), end(INT64_MAX) {}
    Interval(int64_t s, int64_t e) : start(s), end(e) {}
};
Interval random_complement(const Interval& a, std::mt19937& mt, const Interval& domain = Interval());
void printInterval(const Interval& interval);
void printIntervals(const std::vector<Interval>& intervals);

}  // namespace sampler
#endif
