#include "sampler.h"

namespace sampler {

void Sampler::safe_exit(int exitcode) {
    if (exitcode) {
        result = "failure";
    } else {
        result = "success";
    }
    exit(exitcode);
}

void Sampler::_compute_formula_stats_aux(z3::expr e, int depth) {
    if (sup.find(e) != sup.end())
        return;                                            
    assert(e.is_app());                                    
    z3::func_decl fd = e.decl();                          
    if (e.is_const()) {                                  
        std::string name = fd.name().str();
        if (var_names.find(name) == var_names.end()) {
            var_names.insert(name);
            variables.push_back(fd);
            variable_names.push_back(name);
            if (fd.range().is_array()) {
                ++num_arrays;
            } else if (fd.is_const()) {
                switch (fd.range().sort_kind()) {
                    case Z3_BV_SORT:
                        ++num_bv;
                        num_bits += fd.range().bv_size();
                        break;
                    case Z3_BOOL_SORT:
                        ++num_bools;
                        ++num_bits;
                        break;
                    case Z3_INT_SORT:
                        ++num_ints;
                        break;
                    case Z3_REAL_SORT:
                        ++num_reals;
                        break;
                    default:
                        std::cout << "Invalid sort\n";
                        safe_exit(1);
                }
            }
        }
    } else if (fd.decl_kind() == Z3_OP_UNINTERPRETED) {
        std::string name = fd.name().str();
        if (var_names.find(name) == var_names.end()) {
            var_names.insert(name);
            // std::cout << "declaration: " << fd << '\n';
            variables.push_back(fd);
            ++num_uf;
        }
    }
    sup.insert(e);
    if (depth > max_depth) {
        max_depth = depth;
    }
    for (size_t i = 0; i < e.num_args(); ++i) {
        _compute_formula_stats_aux(e.arg(i), depth + 1);
    }
}

void Sampler::parseSmtFile() {
    z3::expr_vector formulas = c.parse_file(smtFilePath.c_str());
    original_formula = mk_and(formulas);

#ifdef DEBUG
    _compute_formula_stats_aux(original_formula);
    std::cout << "AST depth: " << max_depth << std::endl;
#endif
}
};