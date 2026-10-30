# Guided Sampler 第三轮语义诊断报告

本轮已执行有限诊断，没有新增 900 秒矩阵，没有重跑冻结 HighDiv，没有追加 seed，没有开启 B。结果是：**当前 A 的指定目标仍未兑现，失效不能统一归因于“官方没有访问”或“只缺 relevance”。** 新追踪定位了相位撤销与内部赋值到叶子模型之间的断点；独立查询又证明所选目标存在全局不可行、访问不可行和当前固定条件阻塞三类情况。本轮没有证据支持优于完整 HighDiv。

分支 `round3-a-semantic-diagnosis` 从 `2f839861acf0a8cec78e05dac256b98b0dc30099` 建立。D0 见证先提交为 `98d8d02`，D1 实现与测试冻结于 `4712d0e`，D3 独立实现和六检查点计划冻结于 `7cb77b4`。原指引及用户附件完整保存在 [execution_guide.zh.md](round3/execution_guide.zh.md) 和 [request.zh.txt](round3/request.zh.txt)。

## 1. “没有观察到改变”到底缺少哪一步

旧数据只读复核全部 916 次建议、534 次实际相位改变、941 条 action–target 支持记录。941 条纯位值均未达到期望，其中 320 条节点被官方访问、621 条未被访问，目标观察命中和新增 covered 均为 0。**621 是 941 的子集；这些未访问记录也没有达到目标值，不能将它们解释成“值已改变，只是没访问”。** 旧记录覆盖 53 个唯一 `(node, bit, desired)`、709 个 run/query、43 个 legacy canonical key；旧真实内部 AST 缺失，不能把 43 个 key 当成独立证明的 43 个实际原子。

全部 916 个旧动作缺少真实内部表达式及模型恢复来源，旧 retention 的 canonical 反查只能保留为线索。旧样本原变量赋值完整，但不能进一步区分这些值来自原始解释、converter 还是输出补全。故本轮没有把缺证据的旧事件分配给“模型转换错误”或“映射错误”。这两项原因的可确认数量是未知，并非已排除。

新 convert apply 的 56 次建议实际改相位 50 次，支持 64 条目标记录、36 个唯一目标、31 个真实表达式、25 个查询。64 条仍全部 value_hit=false；50 条被访问、14 条未访问；目标观察和新增 covered 均为 0。56 个动作的最早已证断点为：39 个建议相位在最终内部赋值中不再保留，17 个最终内部赋值与实际 M_leaf 不同。50 个最初 assignment token 曾撤销，后续同值重新赋值使用新 token，不能算作原赋值持续存活。

observe 的 124 次建议没有实际改相位，支持 155 条记录、40 个唯一目标、32 个真实表达式、31 个查询；152 条被访问、纯值命中仍为 0。其中 121 次原生相位本来就不同于建议，不能列为 apply 后失效。其余 3 次建议同相位但未保留。计数单位见 [event_chain.csv](../results/round3_semantics/analysis/event_chain.csv)、[target_chain.csv](../results/round3_semantics/analysis/target_chain.csv) 和 [report_facts.json](../results/round3_semantics/analysis/report_facts.json)。这些是相关的、刻意挑选的诊断事件，不是独立随机试验，不估计显著性或总体比例。

## 2. 内部 assignment 与模型第一次在哪里分叉

convert apply 的 17 个事件，首次可验证差异发生在 **最终内部赋值 → 实际叶子模型 M_leaf**。相同提供者的 M_outer、独立原变量投影 M_original、正式收据 M_formal 未出现后续新的真值分叉。不能把这个结果归咎于官方访问或外层 model converter。

这 17 个最终 token 均未观察到直接 atom/EUF/理论消费入口的传递，且没有缓冲溢出。实际原子声明与原变量身份经过核对，真值来自对应模型独立求值，没有从 assignment 复制。证据支持“存活赋值尚未成为该叶子模型必须兑现的条件”这一诊断方向，但不是所有间接 EUF 影响均被排除的证明。

