#pragma once

#include <map>
#include <random>
#include <string>
#include <unordered_set>
#include "sampler.h"

#define VERBOSE
#define DEBUG

namespace sampler {


class LiaSampler : public Sampler {
    std::chrono::steady_clock::time_point time_sampling_start;
    size_t num_samples = 0;
    size_t num_ls_samples = 0;
    size_t num_cdcl_samples = 0;
    std::mt19937 mt;
    std::random_device rd;
    std::map<std::string, std::string> curr_sample;
    std::unordered_set<std::string> unique_samples;
    static constexpr size_t cdcl_epoch = 1;
    static constexpr double fixed_var_pct = 0.5;

    double TimeElapsed();
    void print_statistic();
    void record_model(z3::model model, std::ofstream& samplesFile);

   public:
    LiaSampler(z3::context* _c, std::string _smtFilePath, std::string _samplesFileDir, size_t _maxNumSamples, double _maxTimeLimit, unsigned seed)
        : Sampler(_c, _smtFilePath, _samplesFileDir, _maxNumSamples, _maxTimeLimit) {
        mt.seed(seed);
    }


    z3::tactic mk_preamble_tactic(z3::context& ctx);

    void sampling() override;
    void print_unique_sample(std::ofstream& samplesFile);
    void hybrid_sampling(std::ofstream& samplesFile);
    unsigned gen_random_seed();
};
};  // namespace sampler
