// Exercise the actual hybrid sampler and modified Z3 API, without test hooks.
#include "sampler/liasampler.h"

#include <fstream>
#include <stdexcept>

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main(int argc, char** argv) {
    try {
        require(argc == 3, "pass a case and output path");
        z3::context ctx;
        const std::string name = argv[1];
        if (name == "distinct_samples") {
            sampler::LiaSampler s(&ctx, "", "", 10, 1, 0);
            std::ofstream out(argv[2]);
            s.curr_sample = {{"x", "0"}};
            s.print_unique_sample(out);
            // These distinct integers collide in the old polynomial fingerprint.
            s.curr_sample = {{"x", "2305843009213693951"}};
            s.print_unique_sample(out);
            require(s.num_samples == 2, "different assignments must not be discarded on hash collision");
            s.curr_sample = {{"x", "0"}};
            s.print_unique_sample(out);
            require(s.num_samples == 2, "identical assignments must still be deduplicated");
        } else if (name == "ls_false") {
            z3::params p(ctx);
            p.set("ls_sampling", true);
            p.set("auto_config", false);
            p.set("logic", "QF_LIA");
            auto s = z3::with(z3::tactic(ctx, "smt"), p).mk_solver();
            s.add(ctx.bool_val(false));
            require(s.check() == z3::unsat, "LS must respect a contradiction discovered during internalization");
        } else if (name == "ls_boolean_model") {
            z3::params p(ctx);
            p.set("ls_sampling", true);
            p.set("auto_config", false);
            p.set("logic", "QF_LIA");
            auto s = z3::with(z3::tactic(ctx, "smt"), p).mk_solver();
            auto b = ctx.bool_const("b");
            s.add(b);
            require(s.check() == z3::sat, "a Boolean unit is satisfiable");
            auto model = s.get_model();
            require(model.eval(b, true).is_true(), "LS model must contain the asserted Boolean unit");
        } else {
            throw std::runtime_error("unknown test case");
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