追踪覆盖两处 atom 入队、消费、Bool enode、add_eq/add_diseq、其他理论 assign_eh，以及同步来源可关联的理论等式/不等式队列和 delivery。完整间接 EUF 因果关联仍有 unknown；最后内部状态取自正常 finalize/detach 边界，没有冒称在模型构造入口又读取了一次活 context 的 relevance。跨 manager、丢失提供者、undef 和溢出均保留缺失状态。SMT_random observe 的 query 1/backend 14 达到 8192 事件上限，其 8 个 watched 原子的传播链判断已降为 `UNKNOWN_EVENT_OVERFLOW`；该实例原子定义及 converter 记录没有溢出，独立等价证明不依赖缺失的事件尾部。

实现和实际编译位置见 [round3_hook_map.zh.md](round3_hook_map.zh.md)。原生 get_model 调用次数未增加；M_leaf、M_outer 都在原有导出点观测。受控模型补全测试确认：先保留 raw undef，再在副本/单独投影上补全，原模型不被改写。

## 3. convert query 11 / decision 64 是否重现

新 apply 再次出现 `(= z448_31_11_ 0)`：query 11、decision 64、native_var 451，原生 false、建议及实际 true，coverage_version=10。该事件仍是最终内部 true、实际叶子及返回原模型 false；最终 token 未观察到直接传递。query 5/decision 25 和 query 7/decision 30 的可见动作字段也匹配。

历史 time900 convert 与新 apply 的前 63 条查询记录，在完整提交模型哈希（含 CCSS）、原生 assumptions、结果、LS seed 和 A 动作字段上全部相同；首次可见差异是新日志按预算在第 63 条结束。**这仅重现了可见轨迹与同类断点，不证明历史完整搜索状态相同。** 旧日志没有完整原生决策前缀、RNG 和学习状态，状态关系保留 `not_verifiable_from_old_logs`。见 [trajectory_comparison.json](../results/round3_semantics/analysis/trajectory_comparison.json)。

新 observe/apply 三对会话均在 query 3 首次出现可见模型差异；两个主实例此时实际 A 改相位为 0，故它们的模型或覆盖差异不能归因于 A。连续会话保留原生 CCSS/超时历史，且未映射代表仅在 observe 采集，两组诊断负担不完全相同。这不是同状态因果对照。

## 4. 原式可行、当前固定条件不可行的有多少

D0 预先冻结 12 个 action–target 见证；D2 实际执行 72 次独立求解，每次上限 2 秒，全部 SAT/UNSAT，没有求解 Unknown。12 个 Q0 使用已保存完整合法模型验证 F+Aq，未新增调用；12 个 Q7 因旧真实原子/声明来源缺失而跳过，状态为 mapping_unknown，不伪造 XOR 验证。

| 查询 | SAT | UNSAT | 含义 |
|---|---:|---:|---|
| Q1：F+V | 7 | 5 | 5 个目标值在原式下已不可行 |
| Q2：F+Reach+V | 4 | 8 | 另 3 个虽值可行，但官方观察不可行 |
| Q3：F+Aq+Reach+V | 0 | 12 | 4 个原式可观察目标被当前固定条件阻塞 |
| Q4：F+Aq+D | 0 | 12 | 所选代表建议条件在当前查询中均不可行 |
| Q5、Q6 | 各 0 | 各 12 | Q4 前提不可行，属于空真，不能证明支持/访问蕴含 |

因此，12 见证可分为 5 个全局值不可行、3 个纯值可行但观察不可行、4 个原式观察可行但 Aq 阻塞。这里的 D 明确是**旧目录中的原式代表条件**，没有被包装成已独立证明对应旧实际内部原子的条件。其不可行不能反过来证明旧映射正确。

SAT 见证全部保留，独立审计从落盘 SMT2 和模型重新核对了 23 个模型（12 个既有 Q0、11 个 Q1/Q2 SAT），检查原式、查询约束、精确整数位值及冻结官方访问，无新增求解调用。所有 oracle 模型均不计入正式样本。72 次 check 合计约 1.296 秒，最长约 0.068 秒；这些是 check 时间，不含公式/Reach 构造和审计。

## 5. 两个主实例为什么仍没有映射

