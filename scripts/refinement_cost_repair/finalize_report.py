"""Post-audit interpretation only; does not change the frozen implementation."""
from common_cr import *
p=ROOT/'docs/refinement_cost_repair/results.zh.md';s=p.read_text();distinct=read(BASE/'analysis/distinct_assignments.json');assert distinct['total_distinct_formula_assignment_pairs']==113
s=s.replace('190 个唯一赋值的官方访问轨迹','190 次官方访问轨迹核验（覆盖 113 个不同的“公式、完整赋值”对象，含原生及离线候选；真实来源仍为 43 模型）')
s=s.replace('NumericValues 调用','NumericValues 阶段调用')
s=s.replace('## 2. 固定诊断探针：上轮究竟卡在哪里','''审计计数口径：冻结审计脚本的 `unique_official_assignments_checked` 字段实际上计 LRU 未命中后的核验次数，逐序列复查和缓存淘汰会重复核验；不能将 190 当作不同模型数。独立按公式及完整赋值去重结果为 convert 95、random 8、real 10，共 113 个对象，见 `analysis/distinct_assignments.json`。没有更改冻结脚本或原日志来掩盖这个命名边界。

## 2. 固定诊断探针：上轮究竟卡在哪里''')
s=s.replace('## 3. 主 L2 三次重复：成本与收益分开','''单次数值诊断的具体解释：ValueCache 与 Shared 都让 convert 的四位置完成 64 个域、real 完成 64 个域；旧配置在相同诊断上限均未完成第一个域。NumericValues 的整数组扫描从旧路径的千万级要求槽数降为 0，新路径每 anchor 的值槽和仿射常数槽仍分别分配并计费；上表 NumericValues 的调用还包含四次冷初始化，不能拿调用数直接当作相同工作量。

**Shared 没有带来总体预处理降本。** convert 的依赖阶段从本阶段 ValueCache 的 36.277 ms 降到 4.735 ms，但 affected 构造从 14.085 ms 升到 75.173 ms，抵消并超过前项节省；整个已完成的诊断冷预处理为 124.314 vs 148.848 ms CPU。这个对照只有一次，不能声称普遍精确加速/退化倍数。主 L2 的 real 三次完整预处理则稳定显示 Shared 更贵：中位 CPU 43.736 ms，ValueCache 36.525 ms。父边表示减少传递依赖存储，不代表逐方向反复走父边就更便宜；原预算检查频率没有为新实现稀疏化。

## 3. 主 L2 三次重复：成本与收益分开''')
s=s.replace('## 4. 候选、保护与覆盖得失','''可选成本与尾部边界：每个被取消的 20 ms 事件仍可能因非中断式 JSON/清理/记录尾部产生超支，逐次额外量见 `sequences.csv` 的 `event_overrun_cpu/wall` 和逐事件文件。旧/新配置均计入，不能拿标称 20 ms 当最终耗时。上表 RSS 是完整进程高水位，不是仅数值缓存的净增量；本轮没有把缓存所有动态大整数容量单独做精确堆计量。

## 4. 候选、保护与覆盖得失''')
s=s.replace('带更高无保护分数且有观察缺失的记录共 85 条', '''**诊断轨道的实际见证：** convert 的原生位置 3，两种缓存配置都选到方向 186、参数 t=3 的候选；完整保留 1049 个 protected 观察，新增 covered 从原生的 1049 提高到 1092，即 **+43**。原式合法、官方实际访问和完整保护已独立核验。完整赋值和访问轨迹见 `analysis/diagnosis_v1/diagnostic_opportunities.json`。这是同一个固定位置在两个实现中的一致见证，不是两个独立实例，更不是 100/20 ms 主结果；两个探针都继续使用原生历史，没有交付或将见证带入后续排序。

诊断共完成 133 次候选评价：99 次因 protected 观察缺失被拒，34 次为严格覆盖改进候选（集中在上述同一位置，两配置各 17 次）；另保留 4 条候选重复和 6 条未完成候选。不能用这个截断且有限的集合估计全问题的保护拒绝率。real 的每个缓存配置只有位置 2、5 各完成一个候选，均保护失败，且没有更高的无保护得分；位置 3、4 没有候选。

带更高无保护分数且有观察缺失的记录共 85 条''')
s=s.replace('random 仍为 89 个分量', '''**real 无参数的直接原因已进一步核对。** 主 L2 中，ValueCache 完成 101 个完整域，Shared 完成 105 个；全部精确为 `{0}`，并非不完整记录被写成空域。补充轨道另有 67 个同样的 `{0}` 域。已记录的 2118 次 `no_nonzero_legal_parameter` 均与原式完整域 `{0}` 一致，另有 2 次命中搜索未完成；生产轨道提出参数总数为 0。较宽探针中，每种缓存配置的 real 64 个域有 62 个 `{0}`、2 个有非零位置。说明原有单方向集合在这些 anchor 上大多不能移动，不能归因为保护筛选，也不能推广为原问题不存在其他模型。检查只是分类已落盘区间，没有重算未完成工作、没有新 worker/solver 调用，见 `analysis/domain_records_v1/summary.json`。

完整原式域包含已验证原生 anchor，故本批完成域的 `exact_empty` 为 0；`{0}`、unsupported、not_started 和 incomplete 分开统计。目标的 `complete_no_hit_in_domain` 与预算取消也分开，未记录的目标内部中间状态不作填补。

random 仍为 89 个分量''')
s=s.replace('## 6. 十项直接回答','''当前 oracle 证据是编码推进而非求解推进：Legacy 的 random/real 八案均停在 reach_build，Shared 的相同八案进入 extra_build；convert 两种编码八案都停在 extra_build。24 案均未进入 solver_add、SMT2 完整导出或 check。没有产生可用的完整问题 DAG 大小统计或求解答案，缺值保留未知，不能写成 0 大小或 UNSAT。阶段 enter 记录的计数是最近已落盘的下界；父进程杀死后不能补造末尾计数。

## 6. 十项直接回答''')
s=s.replace('###___unused___','')
s=s.replace('本轮仅提交是否值得继续研究的离线判断，停止于报告，不自动执行在线短会话。下一因素应依据实际停止阶段选择；保持保护和原生反馈隔离，先解决仍占主导的单一阶段，不用放宽预算、换目标或重开 B 补救。随机超大分量的候选供给、方向质量、逐模型 CPU 信用和等时间在线收益仍需独立研究。','''本轮四层结论分别为：正确性与状态隔离通过；数值复用消除了特定重复扫描并在同预算内完成更多域，属于局部成本/工作量进展；Shared 的整体预处理降本未成立；100/20 ms 的合法候选阶段与整体离线覆盖机会均未成立。convert 的 +43 见证只证明较宽预算下存在局部机会。

最值得下一轮独立检验的单因素是：**将 Shared 的 affected 构造改为等价的批量/共享祖先传播，消除现有逐方向重复遍历**，仍核对完全相同的语法影响集合，不改方向池或保护，不以减少预算检查频率获胜。本轮没有实施这第三项修复。即使这一阶段修好，convert 诊断位置 2 的排序本身已花 34.93 ms CPU，超过整个生产事件上限；因此不能承诺一个局部修复就会使候选可达。real 的大量 `{0}` 域则是另一个需要独立研究的方向供给问题。

其余记录边界：预处理构造/验证方向时 trace 未填充稳定方向 ID（为 -1），可定位到具体阶段、节点和累计工作，不能给出精确的在途方向身份；事件中的方向槽与取消阶段均保留。没有为补这个记录缺口重跑已冻结实验。冷启动指每 worker 的空数值缓存、空索引和新方向池；未清空操作系统文件页缓存。CPU 绑定为逻辑 CPU 0，sysfs core_id=0，兄弟线程列表 0–1；不是对宿主所有背景进程的独占声明。

本轮止于离线报告，没有在线短会话、900 秒矩阵、真实 HighDiv 重跑、新 seed 或 B 补救。历史逐模型 CPU 信用、真实生成供给以及等时间/等样本在线收益仍未知。''')
p.write_text(s)
exclusive(BASE/'analysis/report_postaudit.json',{'report_sha256':digest(p),'input_summary_sha256':digest(BASE/'analysis/audit_v1/summary.json'),'distinct_counts_sha256':digest(BASE/'analysis/distinct_assignments.json'),'recorded_domains_sha256':digest(BASE/'analysis/domain_records_v1/summary.json'),'diagnostic_opportunities_sha256':digest(BASE/'analysis/diagnosis_v1/diagnostic_opportunities.json'),'frozen_implementation_changed':False,'extra_real_workers':0,'solver_checks':0,'note':'Post-audit interpretation and correction of a count label; original logs and frozen scripts preserved.'})
print('post-audit report finalized')
