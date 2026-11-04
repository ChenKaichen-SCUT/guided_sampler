"""Bound all braced sampler loops; leave disabled-budget decisions unchanged."""
import re
from prepare import ROOT,write,replace

def patch_mapping(dest):
    p=dest/'z3/src/smt/smt_context_pp.cpp';s=p.read_text()
    start=s.index('void context::expr_bool_var_map(');end=s.index('\nvoid context::print_clauses_vec',start)
    section=s[start:end]
    section=replace(section,'for (uint64_t i = 0; i < sz; i++) {','for (uint64_t i = 0; i < sz; i++) { expr_ccss::checkpoint();')
    section=replace(section,'for (unsigned j = 0; j < to_app(n)->get_num_args(); j++) {','for (unsigned j = 0; j < to_app(n)->get_num_args(); j++) { expr_ccss::checkpoint();')
    write(p,'#include "sampler/ccss_control.h"\n'+s[:start]+section+s[end:])

def patch(dest):
    patch_mapping(dest)
    header=dest/'z3/src/sampler/ccss_control.h';write(header,(ROOT/'kernel/ccss_control.h').read_text())
    p=dest/'z3/src/api/api_solver.cpp'
    write(p,'#include "sampler/ccss_control.h"\n'+p.read_text()+(ROOT/'kernel/ccss_api.inc').read_text())
    p=dest/'z3/src/smt/smt_context.cpp';s=p.read_text()
    s=replace(s,'                expr_bool_var_map(m_ls_sampler);',
        '                expr_ccss::phase(1);expr_ccss::checkpoint(true);\n                expr_bool_var_map(m_ls_sampler);\n                expr_ccss::phase(2);expr_ccss::checkpoint(true);')
    s=replace(s,'                if (m_ls_sampler->ls_sampling()) {','                expr_ccss::phase(4);expr_ccss::checkpoint(true);\n                if (m_ls_sampler->ls_sampling()) {\n                    expr_ccss::phase(5);expr_ccss::checkpoint(true);')
    write(p,'#include "sampler/ccss_control.h"\n'+s)
    p=dest/'z3/src/sampler/sampler.cpp';s=p.read_text()
    # Mask comments and strings before locating loop syntax. Inserting at the
    # opening brace works for nested/multiline conditions without reformatting.
    masked=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m[0]),s)
    positions=[]
    for m in re.finditer(r'\b(?:for|while)\s*\(',masked):
        i=m.end();depth=1
        while depth:
            if masked[i]=='(':depth+=1
            if masked[i]==')':depth-=1
            i+=1
        while masked[i].isspace():i+=1
        if masked[i]=='{':positions.append(i+1)
    for i in reversed(positions):s=s[:i]+' expr_ccss::checkpoint();'+s[i:]
    s=replace(s,'void ls_sampler::initialize() {','void ls_sampler::initialize() {\n    expr_ccss::phase_scope phase(3);')
    write(p,'#include "sampler/ccss_control.h"\n'+s)
    print('CCSS cooperative loop checkpoints:',len(positions))