SMT_random 和 SMT_real 的 observe/apply 各 8 个 CDCL 查询均接入真实 SMT 后端；每会话 8/8 收到 A 元数据。每会话前 64 决策累计 512 次，现有索引均未映射；无建议、无相位改变、无被干预查询暴露。窗口外决策继续正常进行，未扩大窗口或修改 HighDiv 路由制造触发。

每实例固定取最早 8 个不同键，共 16 个代表：11 个复合 Bool 门、5 个算术界。原生类型与实际 converter 链已记录，不能笼统称为 solve-eqs 结果。SMT_random 有 355 条可恢复定义；SMT_real 有 335 条，包含 dependent-expr-model/lia2card 来源。代表均可核对原声明身份，但身份正确不等于原节点语义对应已证明。

两次 2 秒上限的独立 XOR 核验均 UNSAT：SMT_random 的 `or(not(xH519<=0),not(xH519>=0))`、xH518 同形表达分别等价于原式 `not(xH519=0)`、`not(xH518=0)`。这是现有规范化/预处理语义对应的两个具体缺口；其证明在不受 F 限制的原声明空间成立，没有靠变量名字强配。另 9 个 Bool 门尚未证明原节点对应，5 个算术界的原式来源未证，均保留 unknown；未为凑满 16 次而对无候选者运行伪验证。

必须区分三件事：**后端已接通；2 个代表能独立映射；这 2 个代表是否存在可指导的当前缺口仍未证明。** 它们来自首查询、覆盖版本为 0，不能仅凭恢复映射就声称能触发 A。完整代表、实际定义及两次核验见归档的 mapping/，摘要见 [mapping_summary.json](../results/round3_semantics/mapping_summary.json)。

## 6. 条件干预支持什么解释

D0–D2 完成后，从新 D1 中预选最早 6 个“内部赋值到叶子模型不同、最终 token 无直接传递记录”的检查点，顺序执行 N0/A0/N1/A1 各一次，共 24 次，每次父进程上限 5 秒、seed=0、CPU 0。D3 使用独立库，冻结 D1 二进制与源树未改。原生 `context::decide()` 已 push_scope，N1/A1 调用现有 mark_as_relevant，再走正常 propagate；回溯使用原生 relevance trail 的撤销契约。不新增断言，不内部化原子，不换候选，不强行保持相位。

该环境存在 watchdog/原生计时线程，没有验证过安全的单线程历史进程快照，因此完全不 fork。24 次均明确命名 **same_query_not_same_state**：只恢复 F、原 Aq、覆盖状态及 seed，没有复制学习子句、相位缓存、CCSS 或预处理历史。前缀指纹可作检查，但不能代替进程快照证明同状态。局部激活是本轮诊断性新干预，不能算作“只修日志的第二轮 A”。契约见 [round3_intervention_contract.zh.md](round3_intervention_contract.zh.md)。

| 历史检查点 | N0 | A0 | N1 | A1 |
|---|---|---|---|---|
| q5 / d25 | SAT | SAT | SAT | SAT |
| q11 / d64 | SAT | SAT | Unknown，边界缺失 | Unknown，边界缺失 |
| q13 / d27 | SAT，未遇到 | SAT，未遇到 | SAT，未遇到 | SAT，未遇到 |
| q19 / d31 | Unknown | SAT | Unknown | SAT |
| q23 / d44 | SAT | SAT | SAT | Unknown |
| q27 / d52 | Unknown | Unknown | Unknown，边界缺失 | Unknown |

共 15 SAT、9 Unknown；17 单元有检查点记录、4 单元完整结束但未遇到、3 单元截止前缺少边界记录而无法判定是否触发。已记录实际改相位至少 9 次、局部激活至少 7 次；这两项是有边界记录单元的下界。不能把缺记录计成零。父进程总耗时约 91.065 秒，最大截止检测/退出超额约 0.00863 秒；没有重试。

