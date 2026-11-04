// Tests inspect the starting assignment before local search can overwrite it.
// The test compiler uses -fno-access-control; production exposes no test API.
#include "sampler/sampler.h"

#include <stdexcept>

using sampler::Interval;
using sampler::ls_sampler;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void configure(ls_sampler& s, int64_t lower, int64_t upper) {
    s._num_vars = 1;
    s._vars.resize(1);
    s._vars[0].var_name = "x";
    s._vars[0].is_lia = true;
    s._vars[0].low_bound = lower;
    s._vars[0].upper_bound = upper;
    s._solution.resize(1);
    s._vars_initialization_intervals.resize(1);
    s._lits.resize(1);  // Literal zero is reserved by the sampler.
    s._lit_appear.push_back(false);
}

int inequality(ls_sampler& s, int64_t coefficient, int64_t constant) {
    sampler::lit l;
    l.lits_index = s._lits.size();
    l.is_lia_lit = true;
    l.key = constant;
    if (coefficient > 0) {
        l.pos_coff = {coefficient};
        l.pos_coff_var_idx = {0};
    } else {
        l.neg_coff = {-coefficient};
        l.neg_coff_var_idx = {0};
    }
    s._lits.push_back(l);
    s._lit_appear.push_back(true);
    return l.lits_index;
}

void clause(ls_sampler& s, std::initializer_list<int> literals) {
    sampler::clause c;
    c.literals = literals;
    int clause_id = s._clauses.size();
    s._clauses.push_back(c);
    std::set<int> involved;
    for (int signed_id : literals) {
        const auto& l = s._lits[std::abs(signed_id)];
        auto add = [&](int idx, __int128_t coefficient) {
            auto& v = s._vars[idx];
            involved.insert(idx);
            v.literals.push_back(signed_id);
            v.literal_clause.push_back(clause_id);
            v.literal_coff.push_back(coefficient);
            v.is_in_equal |= l.is_equal;
            v.occs++;
        };
        for (size_t j = 0; j < l.pos_coff.size(); ++j)
            add(l.pos_coff_var_idx[j], l.pos_coff[j]);
        for (size_t j = 0; j < l.neg_coff.size(); ++j)
            add(l.neg_coff_var_idx[j], -l.neg_coff[j]);
    }
    for (int idx : involved) s._vars[idx].clause_idxs.push_back(clause_id);
}

int add_variable(ls_sampler& s, const char* name) {
    sampler::variable v;
    v.var_name = name;
    v.is_lia = true;
    s._vars.push_back(v);
    s._num_vars = s._vars.size();
    s._solution.resize(s._num_vars);
    return s._num_vars - 1;
}

int relation(ls_sampler& s, int x, int y, int64_t constant, bool equality = false) {
    int id = inequality(s, 1, constant);
    auto& l = s._lits[id];
    l.pos_coff_var_idx = {x};
    l.neg_coff_var_idx = {y};
    l.neg_coff = {1};
    l.is_equal = equality;
    return id;
}

void paper_example() {
    ls_sampler s(0, 60);
    configure(s, -20, 20);
    int y = add_variable(s, "y"), z = add_variable(s, "z");
    // (y-x<=-1 or -x<=-10) and y-z<=0 and x-z<=3; M=(10,7,7).
    clause(s, {relation(s, y, 0, 1), inequality(s, -1, 10)});
    clause(s, {relation(s, y, z, 0)});
    clause(s, {relation(s, 0, z, -3)});
    s.last_cdcl_model = {{"x", "10"}, {"y", "7"}, {"z", "7"}};
    s._vars[0].in_occs_closure = true;
    s.calc_var_intervals();
    auto direct = s._vars_initialization_intervals[0];
    require(direct.start == 8 && direct.end == 10, "paper Example 3 must produce [8,10]");
    bool seen[3] = {};
    for (int i = 0; i < 64; ++i) {
        s.construct_solution_score();
        require(s._solution[0] >= 8 && s._solution[0] <= 10, "high-frequency values must stay inside [8,10]");
        seen[s._solution[0] - 8] = true;
    }
    require(seen[0] && seen[1] && seen[2], "high-frequency initialization must sample the interval");
    s._vars[0].in_occs_closure = false;
    bool left = false, right = false;
    for (int i = 0; i < 64; ++i) {
        s.calc_var_intervals();
        auto reverse = s._vars_initialization_intervals[0];
        require((reverse.start == -20 && reverse.end == 7) ||
                (reverse.start == 11 && reverse.end == 20), "general system must use the strict complement");
        left |= reverse.end == 7;
        right |= reverse.start == 11;
        s.construct_solution_score();
        require(s._solution[0] <= 7 || s._solution[0] >= 11, "general value must lie outside [8,10]");
    }
    require(left && right, "both reverse intervals must be reachable");
}

