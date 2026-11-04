#pragma once
#include "ast/ast.h"
#include <memory>
#include <cstdint>
#include <unordered_set>
#include <functional>

namespace expr_soft {
struct request {
    ast_manager* manager;
    expr_ref_vector goals;
    expr_ref_vector working_goals;
    expr_ref_vector definitions;
    std::function<void()> cleanup;
    expr_ref_vector auxiliary_refs;
    std::unordered_set<func_decl*> auxiliary;
    void* owner = nullptr;
    unsigned next = 0;
    unsigned window = 64;
    unsigned decisions = 0;
    uint64_t prepared = 0, chosen = 0, already_true = 0, already_false = 0;
    uint64_t auxiliary_map_skips = 0, window_skips = 0;
    uint64_t tactic_routes = 0, incremental_routes = 0, mapped = 0, mapping_failures = 0;
    bool mapping_ok = true;
    explicit request(ast_manager& m): manager(&m), goals(m), working_goals(m), definitions(m), auxiliary_refs(m) {}
};
inline std::shared_ptr<request>& active() {
    static thread_local std::shared_ptr<request> value;
    return value;
}
inline request* for_manager(ast_manager& m) {
    auto& r = active();
    return r && r->manager == &m ? r.get() : nullptr;
}
inline bool exclude_from_native_exchange(ast_manager& m, func_decl* declaration) {
    auto* r=for_manager(m);
    if (!r || !r->auxiliary.count(declaration)) return false;
    ++r->auxiliary_map_skips;
    return true;
}
}