15 个 SAT 模型均独立验证 F+Aq；目标纯值命中、观察命中均为 0。完整四格的 q5 案例中，N0/N1 均返回 false；A0 最终内部 true 而叶子 false；A1 局部参与后最终内部也回到 false，且经过正常撤销/理论传递。这显示局部参与能够改变赋值处理，但没有改善所求相位的最终保留或目标命中。q19 的 A0/A1 SAT 记录也呈现相似差异；其他不完整格和 Unknown 不补造结论。未出现“传播抢先赋值/冲突后仍强制相反赋值”；有记录的相关标志均为 false。

所以本轮不支持“简单加 relevance 就可兑现目标”，也不支持“提高相位概率必然奏效”。D2 的固定条件阻塞及不可行证据与这些负结果相容，但 fresh-query 对照不能把所有变化强归因于单个历史事件。玩具四格正例仅验证机制能够工作，不当作真实数据有效性。见 [cause_matrix.csv](../results/round3_semantics/analysis/cause_matrix.csv)。

## 7. 下一项只改变一个因素的策略

建议下一项只研究**现有原生 Bool 决策到原观察的、经独立等价验证的预处理语义对应**，先处理本轮已证明的两个具体对应缺口，再反查当时真实单侧需求。保持原生候选、相位仲裁、relevance、fixed_var_pct、64 窗口、4 配额、CCSS 和 seed 不变；本轮未实现该策略，也未追加实验。

选择依据是两个主实例窗口内 512 次/会话全部 unmapped，而已存在两个可靠对应反例；盲目增加相位频率或统一激活 relevance 没有得到本轮支持。这个方向预期修复的是可证明的映射缺口，不能保证产生当前需求或目标命中。4 个固定条件阻塞目标作为后续独立方向保留，不与映射变化同时实施。下一轮性能实验前，仍须得到真实实例可核验的“目标→动作→理论→模型→官方观察”正链，或明确证明该目标/通道不适用。决策存档见 [strategy_decision.json](../results/round3_semantics/analysis/strategy_decision.json)。

## 实际执行、软相位代码与成本

软相位实际写入在继承的 [src/round2/a_context.inc](../src/round2/a_context.inc) `context::apply_A_phase_hint()`：原生变量已选定后，从其实际原子反查当前缺口，仲裁建议，写 `effective_phase`；原生 decide 随后使用该极性。第三轮生成器将只读诊断安装到新的源树，正式规则未改；可复查 [patches/round3_semantics/z3.patch](../patches/round3_semantics/z3.patch)。D3 的一次性相位/相关性实验独立位于 [semantic_intervention_phase.inc](../src/round3/semantic_intervention_phase.inc)，不进入 D1 库。

| D1 会话 | CDCL / 正式模型 | 总墙钟秒 | A 元数据注册秒 | A 显式总账秒 | 实际干预查询暴露秒 | 官方 covered / total |
|---|---:|---:|---:|---:|---:|---:|
| convert_observe_trace | 32 / 63 | 3.809 | 0.001404 | 0.189261 | 0.000000 | 38193 / 179302 |
| convert_apply_trace | 32 / 63 | 4.196 | 0.001332 | 0.209323 | 0.716878 | 38318 / 179302 |
| SMT_random_observe_trace | 8 / 8 | 24.461 | 0.001152 | 0.126865 | 0.000000 | 11166 / 104639 |
| SMT_random_apply_trace | 8 / 8 | 22.812 | 0.001108 | 0.119803 | 0.000000 | 11259 / 104639 |
| SMT_real_observe_trace | 8 / 8 | 4.442 | 0.001011 | 0.063343 | 0.000000 | 5667 / 66061 |
| SMT_real_apply_trace | 8 / 8 | 4.663 | 0.000958 | 0.056523 | 0.000000 | 5614 / 66061 |

六会话均按查询上限结束，均小于 60 秒，共 96 次 CDCL、158 个合法正式模型。正式文件仍保留正常 CCSS 结果，oracle/D3 模型不混入。完整成本类别见 report_facts.json：元数据注册仅合计 request_register、route_metadata、binding；A 显式总账包含索引、观测、仲裁、既有诊断收据等，不等同于相位改变本身的成本。convert apply 的 hot callback 累计约 0.012885 秒，50 次实际改相位所涉查询暴露 0.716878 秒；后者也不是可归因于 A 的净增耗时。