void partition_closures() {
    ls_sampler s(0, 60);
    configure(s, -10, 10);
    int y = add_variable(s, "y"), z = add_variable(s, "z");
    int h = add_variable(s, "h"), k = add_variable(s, "k");
    int boundary = add_variable(s, "boundary");
    clause(s, {relation(s, 0, y, 0, true)});
    clause(s, {relation(s, y, z, 0)});
    clause(s, {relation(s, h, k, 0)});
    s._vars[0].occs = 100;
    s._vars[h].occs = 51;
    s._vars[boundary].occs = 50;
    s.build_occs_closures();
    for (int i : {0, y, z}) {
        require(s._vars[i].in_equal_closure, "equality closure must propagate through inequalities");
        require(!s._vars[i].in_occs_closure, "equality and high-frequency systems must be disjoint");
    }
    for (int i : {h, k})
        require(s._vars[i].in_occs_closure && !s._vars[i].in_equal_closure, "high-frequency closure propagation");
    require(!s._vars[boundary].in_occs_closure, "frequency must be strictly greater than 50");
}

void complement_boundaries() {
    std::mt19937 random(0);
    for (int i = 0; i < 100; ++i) {
        auto interval = sampler::random_complement(Interval(3, 7), random);
        require(interval.end == 2 || interval.start == 8,
                "the integer complement must exclude both original endpoints");
    }
}

void complement_sides() {
    std::mt19937 random(0);
    bool left = false, right = false;
    for (int i = 0; i < 100; ++i) {
        auto interval = sampler::random_complement(Interval(3, 7), random);
        left |= interval.start == INT64_MIN;
        right |= interval.end == INT64_MAX;
    }
    require(left && right, "both nonempty complement sides must be selectable");
}

void complement_extremes() {
    std::mt19937 random(0);
    auto empty = sampler::random_complement(Interval(INT64_MIN, INT64_MAX), random);
    require(empty.start > empty.end, "the full domain must have an empty complement");
    auto full = sampler::random_complement(Interval(1, 0), random);
    require(full.start == INT64_MIN && full.end == INT64_MAX, "empty interval complement");
    auto maximum = sampler::random_complement(Interval(INT64_MIN, INT64_MAX - 1), random);
    require(maximum.start == INT64_MAX && maximum.end == INT64_MAX, "upper endpoint overflow");
    auto minimum = sampler::random_complement(Interval(INT64_MIN + 1, INT64_MAX), random);
    require(minimum.start == INT64_MIN && minimum.end == INT64_MIN, "lower endpoint overflow");
}

void equality_initialization() {
    ls_sampler s(0, 60);
    configure(s, -2, 2);
    s._vars[0].in_equal_closure = true;
    s._vars[0].in_occs_closure = true;  // Equality must take precedence.
    s._vars_initialization_intervals[0] = Interval(1, 1);
    s.construct_solution_score();
    require(s._solution[0] == 0, "equality system must start at zero");
    s._vars[0].low_bound = 2;
    s._vars[0].upper_bound = 5;
    s.construct_solution_score();
    require(s._solution[0] == 2, "equality initialization must honor hard bounds");
}

void bounded_reverse() {
    ls_sampler s(0, 60);
    configure(s, 0, 5);
    clause(s, {inequality(s, 1, -2)});  // x <= 2
    s.last_cdcl_model = {{"x", "1"}};
    s.calc_var_intervals();
    auto interval = s._vars_initialization_intervals[0];
    require(interval.start == 3 && interval.end == 5, "reverse interval must honor hard bounds");
    for (int i = 0; i < 32; ++i) {
        s.construct_solution_score();
        require(s._solution[0] >= 3 && s._solution[0] <= 5, "initial value must be in the reverse interval");
    }
}

