#include "liasampler.h"

#include <filesystem>
#include <fstream>
#include <regex>

namespace sampler {

std::string processNegNumber(const std::string& input) {
    std::regex pattern(R"(\(\s*(-\s*\d+)\s*\))");
    std::string result;

    std::sregex_iterator begin(input.begin(), input.end(), pattern);
    std::sregex_iterator end;

    size_t lastPos = 0;
    for (auto it = begin; it != end; ++it) {
        result += input.substr(lastPos, it->position() - lastPos);
        std::string number = (*it)[1].str();
        number.erase(std::remove_if(number.begin(), number.end(), ::isspace), number.end());
        result += number;
        lastPos = it->position() + it->length();
    }

    result += input.substr(lastPos);

    return result;
}

std::string extract_filename(const std::string& path) {
    size_t pos = path.find_last_of('/');
    if (pos != std::string::npos) {
        return path.substr(pos + 1);
    }
    return path;
}

void LiaSampler::print_statistic() {
    std::cout << "--------------------- After sampling: statistic ---------------------\n";
    std::cout << "Sampling time: " << TimeElapsed() << "\n";
    std::cout << "Total samples number: " << num_samples << "\n";
}

double LiaSampler::TimeElapsed() {
    std::chrono::steady_clock::time_point finish = std::chrono::steady_clock::now();
    std::chrono::duration<double> duration = finish - time_sampling_start;
    return duration.count();
}

z3::tactic LiaSampler::mk_preamble_tactic(z3::context& ctx) {
    z3::params pull_ite_p(ctx);

    pull_ite_p.set("pull_cheap_ite", true);
    pull_ite_p.set("push_ite_arith", false);
    pull_ite_p.set("local_ctx", true);
    pull_ite_p.set("local_ctx_limit", 10000000u);
    pull_ite_p.set("hoist_ite", true);

    z3::params ctx_simp_p(ctx);
    ctx_simp_p.set("max_depth", 30u);
    ctx_simp_p.set("max_steps", 5000000u);

    // z3::params solve_eqs_p(ctx);
    // solve_eqs_p.set("solve_eqs_max_occs", 5U);

    z3::params lhs_p(ctx);
    lhs_p.set("arith_lhs", true);

    z3::params main_p(ctx);
    main_p.set("elim_and", true);
    main_p.set("som", true);
    main_p.set("blast_distinct", true);
    main_p.set("blast_distinct_threshold", 128u);
    // main_p.set("eq2ineq", true);

    return z3::with(z3::tactic(ctx, "simplify") &
                        z3::tactic(ctx, "propagate-values") &
                        z3::with(z3::tactic(ctx, "ctx-simplify"), ctx_simp_p) &
                        z3::with(z3::tactic(ctx, "simplify"), pull_ite_p) &
                        z3::tactic(ctx, "solve-eqs") &
                        z3::with(z3::tactic(ctx, "simplify"), lhs_p),
                    main_p);
}

void LiaSampler::hybrid_sampling(std::ofstream& samplesFile) {
    std::cout << "-----------------------HYBRID-SAMPLING MODE-----------------------\n";
    if (maxNumSamples == 0 || TimeElapsed() >= maxTimeLimit) return;

    std::uniform_real_distribution<double> dist(0.0, 1.0);

    z3::goal g(c);
    g.add(original_formula);
    z3::tactic preamble_tactic = mk_preamble_tactic(c);
    z3::apply_result simp_ar = preamble_tactic(g);

    assert(simp_ar.size() == 1);
    z3::goal subgoal = simp_ar[0];

    /* LS solver */
    z3::params smt_p(c);
    smt_p.set("ls_sampling", true);
    smt_p.set("auto_config", false);
    smt_p.set("logic", "QF_LIA");
    z3::solver ls_solver = z3::with(z3::tactic(c, "smt"), smt_p).mk_solver();  // test

    for (unsigned i = 0; i < subgoal.size(); i++) {  // test
        ls_solver.add(subgoal[i]);
    }
    // ls_solver.add(original_formula);

    /* CDCL(T) solver */
    z3::solver cdcl_solver(c);
    cdcl_solver.set("timeout", 50000U);  // 50 seconds
    cdcl_solver.add(original_formula);

    z3::model m_ls(c);
    z3::check_result res;
    while (num_samples < maxNumSamples && TimeElapsed() < maxTimeLimit) {
        // cdcl sampling
        for (size_t k = 0; k < cdcl_epoch; ++k) {
            if (TimeElapsed() >= maxTimeLimit) break;
            cdcl_solver.set("timeout", static_cast<unsigned>(std::max(1.0,
                std::min(50000.0, (maxTimeLimit - TimeElapsed()) * 1000.0))));
            // cdcl_solver.push();
            z3::expr_vector assertions_vector(c);
            if (num_samples != 0) {
                for (size_t j = 0; j < m_ls.size(); ++j) {
                    if (m_ls[j].is_const() && m_ls[j].decl_kind() != Z3_OP_TRUE && m_ls[j].decl_kind() != Z3_OP_FALSE && dist(mt) < fixed_var_pct) {
                        // Keep the original declaration and sort (Int or Bool).
                        assertions_vector.push_back(m_ls[j]() == m_ls.get_const_interp(m_ls[j]));
                    }
                }
            }
            res = expr_session->check(cdcl_solver, assertions_vector);

            if (z3::sat == res) {
                z3::model cdcl_m = cdcl_solver.get_model();
                sample_source="CDCL";
                record_model(cdcl_m, samplesFile);
#ifdef VERBOSE
                std::cout << "============Sample from CDCL(T)============\n";
#endif
            } else {
                if (res == z3::unsat && assertions_vector.empty()) { expr_session->end_query(); return; }
                std::cout << "CDCL(T) returned " << res << "\n";
            }
            expr_session->end_query();
        }

        if (num_samples < maxNumSamples && TimeElapsed() < maxTimeLimit) {
            if (!expr_session->ccss_enabled()) continue;
            if (!expr_session->ccss_bounded() && maxTimeLimit-TimeElapsed()<1.0) break; // native integral timeout
            // ls sampling
            ls_solver.set("random_seed", gen_random_seed());
            ls_solver.set("ls_timeout", static_cast<unsigned>(
                std::max(0.0, std::min(60.0, maxTimeLimit - TimeElapsed()))));
            expr_session->begin_ccss(ls_solver);
            z3::check_result check_res = ls_solver.check();
            expr_session->checked_ccss(check_res);
            if (z3::sat != check_res) {
                expr_session->end_ccss();
                std::cout << "Unsat or unknown case form LS!\n";
                continue;
            }
            m_ls = ls_solver.get_model();
            m_ls = subgoal.convert_model(m_ls);  // test

            sample_source="CCSS";
            record_model(m_ls, samplesFile);
            expr_session->end_ccss();
#ifdef VERBOSE
            std::cout << "============Sample from stochastic Local Search============\n";
#endif
        }

        if (TimeElapsed() > maxTimeLimit || num_samples >= maxNumSamples) {
            break;
        }
    }
}

void LiaSampler::record_model(z3::model model, std::ofstream& samplesFile) {
    if (expr_session->commit(model,sample_source)) ++num_samples;
}

void LiaSampler::print_unique_sample(std::ofstream& samplesFile) {
    // Store the exact assignment; hashes alone can collide for different models.
    // Length prefixes keep the key unambiguous even for quoted SMT identifiers.
    std::string key;
    for (const auto& p : curr_sample) {
        key += std::to_string(p.first.size()) + ":" + p.first;
        key += std::to_string(p.second.size()) + ":" + p.second;
    }
    if (unique_samples.insert(std::move(key)).second) {
        samplesFile << num_samples << ": ";
        for (auto p : curr_sample) {
            samplesFile << p.first << ":" << p.second << ";";
        }
        samplesFile << "\n";
        num_samples++;
#ifdef VERBOSE
        std::cout << "The " << num_samples << " sample is being generated ..." << std::endl;
#endif
    }
#ifdef VERBOSE
    else {
        std::cout << "duplicate samples\n";
    }
#endif

    curr_sample.clear();
}

unsigned LiaSampler::gen_random_seed() {
    std::uniform_int_distribution<std::uint64_t> dist(0, UINT64_MAX);
    return dist(mt);
}

void LiaSampler::sampling() {
    time_sampling_start = std::chrono::steady_clock::now();

    parseSmtFile();
    expr_session=std::make_unique<esg::Session>(original_formula,samplesFileDir,maxTimeLimit,time_sampling_start);

    std::string samplesFileName = samplesFileDir + "/" + extract_filename(smtFilePath) + ".samples";
    std::ofstream samplesFile(samplesFileName);
    if (!samplesFile) {
        std::cerr << "Unable to open file " << samplesFileName << std::endl;
        return;
    }

    hybrid_sampling(samplesFile);
    expr_session->finish();

    samplesFile.close();

    print_statistic();
}
}  // namespace sampler
