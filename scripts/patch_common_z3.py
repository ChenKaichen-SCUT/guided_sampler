#!/usr/bin/env python3
import pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];tree=pathlib.Path(sys.argv[1]);p=tree/'z3/src/smt/smt_context.cpp';s=p.read_text()
if 'HIGHDIV_NATIVE_DECISION_TRACE' not in s:
    old='    assign(l, b_justification::mk_axiom(), true);\n    return true;\n}'
    assert old in s;s=s.replace(old,(ROOT/'tests/native_trace.inc').read_text()+old,1);p.write_text(s)
p=tree/'z3/src/solver/combined_solver.cpp';s=p.read_text()
if 'HIGHDIV_ROUTE_LOG' not in s:
    s='#include <fstream>\n#include <cstdlib>\n'+s
    s=s.replace('class combined_solver : public solver {','class combined_solver : public solver {\n'+(ROOT/'src/common_route.inc').read_text(),1)
    s=s.replace('    lbool check_sat_core(unsigned num_assumptions, expr * const * assumptions) override {','    lbool check_sat_core(unsigned num_assumptions, expr * const * assumptions) override {\n        ++m_round1_route_epoch;',1)
    for old,backend in [('            return m_solver2->check_sat_core(num_assumptions, assumptions);','smt'),('                lbool r = m_solver2->check_sat_core(num_assumptions, assumptions);','smt'),('                    r = m_solver2->check_sat_core(num_assumptions, assumptions);','smt'),('        return m_solver1->check_sat_core(num_assumptions, assumptions);','tactic')]:
        assert old in s;indent=old[:len(old)-len(old.lstrip())];s=s.replace(old,indent+f'round1_route("{backend}");\n'+old,1)
    p.write_text(s)