void coefficients_and_false_literals() {
    ls_sampler s(0, 60);
    configure(s, 0, 10);
    // Under x=2 only the last two literals are true: their union is x<=4.
    clause(s, {inequality(s, -1, 7), inequality(s, 1, -3), inequality(s, 2, -8)});
    s.last_cdcl_model = {{"x", "2"}};
    s.calc_var_intervals();
    auto interval = s._vars_initialization_intervals[0];
    require(interval.start == 5 && interval.end == 10,
            "use each literal's coefficient and skip model-false literals");
}

void negative_literal() {
    ls_sampler s(0, 60);
    configure(s, 0, 10);
    clause(s, {-inequality(s, 1, -4)});  // not(x <= 4), model x=5
    s.last_cdcl_model = {{"x", "5"}};
    s.calc_var_intervals();
    auto interval = s._vars_initialization_intervals[0];
    require(interval.start == 0 && interval.end == 4, "negated inequalities need strict integer bounds");
}

void fallback() {
    ls_sampler s(0, 60);
    configure(s, 2, 4);
    s._vars_initialization_intervals[0] = Interval(10, 20);
    bool middle = false, upper = false;
    for (int i = 0; i < 64; ++i) {
        s.construct_solution_score();
        require(s._solution[0] >= 2 && s._solution[0] <= 4, "fallback must honor the variable domain");
        middle |= s._solution[0] == 3;
        upper |= s._solution[0] == 4;
    }
    require(middle && upper, "general fallback must sample the legal domain");
}

void oversized_model() {
    ls_sampler s(0, 60);
    configure(s, -3, 3);
    clause(s, {inequality(s, 1, 0)});
    s.last_cdcl_model = {{"x", "340282366920938463463374607431768211456"}};
    s.calc_var_intervals();
    auto interval = s._vars_initialization_intervals[0];
    require(interval.start > interval.end, "oversized model integers must not wrap into false guidance");
}

void equality_sampling_bounds() {
    ls_sampler s(0, 60);
    configure(s, 2, 5);
    s._vars[0].in_equal_closure = true;
    s.construct_solution_score();
    require(s._vars[0].s_lower_bound == 2 && s._vars[0].s_upper_bound == 5,
            "equality group must retain hard bounds for subsequent moves");
}

void empty_complement_fallback() {
    ls_sampler s(0, 60);
    configure(s, 2, 4);
    clause(s, {inequality(s, 1, -10)});
    s.last_cdcl_model = {{"x", "3"}};
    s.calc_var_intervals();
    auto interval = s._vars_initialization_intervals[0];
    require(interval.start > interval.end, "full feasible domain has no reverse interval");
    bool middle = false, upper = false;
    for (int i = 0; i < 64; ++i) {
        s.construct_solution_score();
        require(s._solution[0] >= 2 && s._solution[0] <= 4, "empty-complement fallback stays in domain");
        middle |= s._solution[0] == 3;
        upper |= s._solution[0] == 4;
    }
    require(middle && upper, "empty-complement fallback samples the domain");
}

void equality_requires_conjunction() {
    ls_sampler disjunction(0, 60);
    configure(disjunction, -10, 10);
    int y = add_variable(disjunction, "y");
    int a = relation(disjunction, 0, y, 0);
    int b = relation(disjunction, y, 0, 0);
    clause(disjunction, {a, b});
    disjunction.build_equal_table();
    disjunction.build_occs_closures();
    require(!disjunction._vars[0].in_equal_closure && !disjunction._vars[y].in_equal_closure,
            "opposite inequalities in a disjunction do not imply equality");

    ls_sampler conjunction(0, 60);
    configure(conjunction, -10, 10);
    y = add_variable(conjunction, "y");
    a = relation(conjunction, 0, y, 0);
    inequality(conjunction, 1, -9);  // An unused literal must not corrupt pairing.
    b = relation(conjunction, y, 0, 0);
    clause(conjunction, {a});
    clause(conjunction, {b});
    conjunction.build_equal_table();
    conjunction.build_occs_closures();
    require(conjunction._vars[0].in_equal_closure && conjunction._vars[y].in_equal_closure,
            "opposite positive unit constraints imply equality");
    require(conjunction._lits[a].equal_pair == b && conjunction._lits[b].equal_pair == a,
            "equal pairs must refer to the actual constraints");
}

