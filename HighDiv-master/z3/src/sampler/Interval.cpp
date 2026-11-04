#include "Interval.h"
#include "util/debug.h"
#include <sstream>
#include <cstring>

namespace sampler {
// Select one nonempty component of domain \ a. Integer endpoints are excluded.
Interval random_complement(const Interval& a, std::mt19937& mt, const Interval& domain) {
    if (domain.start > domain.end) return Interval(1, 0);
    if (a.start > a.end || a.end < domain.start || a.start > domain.end)
        return domain;
    std::vector<Interval> result;
    if (a.start > domain.start) {
        result.emplace_back(domain.start, a.start - 1);
    }
    if (a.end < domain.end) {
        result.emplace_back(a.end + 1, domain.end);
    }
    if (result.empty()) return Interval(1, 0);
    std::uniform_int_distribution<size_t> dis(0, result.size() - 1);
    return result[dis(mt)];
}

void printInterval(const Interval& interval) {
    std::cout << "[" << interval.start << ", " << interval.end << "]\n";
}

void printIntervals(const std::vector<Interval>& intervals) {
    for (const auto& interval : intervals) {
        printInterval(interval);
        std::cout << " ";
    }
    std::cout << std::endl;
}

}
