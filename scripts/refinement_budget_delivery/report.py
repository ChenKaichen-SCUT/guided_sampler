from common_bd import *
from runner import stream_rows
import statistics,collections
A=BASE/'analysis/audit_v1';seq=read(A/'sequences.json');events=read(A/'events.json');pre=read(A/'preprocess.json');real=read(A/'real_funnel.json');certs=read(A/'certificates.json');audit=read(A/'summary.json');cfg=read(ROOT/'configs/refinement_budget_delivery.json')
reportdir=ROOT/'docs/refinement_budget_delivery';analysis=BASE/'analysis';analysis.mkdir(exist_ok=True)
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(str(x) for x in r)+' |\n' for r in rows)+'\n'
def ms(x):return '未知' if x is None else f'{1000*x:.3f}'
def span(xs):return f'{ms(statistics.median(xs))} [{ms(min(xs))}, {ms(max(xs))}]' if xs else '无完成记录'
def stage_cpu(trace,name):return trace.get('stages',{}).get(name,{}).get('inclusive_cpu',0)
def canonical_events(stage,job):return stream_rows(BASE/stage/'frozen_v1'/job/'stream.jsonl')[0]
def accepted(e):return e['actually_delivered'] and e['candidate_gain']['covered']>e['native_gain']['covered']
formal=[s for s in seq if s['stage']=='offline'];probes=[s for s in seq if s['stage']=='probes'];main=[s for s in formal if s['instance']=='convert' and s['track']=='L2'];v3=[s for s in main if s['configuration']=='V3']
a1=any(s['counts'].get('complete_evaluations',0) for s in main);a2=any(accepted(e) for e in events if e['stage']=='offline' and e['instance']=='convert' and e['track']=='L2');common=None
for s in v3:
 p={e['position'] for e in events if e['sequence']==s['sequence'] and accepted(e)};common=p if common is None else common&p
a3=bool(common) and len(v3)==3;a4=len(v3)==3 and all(s['final_extra']>0 for s in v3);b2=any(r['B2'] for r in real);b3=any(r['B3'] for r in real);b1=all(r['verified'] for r in real if r['kind']=='original' and r.get('blocked')) and any(r.get('blocked') for r in real if r['kind']=='original')
gate={'A0':audit['passed'],'A1':a1,'A2':a2,'A3':a3,'A3_common_positions':sorted(common or []),'A4':a4,'B1':b1,'B2':b2,'B3':b3,'overall_online_Go':False,'historical_cpu_credit_proven':False}
write(analysis/'gate.json',gate)
lines=['# convert 原预算交付与 real 方向阻塞：限定离线结果\n',f'本轮完成固定代码修改、Release/ASan/UBSan 正确性及原生隔离验证、4 个 convert 冷探针、22 条正式离线序列和 4 个 real 诊断 worker。43 个源模型共重放 518 个正式事件；没有新真实采样、真实 solver check、HighDiv 重跑、在线短会话、900 秒矩阵、追加 seed 或 B。基点 `{cfg["base"]}`，源码冻结 `{read(MAN/"implementation.json")["commit"]}`，分支 `refinement-budget-delivery`。\n',f'任务 A 分层：A0={gate["A0"]}，A1={a1}，A2={a2}，A3={a3}（共同位置 {sorted(common or [])}），A4={a4}。任务 B：B1={b1}，B2={b2}，B3={b3}。整体在线算法仍不自动 Go；`historical_cpu_credit_proven=false`，不能声称已满足原生 CPU 10% 双信用或低于重新求解成本。\n', '## 1. 实现与验证\n','V0 保留 ValueCache；V1 以一次行槽、epoch/touched 做稀疏全等式验证；V2 在确定旧方向池后批量传播四字位集；V3 按完全相同的影响签名分组，并在事件入口对当前实际输出历史事务式同步 covered 分数。全部强制等式义务保留；未触及的行因方向支持与行系数无交集而结构上为零。x-x、未选分支、共享 DAG、Bool 和原 AST 身份均保留。hard AST 使用自己的影响节点空间。\n','四配置正式实验统一 FirstCovered、96/18 ms 算法软截止和 100/20 ms 最终上限；这项停止策略是显式算法变化，缓存/稀疏/位集/精确评分属于等价成本修复。AuditAll 探针关闭早停；固定工作量合成测试也关闭时限及早停，逐项比较元数据、方向、affected、分数、顺序、目标、区间、参数、赋值、实际观察、保护、得分和选择。不能将四配置差值直接归于 FirstCovered，也没有额外正式停止消融来量化其独立性能贡献。\n','两种构建通过 244612 算术、1356 模命中、7938 域点、4 方向系统、32 官方观察检查；新增独立核验 304 次合成候选、17 份完整域证书，68 份损坏证书全部拒绝。测试覆盖 epoch 清理取消恢复、深链/共享 DAG、评分身份/取消发布、真实 hard 条件、17+4 ms 收尾回退、19 ms 搜索软截止、二向协调/整数取整/远 OR 分支/三向才可移动例。四配置原生隔离均实际发生替代，保持完整 map、m_ls、RNG、参考、反馈、路由和原生计数；关闭行为与保存的基线一致。\n',f'真实独立审计：官方访问核验调用 {audit["official_audit_calls"]} 次，涉及 {audit["distinct_formula_assignment_objects"]} 个不同公式—完整赋值对象；完整候选核验 {audit["complete_candidate_audits"]} 次，完整域证书 {audit["complete_certificates"]} 份。以上与 43 个源模型区分。22 条正式输出及原生序列各运行冻结官方 wire_coverage 脚本；完整输出前缀都保留原生观察。\n','## 2. 冷预处理与重复工作\n']
lines.append(table(['轨道/实例','配置','重复','CPU ms','墙钟 ms','冷合格','状态'],[[s['stage']+'/'+s['instance'],s['configuration'],s['repeat'],ms(s['preprocess_cpu']),ms(s['preprocess_wall']),s['preprocess_eligible'],s['preprocess_status']] for s in seq]))
stages=[];compression=[]
for s in probes:
 rs=canonical_events('probes',s['sequence']);p=next((r for r in rs if r['kind']=='preprocess'),None);m=next((r['metadata'] for r in rs if r['kind']=='metadata'),None)
 if p:
  for name,r in p['trace']['stages'].items():stages.append({'sequence':s['sequence'],'configuration':s['configuration'],'stage':name,**r})
 if m:
  compression.append({'configuration':s['configuration'],'directions':len(m['directions']),'affected_entries':sum(len(d['affected']) for d in m['directions']),**m.get('score_index',{})})