void feasible_interval_outside_sampling_domain() {
    ls_sampler s(0, 60);
    configure(s, -10, 10);
    int far_lower = inequality(s, -1, 0);
    s._lits[far_lower].key = static_cast<__int128_t>(INT64_MAX) + 1;
    clause(s, {far_lower});
    clause(s, {inequality(s, -1, 5)});
    s.last_cdcl_model = {{"x", "9223372036854775808"}};
    s.calc_var_intervals();
    auto interval = s._vars_initialization_intervals[0];
    require(interval.start == -10 && interval.end == 10,
            "the complement of a feasible interval outside the sampling domain is the full domain");
}

void missing_model() {
    ls_sampler s(0, 60);
    configure(s, -3, 3);
    clause(s, {inequality(s, 1, 0)});
    s.calc_var_intervals();
    const auto interval = s._vars_initialization_intervals[0];
    require(interval.start > interval.end, "a missing model must not be replaced by a synthetic zero model");
    s.construct_solution_score();
    require(s._solution[0] >= -3 && s._solution[0] <= 3, "missing-model fallback must remain in bounds");
}

void boolean_model() {
    ls_sampler s(0, 60);
    configure(s, 0, 1);
    s._vars[0].is_lia = false;
    s.last_cdcl_model = {{"x", "true"}};
    s.calc_var_intervals();
    s.construct_solution_score();
    require(s._solution[0] == -1 || s._solution[0] == 1, "Boolean initialization must retain its representation");
}

void boundary_move_interval() {
    ls_sampler s(0, 60);
    configure(s, -20, 20);
    // At x=0, satisfy x>=1 while preserving the true context x<=3.
    clause(s, {inequality(s, -1, 1)});
    clause(s, {inequality(s, 1, -3)});
    s._solution[0] = 0;
    for (auto& l : s._lits) if (l.is_lia_lit) l.delta = s.delta_lit(l);
    bool seen[3] = {};
    for (int i = 0; i < 128; ++i) {
        __int128_t change = 1;
        s.interval_move(0, change);
        require(change >= 1 && change <= 3, "paper BAM example must stay in [1,3]");
        seen[change - 1] = true;
    }
    require(seen[0] && seen[1] && seen[2], "BAM must sample the whole feasible interval");
}

void boundary_move_singleton() {
    ls_sampler s(0, 60);
    configure(s, -20, 20);
    // At x=2, satisfy x<=1 while preserving the true context x>=1.
    clause(s, {inequality(s, 1, -1)});
    clause(s, {inequality(s, -1, 1)});
    s._solution[0] = 2;
    for (auto& l : s._lits) if (l.is_lia_lit) l.delta = s.delta_lit(l);
    for (int i = 0; i < 128; ++i) {
        __int128_t change = -1;
        s.interval_move(0, change);
        require(change == -1, "a singleton BAM interval must not sample its neighbour");
    }
}

void boundary_move_wide_interval() {
    ls_sampler s(0, 60);
    configure(s, INT64_MIN, INT64_MAX);
    clause(s, {inequality(s, 1, 0)});
    s._solution[0] = 1;
    s._lits[1].delta = 1;
    bool interior = false;
    for (int i = 0; i < 128; ++i) {
        __int128_t change = -1;
        s.interval_move(0, change);
        const auto value = s._solution[0] + change;
        require(value >= INT64_MIN && value <= 0, "wide BAM interval must remain in bounds");
        interior |= value < -1;
    }
    require(interior, "a wide BAM interval must not collapse to the critical boundary");
}

void parsed_integer_limits() {
    ls_sampler s(0, 1);
    s.make_lits_space(3);
    std::string lower = "1 ( <= ( + x y ) -9223372036854775808 )";
    s.build_lits(lower);
    require(s._lits[1].key == -static_cast<__int128_t>(INT64_MIN),
            "negating a 64-bit minimum constant must happen after widening");
    std::string wide = "2 ( <= ( + ( * 18446744073709551617 x ) y ) 18446744073709551618 )";
    s.build_lits(wide);
    const __int128_t two64 = static_cast<__int128_t>(UINT64_MAX) + 1;
    require(s._lits[2].pos_coff[0] == two64 + 1 && s._lits[2].key == -(two64 + 2),
            "128-bit coefficients and constants must not be truncated to int64");
}

