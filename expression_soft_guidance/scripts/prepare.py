"""Verify and copy fixed HighDiv files, then apply only this experiment's patch."""
import hashlib,json,pathlib,shutil,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parent
CHANGED=['src/smt/smt_context.cpp','src/api/api_solver.cpp','src/smt/smt_model_generator.cpp',
         'src/solver/combined_solver.cpp','src/solver/tactic2solver.cpp','src/smt/tactic/smt_tactic_core.cpp',
         'src/ast/converters/model_converter.h','src/ast/converters/model_converter.cpp',
         'src/ast/converters/generic_model_converter.h','src/ast/converters/generic_model_converter.cpp','src/sampler/sampler.cpp','src/smt/smt_context_pp.cpp']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8',newline='\n')
def replace(s,old,new,count=1):
    assert s.count(old)==count,(old[:80],s.count(old),count)
    return s.replace(old,new)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--destination',required=True);ap.add_argument('--repatch',action='store_true');args=ap.parse_args()
    dest=pathlib.Path(args.destination).resolve()
    if args.repatch:
        previous=json.loads((ROOT/'build/prepare.json').read_text())
        assert dest==pathlib.Path(previous['destination']).resolve()
    else: assert not dest.exists(),'new exclusive build directory required'
    up=WORKSPACE/'HighDiv-master'
    manifest=json.loads((WORKSPACE/'guided_sampler/manifests/upstream.json').read_text())
    checked={}
    for e in manifest['files']:
        p=up/e['path'];assert sha(p)==e['sha256'],str(p)
        checked[e['path']]=e['sha256']
    for name in checked:
        if args.repatch and name not in ['z3/'+p for p in CHANGED]:continue
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(up/name,p)
    shutil.copyfile(ROOT/'kernel/expr_soft.h',dest/'z3/src/smt/expr_soft.h')
    path=dest/'z3/src/smt/smt_context.cpp';s=path.read_text()
    s='#include "smt/expr_soft.h"\n'+s
    anchor='            internalize_assertions();\n            add_theory_assumptions(asms);'
    s=replace(s,anchor,'            internalize_assertions();\n'+(ROOT/'kernel/prepare.inc').read_text()+'            add_theory_assumptions(asms);',2)
    anchor='        internalize_assertions();\n    } catch (cancel_exception&)'
    s=replace(s,anchor,'        internalize_assertions();\n'+(ROOT/'kernel/prepare.inc').read_text()+'    } catch (cancel_exception&)')
    anchor='    bool_var var;\n    bool is_pos;\n    bool used_queue = false;'
    s=replace(s,anchor,(ROOT/'kernel/decide.inc').read_text()+anchor)
    write(path,s)
    path=dest/'z3/src/api/api_solver.cpp'
    write(path,'#include "smt/expr_soft.h"\n'+path.read_text()+(ROOT/'kernel/api.inc').read_text())
    path=dest/'z3/src/smt/smt_model_generator.cpp';s=path.read_text()
    anchor='                m.last_CDCL_model[d->get_name().str()] = var_val_stream.str();'
    s=replace(s,anchor,'                if (!expr_soft::exclude_from_native_exchange(m,d))\n    '+anchor)
    write(path,'#include "smt/expr_soft.h"\n'+s)
    path=dest/'z3/src/solver/combined_solver.cpp';s=path.read_text()
    # Native routing logic is untouched. Scope only the selected incremental
    # backend, and retain its model until the host finishes consuming it.
    s=s.replace('m_solver2->check_sat_core(num_assumptions, assumptions)', 'expr_soft_check_incremental(num_assumptions, assumptions)')
    anchor='    lbool check_sat_core(unsigned num_assumptions, expr * const * assumptions) override {'
    helper='''    lbool expr_soft_check_incremental(unsigned n, expr* const* assumptions) {
        if (auto* r = expr_soft::for_manager(get_manager())) {
            ++r->incremental_routes;
            r->owner = nullptr;
            r->mapping_ok = true;
            r->working_goals.reset(); r->working_goals.append(r->goals);
            if (!r->definitions.empty() && !r->cleanup) {
                m_solver2->push();
                r->cleanup = [s = ref<solver>(m_solver2)]() { s->pop(1); };
                for (expr* d : r->definitions) m_solver2->assert_expr(d);
            }
        }
        return m_solver2->check_sat_core(n, assumptions);
    }
'''
    s=replace(s,anchor,helper+anchor)
    s=replace(s,'        return m_solver1->check_sat_core(num_assumptions, assumptions);',
              '        if (auto* r = expr_soft::for_manager(get_manager())) ++r->tactic_routes;\n        return m_solver1->check_sat_core(num_assumptions, assumptions);')
    write(path,'#include "smt/expr_soft.h"\n'+s)
    path=dest/'z3/src/solver/tactic2solver.cpp';s=path.read_text()
    anchor='    for (unsigned i = 0; i < num_assumptions; i++) {\n        proof_ref pr'
    s=replace(s,anchor,'    if (auto* r = expr_soft::for_manager(m))\n        for (expr* d : r->definitions) g->assert_expr(d);\n'+anchor)
    write(path,'#include "smt/expr_soft.h"\n'+s)
    path=dest/'z3/src/smt/tactic/smt_tactic_core.cpp';s=path.read_text()
    anchor='                    goal_ref_buffer& result) override {\n        try {'
    s=replace(s,anchor,'                    goal_ref_buffer& result) override {\n'+(ROOT/'kernel/tactic.inc').read_text()+'        try {')
    write(path,'#include "smt/expr_soft.h"\n'+s)
    # Forward transport is opt-in for converter types with known semantics.
    path=dest/'z3/src/ast/converters/model_converter.h';s=path.read_text()
    s=replace(s,'    virtual void operator()(model_ref & m) = 0;',
              '    virtual bool expr_soft_rewrite(expr_ref&) { return false; }\n    virtual void operator()(model_ref & m) = 0;')
    write(path,s)
    path=dest/'z3/src/ast/converters/model_converter.cpp';s=path.read_text()
    anchor='    void operator()(model_ref & m) override {\n        this->m_c2'
    s=replace(s,anchor,'''    bool expr_soft_rewrite(expr_ref& e) override {
        return m_c1->expr_soft_rewrite(e) && m_c2->expr_soft_rewrite(e);
    }
'''+anchor)
    write(path,s)
    path=dest/'z3/src/ast/converters/generic_model_converter.h';s=path.read_text()
    s=replace(s,'    void operator()(model_ref & md) override;',
              '    bool expr_soft_rewrite(expr_ref& e) override;\n    void operator()(model_ref & md) override;')
    write(path,s)
    path=dest/'z3/src/ast/converters/generic_model_converter.cpp';s=path.read_text()
    s+='''
bool generic_model_converter::expr_soft_rewrite(expr_ref& e) {
    expr_safe_replace replace(m);
    for (entry const& instruction : m_entries) {
        if (instruction.m_instruction == HIDE) continue;
        if (instruction.m_f->get_arity() != 0) return false;
        expr_ref variable(m.mk_const(instruction.m_f), m);
        replace.apply_substitution(variable, instruction.m_def, e);
    }
    th_rewriter rewrite(m); rewrite(e);
    return true;
}
'''
    write(path,s)
    from patch_ccss import patch
    patch(dest)
    out={'upstream_commit':manifest['commit'],'verified_files':len(checked),'destination':str(dest),
         'upstream':checked,'kernel_files':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'kernel').iterdir()},
         'changed_z3_files':CHANGED+['src/smt/expr_soft.h','src/sampler/ccss_control.h'],
         'no_previous_guidance_or_refinement_patches':True}
    write(ROOT/'build/prepare.json',json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['upstream','kernel_files']},indent=2))
if __name__=='__main__':main()