lines.append(table(['配置','完整行槽初始化','全行扫描次数','触及行数','乘加数','位集 OR','affected 字节槽'],[[p['configuration'],p['verify_slots'],p['verify_full_scans'],p['verify_touched'],p['verify_multiply_adds'],p['influence_ors'],p['affected_storage_bytes']] for p in pre if p['stage']=='probes']))
lines.append(table(['配置','阶段','exclusive CPU ms','exclusive 墙钟 ms','完成/未完成'],[[r['configuration'],r['stage'],ms(r['exclusive_cpu']),ms(r['exclusive_wall']),f'{r["completed"]}/{r["incomplete"]}'] for r in stages]))
lines.append(table(['配置','方向','affected 条目','签名组','组—方向条目'],[[r['configuration'],r['directions'],r['affected_entries'],r.get('groups','不适用'),r.get('compressed_group_direction_entries','不适用')] for r in compression]))
lines+=['同一新二进制、同一记录策略的 V0–V3 才是本轮配对对照。上轮 ValueCache/Shared 单次 convert 依赖分别 36.277/4.735 ms、affected 14.085/75.173 ms、完整预处理 124.314/148.848 ms，只作为历史背景，不据跨冻结版本的墙钟比值宣称精确加速。表中被截止的工作属于删失，不是完整耗时。方向验证总行、槽、触及行与乘加分别记录；位集和 affected 内存为容器槽容量，完整峰值看 worker RSS。\n','## 3. 排名、候选与交付\n']
rank=[]
for e in events:
 if e['stage']=='probes' or e['instance']=='convert' and e['configuration']=='V3' and e['position'] in [2,3,4,5]:
  w=e['cost_trace']['work'];rank.append([e['sequence'],e['position'],ms(stage_cpu(e['cost_trace'],'RankDirections')),w['rank_sync_nodes'],w['changed_covered_bits'],w['dirty_groups'],w['score_updates'],e['completed_evaluations'],ms((e['first_complete'] or {}).get('cpu')),ms((e['first_preserved_covered'] or {}).get('cpu')),ms(e['delivery_ready_cpu']),ms(e['event_total_cpu']),e['actually_delivered'],e['delivery_rejection'] or e['cancellation'] or e['reason']])