void unsupported_integer_is_reported() {
    ls_sampler s(0, 1);
    s.make_lits_space(2);
    std::string literal = "1 ( <= ( + x y ) -170141183460469231731687303715884105728 )";
    bool rejected = false;
    try { s.build_lits(literal); }
    catch (const std::out_of_range&) { rejected = true; }
    require(rejected, "a constant beyond the local-search arithmetic domain must be rejected");
}

void overflowing_search_is_not_a_model() {
    ls_sampler s(0, 1);
    s.make_lits_space(2);
    std::string literal = "1 ( <= ( +";
    std::unordered_map<std::string, std::string> model;
    for (int i = 0; i < 8; ++i) {
        const auto name = "x" + std::to_string(i);
        model[name] = "0";
        literal += " ( * " + std::to_string(INT64_MAX - 2 * i) + " " + name + " )";
    }
    literal += " ) 0 )";
    s.build_lits(literal);
    std::vector<std::vector<int>> clauses{{1}};
    s.build_instance(clauses, model);
    s.ls_sampling();
    if (s._best_found_cost == 0) {
        require(!s.is_overflow, "overflowed clause evaluation cannot establish satisfaction");
        bool all_positive = true;
        for (int i = 0; i < 8; ++i) all_positive &= s._solution[i] > 0;
        require(!all_positive, "a positive sum cannot satisfy the nonpositive inequality");
    }
}

void independent_sampler_sizes() {
    auto move = [](ls_sampler& s, int literal_idx) {
        configure(s, -10, 10);
        s._lits.resize(literal_idx);
        s._lit_appear.resize(literal_idx);
        clause(s, {inequality(s, -1, 1)});
        s._num_lits = s._lits.size();
        s._num_clauses = 1;
        s._num_bool_lits = 0;
        s._num_opt = 10;
        s.make_space();
        s.set_pre_value();
        s._clauses[0].lia_literals = s._clauses[0].literals;
        s._solution[0] = 0;
        s._step = 1;
        s.initialize_lit_datas();
        s.initialize_clause_datas();
        s.critical_move(0, 1);
        require(s._lits[literal_idx].delta == 0, "each sampler must update its own literal storage");
    };
    ls_sampler small(0, 1), large(0, 1);
    move(small, 1);
    move(large, 30);
}

int main(int argc, char** argv) {
    try {
        require(argc == 2, "pass a test case name");
        const std::string name = argv[1];
        if (name == "complement_boundaries") complement_boundaries();
        else if (name == "complement_sides") complement_sides();
        else if (name == "complement_extremes") complement_extremes();
        else if (name == "equality_initialization") equality_initialization();
        else if (name == "paper_example") paper_example();
        else if (name == "partition_closures") partition_closures();
        else if (name == "bounded_reverse") bounded_reverse();
        else if (name == "coefficients_and_false_literals") coefficients_and_false_literals();
        else if (name == "negative_literal") negative_literal();
        else if (name == "fallback") fallback();
        else if (name == "oversized_model") oversized_model();
        else if (name == "equality_sampling_bounds") equality_sampling_bounds();
        else if (name == "empty_complement_fallback") empty_complement_fallback();
        else if (name == "equality_requires_conjunction") equality_requires_conjunction();
        else if (name == "feasible_interval_outside_sampling_domain") feasible_interval_outside_sampling_domain();
        else if (name == "missing_model") missing_model();
        else if (name == "boolean_model") boolean_model();
        else if (name == "boundary_move_interval") boundary_move_interval();
        else if (name == "boundary_move_singleton") boundary_move_singleton();
        else if (name == "boundary_move_wide_interval") boundary_move_wide_interval();
        else if (name == "parsed_integer_limits") parsed_integer_limits();
        else if (name == "unsupported_integer_is_reported") unsupported_integer_is_reported();
        else if (name == "overflowing_search_is_not_a_model") overflowing_search_is_not_a_model();
        else if (name == "independent_sampler_sizes") independent_sampler_sizes();
        else throw std::runtime_error("unknown test case");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
