#pragma once

#include <z3++.h>
#include <chrono>
#include <iostream>
#include <unordered_set>

// #define PRINT_PROGRESS
// #define SHOW_PROGRESS_BAR

namespace sampler {
class Sampler {
   protected:
    std::string smtFilePath;
    std::string samplesFileDir;
    unsigned maxNumSamples;
    double maxTimeLimit;
    unsigned seed;
    std::chrono::steady_clock::time_point start;

    z3::context& c;
    z3::expr original_formula;

   private:
    // formula statistic
    int num_arrays = 0, num_bv = 0, num_bools = 0, num_bits = 0, num_uf = 0,
        num_ints = 0, num_reals = 0;
    std::vector<z3::func_decl> variables;          // function declarations in formulas
    std::vector<std::string> variable_names;       // used for model Record the names of the variables in the model (excluding uninterpreted functions)
    std::unordered_set<std::string> var_names = {  // variable names in formulas
        "bv", "Int", "true",
        "false"};       // initialize with constant names so that
                        // constants are not mistaken for variables
    int max_depth = 0;  // AST max depth
    bool has_arrays = false;         // whether the formula contains an array
    std::unordered_set<Z3_ast> sup;  // bat: nodes (=leaves?) independent Support Set?
    std::string result = "unknown";  // success/failure

public:
    Sampler(z3::context* _c)
        : c(*_c), original_formula(c){
        }

    Sampler(z3::context* _c, std::string _smtFilePath, std::string _samplesFileDir, size_t _maxNumSamples, double _maxTimeLimit)
        : c(*_c), smtFilePath(_smtFilePath), samplesFileDir(_samplesFileDir), maxNumSamples(_maxNumSamples), maxTimeLimit(_maxTimeLimit), original_formula(c) {
    }

    virtual void sampling() = 0;
    void parseSmtFile();
    
    /* formula statistic */
    void _compute_formula_stats_aux(z3::expr e, int depth = 0);
    void safe_exit(int exitcode);
};
};  // namespace sampler