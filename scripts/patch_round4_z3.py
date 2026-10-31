#!/usr/bin/env python3
"""R4 isolated source generation. Never edits R2/R3 sources or compiled trees."""
from common import *
import shutil,tempfile
stage=sys.argv[1];target=pathlib.Path(sys.argv[2]);assert stage in ('M','S')
with tempfile.TemporaryDirectory(prefix='round4-patch-') as tmp:
 root=pathlib.Path(tmp);subprocess.run([sys.executable,ROOT/'scripts/patch_round3_diagnostics.py',root],check=True);z=root/'z3/src'
 for name in ['a_shared.hpp','semantic_correspondence.hpp','declaration_identity.hpp'] :shutil.copyfile(ROOT/'include/round4'/name,z/'util'/name)
 p=z/'smt/a_internal_view.h';s=p.read_text().replace('#include "util/a_shared.hpp"','#include "util/a_shared.hpp"\n#include "util/declaration_identity.hpp"');s=s.replace('return std::string(to_app(e)->get_decl()->is_skolem()?"SKOLEM:":"")+std::string(1,sort(e))+(s.is_numerical()?"#":"$")+std::to_string(name.size())+":"+name;', 'return r4::declaration_identity(sort(e),s.is_numerical(),name,to_app(e)->get_decl()->is_skolem());');p.write_text(s)
 p=z/'smt/a_context.inc';s=p.read_text()
 s=s.replace('    unsigned encounter=0;', '''    if(!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_matched");r.count(m_A_call,r.version?"new_rule_after_first_model":"new_rule_version_zero");}
    unsigned encounter=0;''')
 s=s.replace('    std::map<unsigned,std::pair<uint64_t,uint64_t>> supports[2];', '''    if(!n.mapping_rule.empty()){
        a2::Json originals=a2::Json::array();for(auto const& o:entry.originals)originals.push_back({{"original_node_id",o.node},{"original_expression_fingerprint",o.fingerprint},{"canonical_negated",o.negated}});
        if(m_S&&!m_S->encounters.empty()){auto& rec=m_S->encounters.back();rec["mapping_atom_slot"]=m_S->refs.size();m_S->refs.push_back(e);rec["new_mapping_rule"]=n.mapping_rule;rec["originals"]=originals;rec["canonical_negated"]=n.negated;}
        bool demand=false,covered=false,unseen=false;for(auto const& rule:entry.rules){demand|=(rule.want_one|rule.want_zero)!=0;if(rule.node>=r.index->node_states.size())continue;auto const& state=r.index->node_states[rule.node];unseen|=!(state.first|state.second);covered|=(state.first&state.second)!=0;}
        r.count(m_A_call,demand?"new_rule_single_sided_demand":"new_rule_no_active_demand");if(unseen)r.count(m_A_call,"new_rule_two_sides_unseen");if(covered)r.count(m_A_call,"new_rule_has_covered_bits");
        r.event({{"kind","new_mapping_opportunity"},{"backend_call_id",m_A_call},{"decision_id",r.ordinal},{"native_var",native_var},{"native_expression_fingerprint",a2::r4::fingerprint(n.exact)},{"canonical_key",n.key},{"mapping_rule",n.mapping_rule},{"canonical_negated",n.negated},{"originals",originals},{"equivalence_scope","unconditional_integer_declaration_space"},{"coverage_version",r.version},{"single_sided_demand",demand},{"unassigned",true},{"native_selected",true},{"outside_window",outside_window}});
    }
    std::map<unsigned,std::pair<uint64_t,uint64_t>> supports[2];''')
 s=s.replace('    if(score[0]==score[1])', '    if(!n.mapping_rule.empty())r.count(m_A_call,score[0]==score[1]?"new_rule_support_tie":"new_rule_support_nontie");\n    if(score[0]==score[1])')
 s=s.replace('    ++r.suggestions;', '    if(!n.mapping_rule.empty()){r.count(m_A_call,"new_rule_advice");if(changed)r.count(m_A_call,"new_rule_override");}\n    ++r.suggestions;')
 s=s.replace('    event.mapping=exact?', '    event.extra={{"new_mapping_rule",n.mapping_rule},{"native_expression_fingerprint",a2::r4::fingerprint(n.exact)},{"equivalence_scope","unconditional_integer_declaration_space"}};\n    event.mapping=exact?')
 p.write_text(s)
 p=z/'util/a_state.h';s=p.read_text().replace(' int final_truth=-1;', ' Json extra=Json::object();\n int final_truth=-1;');s=s.replace(' return {{"query_id",query}', ' Json result={{"query_id",query}',1);s=s.replace('Json(final_truth!=0)}};}','Json(final_truth!=0)}};result.update(extra);return result;}');p.write_text(s)
 p=z/'model/semantic_trace.h';s=p.read_text().replace('row["encounters"]=encounters;', 'row["encounters"]=encounters;for(auto& rec:row["encounters"])if(rec.contains("mapping_atom_slot"))rec["actual_atom"]=ast(refs.get(rec["mapping_atom_slot"].get<unsigned>()));');p.write_text(s)
 if stage=='S':
  headers=ROOT/'include/round4/soft_reference'
  for name in ['a_shared.hpp','semantic_correspondence.hpp','declaration_identity.hpp','preference_types.hpp','reference_evaluation.hpp','phase_evidence.hpp']:shutil.copyfile(headers/name,z/'util'/name)
  p=z/'util/a_state.h';s=p.read_text().replace(' std::shared_ptr<const Index> index;', ' std::shared_ptr<const r4::QueryPreferences> preferences;std::set<std::string> preference_attempted,reference_attempted;\n std::shared_ptr<const Index> index;');s=s.replace(':index(p),query(q)',':preferences(p->preferences),index(p),query(q)');p.write_text(s)
  p=z/'smt/smt_context.h';s=p.read_text().replace('bool apply_A_phase_hint(', 'bool apply_S_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase);\n    bool apply_A_phase_hint(');p.write_text(s)
  p=z/'smt/a_context.inc';s=p.read_text();marker='bool context::apply_A_phase_hint(bool_var native_var,bool native_phase,bool& effective_phase) {';s=s.replace(marker,(ROOT/'src/round4/soft_phase.inc').read_text()+'\n'+marker+'\n    if(m_A&&m_A->preferences&&m_A->preferences->policy!=a2::r4::Policy::Legacy)return apply_S_phase_hint(native_var,native_phase,effective_phase);');p.write_text(s)
  p=z/'smt/semantic_context.inc';s=p.read_text().replace('m_S->watches.size()>=12','m_S->watches.size()>=(m_A&&m_A->preferences?64u:12u)');p.write_text(s)
 # Preserve concrete M sources as reviewable R4 copies; later S patch has its own file.
 for f in z.rglob('*'):
  if f.is_file():
   dest=target/'z3/src'/f.relative_to(z);dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists() or dest.read_bytes()!=f.read_bytes():shutil.copyfile(f,dest)
 print('R4',stage,'patch generated',target)