第三轮新增的语义层求值、事件收集和序列化并未全部分解成独占成本科目；`diagnostic_snapshot_seconds=0` 不表示新增追踪零成本。总墙钟包含这些负担，本轮没有新增关闭追踪的真实实例性能配对，不能用 observe/apply 的墙钟相减估计因果开销。两个零触发主实例也付出了索引、注册和仲裁开销。表中覆盖只是这六个短诊断文件的官方计分，不是新的性能排名；convert apply 比 observe 多出的其他位不等于指定目标命中。

## 验证、失败保留与复现

Release 和 ASan/UBSan 最终同源验证均通过：规范化/极性、实际内核、回溯 token、scope/pop/reset、取消/异常、CCSS 隔离、多叶子模型提供者、等式与其他理论入口、查询暴露保护、原模型不变的补全，以及 trace off/on 三模式的模型、原生选择、RNG、假设、结果、LS seed 一致性。关闭行为与已保存冻结基线 fixture 比较，没有重跑 HighDiv。704 项官方短路 Reach/共享 DAG/负数/第 63 位检查通过；此测试不调用 solver.check。LSan 仅保留历史已知 `lp::dioph_eq::imp::undo_fixed_column` 的精确抑制，未扩大抑制范围。验证摘要见 [validation_summary.json](../results/round3_semantics/validation_summary.json)。

两个构建失败（组件头文件依赖、暂存目录未创建）及修复前日志均保存；最终测试对应冻结源码/库哈希。D2 在完成 24 次调用后、case_04 尚未发起任何调用时中断重复 Reach 构造，改为缓存相同输入 DAG 后继续：总计仍为 72 次，已完成调用重复数为 0，保留中断日志、前后脚本哈希和 CONSTRUCTION_RESUME.json。未映射分析首次无可证明候选的全部输出、后续同 16 代表的两个核验均保留。审计器先后补充分离相位撤销、事件溢出降级，旧审计输出也保留；这些是原证据的离线重审，没有新增采样。

独立审计使用冻结官方 calc_metric.py（SHA-256 `a51cdd069321cd32becf8eeb5e606cb71fbab16ae3e0231f68963eaadf493f04`）、任意精度整数、实际模型层和声明身份；B 编码、内部化、选择路径均为零。D1 不新增约束/变量/relevance 改动，D3 局部激活单列。全部 Unknown、未命中、未遇到、缺边界及缓冲溢出保留。

复现入口依次为 `select_semantic_cases.py`、`build_round3.py`、`run_round3_correctness.py`、`run_semantic_probes.py`、`finalize_semantic_probes.py`、`audit_semantic_chain.py`、`check_target_feasibility.py`、`classify_unmapped_atoms.py`/`refine_unmapped_semantics.py`、独立 D3 build/prepare/execute、两项 oracle/intervention 审计和 `audit_round3_semantics.py`。执行脚本的 STARTED、已完成调用及冻结哈希保护用于防止覆盖证据或意外重复求解；已有完成目录不要直接重跑。

全部诊断原始文件在 [archives/round3_semantics](../archives/round3_semantics) 无损归档，逐分片/逐成员 SHA-256 和完整解压验证见 manifest.json、verification.json，恢复命令见 RESTORE.md。旧输入、上游源码、历史文件及关键二进制完整性结果见 [BASELINE_UNCHANGED.json](../results/round3_semantics/BASELINE_UNCHANGED.json)，本轮调用/预算/审计结果见 [audit_summary.json](../results/round3_semantics/audit_summary.json)。前两轮归档直接引用基点，不重复上传编译目录、虚拟环境或旧原始资料。

本轮归档实际为 1 片、19,158,304 字节，2127 个成员均已完整流式解压并逐成员核对；分片 SHA-256 为 `b7e117028b4478a464b91cd99de8db3a03810c7bcc2899736626a7c56d21ff3a`。历史完整性审计检查了 8 个输入、2935 个上游文件、3723 个旧文件元数据、5 个关键文件哈希及 28 个 D0 消费证据哈希，无变化。发布脚本只做非强制新分支推送，并在成功后使用 `git ls-remote` 核对最终提交 SHA。
