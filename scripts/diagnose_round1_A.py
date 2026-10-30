#!/usr/bin/env python3
"""Read and hash frozen round-one evidence, never launch a sampler."""
import collections,csv,json
from common import ROOT,read,write,digest
BASE='fc19bd22609295ed405e1ac96bf35d695c42832a'
def main():
 out=ROOT/'results/round2_a/diagnosis_before';out.mkdir(parents=True,exist_ok=True)
 plan=read(ROOT/'manifests/plan.json');paths={r['id']:ROOT/r['output'] for r in plan['runs']}
 rows=[];routes=[];verified={}
 for r in read(ROOT/'results/audit_summary.json')['runs']:
  if r['config']!='a_only':continue
  d=paths[r['id']];manifest=read(d/'artifact_hashes.json')
  p=d/'queries.audited.jsonl';assert digest(p)==manifest[p.name];verified[str(p.relative_to(ROOT))]=manifest[p.name]
  c=collections.Counter()
  with p.open() as f:
   for line in f:
    q=json.loads(line)
    if q['source']!='CDCL':continue
    c['checks']+=1;c['fallback']+=q['actual_fallback']
    for b in q['actual_backend_path']:c[b]+=1
  g=r['guidance'];w=r['window']
  row={'id':r['id'],'input':r['input'],'mode':r['mode'],'selected_distinct_targets':r['distinct_targets'],'window_occurrences':w.get('Bool',0)+w.get('Int',0),'static_matching_window_occurrences':w.get('a_static_match',0),'binding_occurrences':g['a_live'],'suggestions':g['a_used'],'overrides':g['a_changed'],'unsupported_checks':g['unsupported'],'explicit_seconds':r['costs']['explicit_seconds']}
  for field in ['assigned','unassigned','native_not_selected','outside_window_potential','normalization_loss','within_window_native_matches','quota_rejected']:row[field]='not_recorded'
  rows.append(row);routes.append({'id':r['id'],**dict(c),'suggestions':g['a_used'],'CDCL_models':r['source_models'].get('CDCL',0),'CCSS_models':r['source_models'].get('CCSS',0),'actual_tactic_leaf':'not_recorded'})
 for name,data in [('old_a_funnel.csv',rows),('old_route_summary.csv',routes)]:
  fields=list(dict.fromkeys(k for r in data for k in r))
  with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(data)
 write(out/'missing_evidence.json',{'frozen_commit':BASE,'not_recorded':['assignment-state snapshots','actual tactic leaf and setup_and_check entry','native atom encounters and canonicalization','per-target backtrack tokens','window versus quota opportunity loss'],'prohibitions':['No inference of assignment from a_live','No inference of decision from final SAT','No rerun of round-one sampling']})
 write(out/'verified_evidence.json',{'frozen_commit':BASE,'files':verified,'baseline_frozen_sha256':digest(ROOT/'results/baseline_seed0_v1/BASELINE_FROZEN.json'),'read_only':True,'sampler_invocations':0})
 (out/'root_cause_hypotheses.zh.md').write_text('''# 第一轮A失效证据分解\n\n已证事实：16项A-only均没有建议或相位改变。Bromberger、prime_cone有实际绑定但未使用；CAV、dillig、pb2010没有实际绑定。convert有少量绑定。SMT_random和SMT_real的主动查询元数据被标为不支持，仍有准备开销。逐项计数见两张CSV。\n\n源码证据：旧combined_solver只向solver2传递；临时tactic内核及setup_and_check没有A入口。旧A先选择8个单侧bit才找映射，且要求原表达式在搜索前已internalized。旧目录会构造交换等式。\n\n尚未证实的假设：全局8位窗口与原生选原子错开、重写导致原子身份不同、绑定原子已传播赋值、原生64决策窗口遗漏。旧日志不能量化各自损失，也不能把未匹配直接称为被消元。第二轮以只读规范化、真实叶子跟踪和有限绑定快照区分这些情况。\n\n本步骤没有执行任何采样器，也没有修改第一轮证据。\n''')
 print('Read-only diagnosis:',len(rows),'runs; all consumed query logs hash-verified')
if __name__=='__main__':main()