lines.append(table(['序列','位置','排名 CPU ms','同步节点','变化bit','脏组','评分更新','评价','首完成 CPU ms','首保护增益 CPU ms','ready CPU ms','事件 CPU ms','实际交付','停止/拒绝'],rank))
lines+=['所有首次时间从事件可选工作入口累计，不是候选内部计时；完整原式合法性、官方观察、保护差集和评分先完成，保存赋值/完整观察后才可能交付。序列化、全部候选日志写出、临时对象清理、staging 账本复制、外层记录和回滚均计费。proposal 非最终输出；超时恢复原生交付，再以真实历史运行下一事件。详细每位置 CPU/墙钟、首次方向/参数、全部缺失观察、分数、分阶段成本和尾部见归档 events.json 与 stream.jsonl。\n','## 4. 22 条正式序列：三次重复全部保留\n']
lines.append(table(['序列','完整评价','预算可交付','实际替代','严格 covered 交付','终点额外 covered','可选 CPU/墙钟 ms','进程 CPU/墙钟 ms','RSS KiB'],[[s['sequence'],s['counts'].get('complete_evaluations',0),s['counts'].get('budget_eligible',0),s['counts'].get('actual_replacements',0),s['counts'].get('strict_covered_deliveries',0),s['final_extra'],ms(s['optional_cpu'])+'/'+ms(s['optional_wall']),ms(s['terminal']['user_cpu']+s['terminal']['system_cpu'])+'/'+ms(s['terminal']['parent_wall']),s['terminal']['max_rss_kb']] for s in formal]))
for mode in ['V0','V1','V2','V3']:
 ss=[s for s in main if s['configuration']==mode];good=[s for s in ss if s['preprocess_eligible']];lines.append(f'{mode} convert L2 三次合格预处理 CPU 中位/范围 ms：{span([s["preprocess_cpu"] for s in good])}；墙钟：{span([s["preprocess_wall"] for s in good])}；未合格 {len(ss)-len(good)} 次单列，不计完成中位数。\n')
lines+=['L1 后续历史始终是原生前缀，预算合格仅表示假设可交付；L2 才使用真实预算决定后的输出历史。首模型原样交付。完整前缀曲线在 analysis/audit_v1/prefixes.csv：局部替代 covered 增益与终点差值分开，原生后续可能补齐前缀新增 bit。后续 L2 机会不能强求与旧位置 3 的 +43 完全相同。\n','旧 +43 只读 fixture 在两种构建的独立审计中均合法、保护 1049 个观察完整、covered 多 43。生产选择器不读此 fixture、不按实例名/位置/方向 186/参数 3 指定快路径。若本轮原预算没有重新找到，fixture 仍不能算本轮发现。\n','## 5. real 完整域与有限协调诊断\n']
summary_rows=[]
for pos in [2,3,4,5]:
 for kind in ['original','combination']:
  xs=[r for r in real if r['position']==pos and r['kind']==kind];summary_rows.append([pos,kind,len(xs),sum(r['root_complete'] for r in xs),sum(r['certificate_complete'] for r in xs),sum(r['verified'] for r in xs),sum(r.get('blocked',False) for r in xs),sum(r.get('nonzero_domain_found',False) for r in xs),sum(r.get('legal_witness_verified',False) for r in xs),sum(r.get('preserved',False) for r in xs),sum(r.get('covered_gain',False) for r in xs),sum(r['B2'] for r in xs),sum(r['B3'] for r in xs)])
lines.append(table(['位置','类别','记录','完整根域','完整证书','独立核验','{0}','非零域','合法见证','保护','覆盖增益','B2','B3'],summary_rows))
lines+=['完整原子算术、节点作用域、完整 Bool DAG 推导和组合逐条结果见 real_blocking.zh.md 与归档证书。合法域先于保护；完整域为 {0} 时，不能把不能移动归因为观察保护。组合结果只对预登记的有限二方向集合有效，失败不能推出没有三向协调、其他模型或全局无解。原池重合方向不算新增组合首次解除阻塞。\n','## 6. 成本边界、失败与结论限制\n','每 worker 冷启动清空模型值缓存、重新生成方向池/索引/评分状态，未清操作系统页缓存。正式计时顺序执行、绑定逻辑 CPU 0（物理 core 0，sibling 0–1）；没有与本任务编译/归档/上传/real 诊断重叠，也不宣称宿主完全独占。全部 CPU/墙钟、失败尾部和父进程 wait4/pidfd 成本保留，调度超限没有自动重跑。\n','末尾成本记录无法计量自己的最终写出；父进程完整 CPU/墙钟补充，不能填 0。摘要序列化单列 summary tail；event postlude 与测量余量单列，临界无法确认时保守回退 budget_eligibility_unknown。容器字节是槽存储与证书保守额度，不是所有 BigInt 动态堆的精确快照；RSS 为整进程高水位。仍缺历史逐模型原生 CPU 信用，没有本轮 oracle，也没有重新求解成本估计。\n','保留了空组取消检查测试失败、测试 JSON 期望格式错误、构建 -B 触发已有依赖占位目标失败，以及源码仍在复核时被“编译期间源码变化”检查拒绝的构建。均在真实探针开始前修复或完成最终一致构建；失败目录未删除。工具会话重启中断 SAN 审计时，复用已经完成的机制证据，只继续未完成测试；不重跑真实探针。所有正式 worker 尝试目录拒绝覆盖。\n','全部工件保存在 results/refinement_budget_delivery；可恢复归档、成员 SHA 和验证见 archives/refinement_budget_delivery/RESTORE.md；源/生成文件/二进制/动态库/输入/官方脚本身份见 manifests/refinement_budget_delivery。分支正常提交推送并由 git ls-remote 核对最终完整 SHA，发布收据在 build/refinement-budget-delivery-publish-receipt.json。\n']
(reportdir/'results.zh.md').write_text('\n'.join(lines))
r=['# real：完整整数域、作用域和有限二方向组合\n','本诊断独立使用原生位置 2/3/4/5 及旧 ValueCache 选定的 16 方向，不读取 convert 候选，也不向正式 L2 注入任何结果。证书审计独立从原 AST/anchor/完整方向重建仿射项与全部 Bool 区间，未调用 C++ LineDomain 或真实 solver。原式根域含 0；额外真实硬条件为 none。\n',table(['位置','类别','记录','完整根域','完整证书','独立核验','{0}','非零域','合法见证','保护','覆盖增益','B2','B3'],summary_rows)]
roles=collections.Counter((b['scope'],role) for c in certs if c['kind']=='original' and c.get('blocked') for b in c['blockers'] for role in b['roles'])
r.append(table(['作用域','边界类型','证书中的原子出现次数'],[[scope,role,count] for (scope,role),count in sorted(roles.items())]))
r.append('计数是每份 anchor—direction 证书的原子出现次数，不是不同原约束数。下列摘要不是最小约束核；完整共享 DAG 的交/并/补证明才排除所有非零整数。必需 AND 路径与 OR/NOT 等条件作用域分开，不把局部分支等式当作全局强制等式。正 slack 而 floor/ceil 产生 0 边界时称“整数取整参与阻塞”，不称其唯一原因。\n')
examples=[]
for pos in [2,3,4,5]:
 xs=[c for c in certs if c['position']==pos and c['kind']=='original' and c.get('blocked')]
 for c in xs[:2]:
  r.append(f'## 位置 {pos}，原方向 {c["direction_id"]}\n\n完整根域为 {c["domain"]}，独立证书核验通过。相关边界（全部仍见归档）：\n')
  r.append(table(['原节点','作用域','角色','规范化 c','斜率 s','域','floor(-c/s)','ceil(-c/s)'],[[b['node'],b['scope'],','.join(b['roles']),b['constant'],b['slope'],b['before_distinct_complement'],b.get('floor'),b.get('ceil')] for b in c['blockers'][:16]]))
  examples.append({'position':pos,'direction':c['direction_id'],'blockers':c['blockers']})
r.append('## 全部有限组合结果\n')
r.append(table(['位置','请求','状态','根域','独立核验','请求内','原池重合','合法','保护','增益','B2','B3'],[[x['position'],x['ordinal'],x['status'],x.get('domain','未完成'),x['verified'],x['within_request_cap'],x['already_in_pool'],x.get('legal_witness_verified',False),x.get('preserved',False),x.get('covered_gain',False),x['B2'],x['B3']] for x in real if x['kind']=='combination']))
r.append('两个原方向都经完整域证书证明 {0}，且该组合在本诊断额度内完成合法非零见证，才记 B2；还需保护通过并严格增 covered 才记 B3。原池重合、零向量、重复、incomplete、unsupported、证书不完整、预算不合格全部保留。有限组合的负结果不能推出原公式唯一可满足或更高阶方向无效。\n')
(reportdir/'real_blocking.zh.md').write_text('\n'.join(r))
write(analysis/'blocking_examples.json',examples);write(analysis/'summary.json',{'gate':gate,'audit':audit,'formal_sequences':formal,'probe_sequences':probes,'group_compression':compression,'real_funnel':summary_rows})
csvwrite(analysis/'preprocess_stages.csv',stages);csvwrite(analysis/'sequences.csv',[{k:v for k,v in s.items() if k not in ['counts','terminal','summary_tail']}|s['counts']|{k:s['terminal'][k] for k in ['user_cpu','system_cpu','parent_wall','max_rss_kb','external_timeout']} for s in seq]);print('reports generated',gate,flush=True)
