# Guided Sampler 第四轮：语义映射与覆盖优先软参考实验报告

本轮建立了真实需求映射，并在一个真实局部案例中证明：相同的历史值若仍硬固定会阻塞目标，改为软参考后 S_cov 实际找到了该观察。没有建立完整性能优势。S_cov 在 convert 的查询 3 命中了第三轮已证明“原式允许、当时继承条件阻塞”的 case_05、case_09，S_ref 的 CDCL 未命中它们。这两个目标是同一不等式及其 NOT 对应的两个原 AST 观察点，不能算两个独立语义成功。

负结果同样明确：S_cov 三个实例的全式官方 covered 都低于 S_ref；convert 还在 CCSS 消耗约 59 秒，截止时仅完成 4 次 CDCL、接纳 5 个正式模型。最终 token 的直接理论递送证据不足，严格完整链计数为 0；这不等于证明没有间接理论影响。当前版本不能声称优于完整 HighDiv，也不应凭这次局部命中自动进入 900 秒矩阵。

## 执行边界与冻结顺序

完整读取并保存了[第四轮指引](round4/execution_guide.zh.md)。从第三轮完成点 `fa68a9996a48cc2251ab2b8d9315da44606825af` 建立独立分支 `round4-mapping-soft-reference`。先完成 M 的实现、验证、6 次短会话及独立检查，再提交 [M 结果](round4/M_frozen_evidence.zh.md)，之后才实现 S。

- M 实现：`5df5eec0a9ba4cc6716e6af1e15d3cbc4060c517`；M 结果冻结：`f83f42b`。
- S 实现：`b635ce9095884512516e7a764e2daf65a400a6d9`；源码、头文件、Release/消毒器库及宿主 SHA 见两个 implementation manifest。
- 恰好 12 次正式短会话：M 六次、S 六次；全部 seed=0、CPU 0、独立进程、顺序执行。每项最多 60 秒，convert 最多 32 次 CDCL，两个主实例最多 8 次。计时阶段没有编译、压缩或审计；无重试、无追加 seed、无 HighDiv 基线重跑、无新 900 秒实验。
- 按用户明确答复冻结：每个外层 check 至多 4 次覆盖建议；参考建议独立受前 64 个普通决策窗口约束。两类实际改变均纳入 45 秒显式预算及 45 秒整查询干预暴露保护。
- B 编码、内部化、代理选择，指导新增断言/布尔变量、relevance 激活及新 LIA 数值移动均为零。保持原生选变量、原生 RNG 调用、CCSS 算法、双向模型交换和正式接纳规则。

## 1. 新映射是否提供真实需求？

是。只增加了同一整数项、同一常数的互补闭区间门与等式/不等式之间的两条精确规则，没有有限域推断。16 个实际原子独立 XOR 检查全部 UNSAT，未加入原公式背景，因此没有用矛盾背景的空真替代等价性。通用模板测试覆盖负/非零常数、交换孩子、NOT 极性及不互补/严格界反例。

| 实例/模式 | 新规则匹配 | 首模型后真实单侧需求事件 | 新规则建议 | 新规则实际改相位 | 同查询目标新增 covered 记录 |
|---|---:|---:|---:|---:|---:|
| convert_M_observe | 0 | 0 | 0 | 0 | 0 |
| convert_M_apply | 0 | 0 | 0 | 0 | 0 |
| SMT_random_M_observe | 27 | 22 | 9 | 0 | 15 |
| SMT_random_M_apply | 22 | 17 | 7 | 6 | 10 |
| SMT_real_M_observe | 51 | 44 | 14 | 0 | 23 |
| SMT_real_M_apply | 52 | 45 | 7 | 2 | 34 |

两个主实例首模型后的事件合计分别为 39、89。版本 0 的 24 次匹配只算接入证据；convert 没有新增门匹配。M_observe 自然命中的目标不能归功于相位改变。表中目标结果包含该模式全部 action，不能把计数列直接解释为新规则的净收益。

按事前固定顺序选取 6 个新映射需求，分别检查 F+G 和 F+inherited+G，各限 2 秒，共 12 次：4 SAT、2 UNSAT、6 Unknown。所有 SAT 见证均经过原式、精确位值和官方访问复核；Unknown 不作不可行结论，不重试、不延时。选取清单来自 random，不能外推为 real 的全局可行性结论；答案未进入在线评分。

## 2. 被软化的条件来自哪里？

只来自采样器 m_ls 的历史选取。`collect_inherited_reference()` 保留原筛选、遍历、0.5 选择率和 RNG 次序，复制原变量精确值，不为 check 构造等式。`QueryInputs::user_hard` 独立保留真实限制；当前 CLI 无外部 assumptions。已定义参考缺失、内部 skolem、运算不支持时返回未知，不补零。

独立审计逐项对照了源 CCSS 模型条目、声明身份、选择列表、hard/reference 摘要，并从 seed=0 重放全部宿主选择与 CCSS seed。convert/S_ref 的 31 次含参考 check 共选取 15,452 个值；S_cov 的 3 次含参考 check 共选取 1,476 个。S_cov 另有一次查询 7 的预备选取（483 个值），随后截止保护阻止了 check 入口；它单列为未进入查询，未计入有效软化或 CDCL 次数。

两个主实例每个模式的 7 次 CCSS 全部 Unknown，故没有产生可继承参考。它们验证映射和覆盖优先的局部效果，不能单独证明历史硬固定软化的效果。受控测试保留了真实外部条件、有限合法投影和 UNSAT；偏好未变成约束。

路由发生了自然变化：M 的 convert 首次使用 solver1，后续 31 次因继承 assumptions 使用 solver2；S_ref/S_cov 的实际 CDCL 均使用 solver1。两个主实例 M、S 都使用 solver1。没有 dummy assumption、额外 push/pop 或 ignore_solver1 强制路由。因此 M/S 差异不能解释为纯覆盖评分收益。

## 3. S_cov 是否提高找到观察的机会？

有一次可复用阻塞证明的真实局部成功，整体不一致。事前冻结的共同初始需求池来自两模式首正式模型的单侧缺口交集，并限定为已有直接规则可涉及的原节点/位；三个实例的首正式赋值实际相同。以下均由冻结官方访问器复算。

| 实例 | 共同初始需求数 | S_ref 观察命中 | S_cov 观察命中 | S_cov 自选目标池 | S_ref 会话内命中该池 | S_cov 会话内命中该池 |
|---|---:|---:|---:|---:|---:|---:|
| convert | 24244 | 173 | 313 | 5 | 0 | 4 |
| SMT_random | 36623 | 2390 | 2468 | 405 | 15 | 22 |
| SMT_real | 27216 | 1414 | 1377 | 481 | 17 | 19 |

自选目标池是策略选择的描述性分母，不是独立随机样本；“会话内命中”也不等于“发出建议的同次查询命中”。三个 S_cov 的同次查询独立目标新增覆盖分别为 convert 4、random 3、real 18。random 的自选池会话内命中 22 中，不能把其他查询的 19 个命中归给某次建议。

| 第三轮目标 | 语义条件 | S_ref 的 CDCL/CCSS 观察次数 | S_cov 的 CDCL/CCSS 观察次数 | S_cov 实际建议 |
|---|---|---:|---:|---:|
| case_01 | NOT(z448_31_31_=1)，期望 true | 0 / 10 | 0 / 0 | 0 |
| case_02 | z448_31_31_=1，期望 false | 0 / 10 | 0 / 0 | 0 |
| case_05 | 原节点 3497，期望 false | 0 / 0 | 1 / 0 | 1 |
| case_09 | 原节点 3498，期望 true | 0 / 0 | 1 / 0 | 1 |

后两项是同一线性和 ≥ 9315 的两个原 AST 观察点。S_cov 在 query=3、decision=30 将该已选原子从原生 false 改成 true；内部最终值、M_leaf、M_outer、原投影、官方 Reach 与新增覆盖一致。该原子的参考相位为 unknown，覆盖没有压过一个已定义的参考相位。另一个 ≥13878 原子原生本来就是 true：相应两个目标虽新增 covered，不能算改相位导致的命中。

全体真实会话只有一次“覆盖压过已定义 reference”：convert/query=3/decision=53 的 z230_31_11_=0。它在内部最终为 true，但叶模型与正式模型为 false，目标没有命中。受控布尔测试的优先级冲突可正常仲裁，真实实例的这次冲突并未形成成功模型事实。

进一步只读核验确认：S_cov 查询 3 的 489 个参考等式，与第三轮 case_05/09 及本轮 M_observe/M_apply 查询 3 的硬继承条件集合完全相同（只忽略空白与合取顺序）；F 的输入 SHA、原节点及 G 也一致。因此既有 Q2=SAT（F+G）和 Q3=UNSAT（F+A+G）可以直接复用：当前这些参考若仍作为硬条件，目标仍被排除；放软后 S_cov 的正式模型实际命中。没有新增 oracle 求解。

S_ref 与 S_cov 的前两个正式模型哈希、查询 3 前的覆盖快照、前 30 次原生 canonical key/phase 全部相同；S_ref 此前没有 action，S_cov 在 decision=30 首次给出覆盖干预。这是可核验的外层输入与选择前缀一致，仍不冒充完整求解器内部状态复制；理论因果关联的限制不变。证据见 [既有阻塞证明复用](../results/round4/analysis/reused_blocker_proof.json)。其他参考集合没有追加可行性检查。

## 4. 理论、模型、访问的完整链建立了吗？

尚未建立可审计的完整因果链。严格要求最终实际赋值 token 的直接理论递送、模型事实和新增覆盖同时成立时，三个 S_cov 的计数都是 0。日志保留 fresh token、撤回/重赋值、理论入口、实际模型提供者、原声明身份、纯值与官方访问；未把历史 action 的首赋值序号误当最终 token。

这不是“所有命中均与理论无关”的证明。复合不等式门自身是 Boolean 门，子原子的间接理论作用仍有未完全关联的部分，标记为 Unknown。random/S_cov 有 3 个 action 的链受有界事件缓冲溢出影响；convert/S_cov 的 3 个等式 action 确实断在内部赋值→M_leaf；另外还存在建议相位在回溯后未保留。

real 中避免阻塞也出现了可验证的位值结果：query=5/decision=15 的新映射门对应 xH383≠0，正式值 1050 命中 bit 1、3、4、10；query=15/decision=1 对应 xH211≠0，正式值 2000 命中 bit 9。内部及模型中的门真值一致、官方访问成立，但缺少完整的最终 token→间接理论因果证据，所以只记目标观察，不宣称由该建议保证或单独造成。

| S_cov 来源 | random：目标记录 / 新 covered | real：目标记录 / 新 covered |
|---|---:|---:|
| coverage_support | 13 / 3 | 17 / 13 |
| avoid_direct_blocker | 556 / 0 | 986 / 5 |

避免 x=0 只排除了一个确定阻塞方向，绝不保证任何特定位成为 1。上表保留了大量可访问但位值未命中的负结果，不把 avoid 当作 support，也不把同一目标在不同 action 中的记录当成全局独立覆盖。

## 5. 只是软化换了轨迹，还是覆盖有额外价值？

S_ref 与 S_cov 共享软化宿主、参考收集、自然路由和窗口，差别是冻结的覆盖优先规则。convert 的相同 489 条件阻塞证明复用与 case_05/09 命中，给出额外局部机制证据；random 的共同池也增加，real 的共同池反而减少。两个主实例没有历史参考，因此它们的差异不能归因于取消继承硬约束。

仍不能据此做同状态因果或统计优势声明：只有 seed=0 的有限会话；轨迹会分叉；convert 的 S_cov 未达到与 S_ref 相同的 CDCL 数。M/S 的路由和状态历史不同，M_observe/S_ref 即使都没有实际改相位，复杂实例也不保证逐模型相同；受控关闭测试的字节回归不能外推为所有实例的内部状态复制。

## 6. 实际成本、重复率与完整 HighDiv 比较

| 实例/模式 | CDCL 次数 | 正式/原始候选 | 官方 covered / total | 会话秒 | 终止原因 |
|---|---:|---:|---:|---:|---|
| convert_S_ref | 32 | 37 / 63 | 36556 / 179302 | 12.421 | cdcl_query_limit |
| convert_S_cov | 4 | 5 / 5 | 28308 / 179302 | 60.008 | deadline |
| SMT_random_S_ref | 8 | 8 / 8 | 11230 / 104639 | 23.434 | cdcl_query_limit |
| SMT_random_S_cov | 8 | 8 / 8 | 11136 / 104639 | 21.059 | cdcl_query_limit |
| SMT_real_S_ref | 8 | 8 / 8 | 5961 / 66061 | 5.078 | cdcl_query_limit |
| SMT_real_S_cov | 8 | 8 / 8 | 5697 / 66061 | 5.439 | cdcl_query_limit |

相对于 S_ref，S_cov 全式 covered 在 convert/random/real 分别减少 8,248、94、264。convert/S_ref 的 63 个原始候选有 26 个重复（41.27%）；正式模型只有 6 个来自 CDCL、31 个来自 CCSS。S_cov 仅有 4 个 CDCL 模型与 1 个 CCSS 模型。其他四个主实例会话均只有 CDCL 模型，无重复候选。所有正式模型均通过原式合法性、冻结官方计分及独立精确评价。

convert/S_cov 的主要成本是 query=4 的 CCSS：59.058 秒后 Unknown；本次 CDCL 总检查时间只有 0.561 秒。对应 S_ref 的 query=4 使用相同记录 seed=1573007388，约 0.045 秒 SAT，但此前 query=3 的模型已经不同。只读源码核验确认完整 HighDiv 的模型交换仍在：模型生成器写 ast_manager::last_CDCL_model，CCSS build_instance 读取并用于初始化。因此相同 seed 不代表相同 CCSS 初态。改变的 CDCL 历史可以通过这条原有路径影响 CCSS；没有完整 map 快照或同状态重放，本轮未隔离 59 秒失败的唯一内部原因。证据见 [CCSS 成本来源](../results/round4/analysis/CCSS_cost_source.json)。

| 实例/模式 | 实际改相位 | 显式账本秒 | 干预整查询暴露秒 |
|---|---:|---:|---:|
| convert_S_ref | 4 | 0.587215 | 0.537904 |
| convert_S_cov | 4 | 0.130655 | 0.405731 |
| SMT_random_S_ref | 0 | 0.161881 | 0.000000 |
| SMT_random_S_cov | 14 | 0.234055 | 17.872660 |
| SMT_real_S_ref | 0 | 0.084097 | 0.000000 |
| SMT_real_S_cov | 18 | 0.100609 | 3.864417 |

S_cov 实际改相位共 36 次（convert 4、random 14、real 18），S_ref 共 4 次。M_apply 另有 58 次，其中 convert 的 50 次属于旧映射，两个主实例新增门共 8 次。观察、同相位建议和元数据登记不计入 override。

元数据成本与改相位暴露分开：例如 convert/S_ref，最后完整查询账本中的索引构建约 0.0534 秒、登记约 0.000859 秒、参考收集/输入日志约 0.194 秒、参考源日志约 0.170 秒、热回调约 0.0426 秒。random/S_cov 的热回调约 0.0791 秒、暴露守卫约 0.0812 秒，而整次受干预查询累计暴露 17.873 秒；后者绝不是净新增开销。

显式账本不是所有诊断 I/O 的完整性能剖析。原生详细语义导出和模型/文件处理可能体现在查询及会话总时间中；不能用较小的显式账本数掩盖 60 秒总耗时。最终提交、日志及未进入 check 的准备工作产生账本尾差，已计入 summary 的显式总量，另在 cost_and_routes.json 单列；convert/S_cov 该差约 0.01017 秒。正式会话没有触发指导显式/暴露停用，也没有记录暴露超支；它因会话墙钟截止，不能把 CCSS 时间误记为 A 干预暴露。

是否优于完整 HighDiv：未建立。这里完成的是有限机制诊断，不是 900 秒性能确认。没有重跑或替换完整 HighDiv，也不能用 S_ref 代替完整 HighDiv 声称获胜；连本轮共同软参考对照的全式覆盖都未胜出。局部目标命中、理论证据不足和完整采样成本必须同时保留。

## 代码、验证和证据交付

- 软相位入口：[soft_phase.inc](../src/round4/soft_phase.inc)，最终完整后端文件为 [a_context.inc](../src/round4/a_context.inc)。
- 精确部分参考：[reference_evaluation.hpp](../include/round4/soft_reference/reference_evaluation.hpp)；支持/阻塞评分：[phase_evidence.hpp](../include/round4/soft_reference/phase_evidence.hpp)；历史来源与 RNG：[inherited_reference.hpp](../include/round4/soft_reference/inherited_reference.hpp)。
- 宿主/后端生成脚本与完整补丁位于 scripts/patch_round4_*.py、patches/round4/M、patches/round4/S；M/S 独立头文件与构建树保留。
- M Release/ASan/UBSan 各 17 项检查通过；S 各 19 项通过，另有两种构建的端到端软宿主和独立模型 completion 验证。包含有限投影、真实硬条件、UNSAT、回溯新 token、CCSS 隔离、跨 manager、取消、pop/reset、配额/暴露、关闭行为和保存的旧原生/RNG/模型回归。唯一 LSan 例外仍是已核实的上游 32 字节泄漏，没有扩大抑制。
- 受控 x=0 或 x=10 的真实原生选择是 x>=10，未匹配等式，两个模式都得到 0；纯评分的条件方向正确不能替代这个未触发结果。另一个布尔窗口测试实际记录 64 个 action，S_cov 恰有 4 个覆盖建议压过参考。
- 构建存储故障、80/73 个损坏对象恢复、链接失败及中止、夹具版本号错误、离线 RNG 审计器 EOF 错误均保留。它们发生在正式 S 会话之前；没有用重跑正式实验挑选结果。截止前未进入的准备记录在后续独立审计中补核验，没有改求解实现或官方分数。审计还纠正了冻结比较计划中的 Q4 编号引用：实际 F+A+Reach+期望值对应 Q3，Q4 检查的是旧建议条件 D；原计划及修正前结果保留，四个目标集合和分数不变，最终阻塞结论使用 Q3。
- 正式独立 solver 检查仅 M 的 16 次实际映射 XOR 和 12 次目标可行性；受控模板测试另有 6 个验证尝试 × 32 次，共 192 次 XOR（含夹具修正前的已通过项目），重复验证及原始记录全部保留。S 分析、四目标清单及共同池比较均为零额外 solver check，oracle 模型从未成为正式样本或线上优先级。
- 历史保护审计检查 5,854 个旧文件元数据、7 个保护 SHA、8 个输入及 2,935 个上游源码 SHA，变化为零。M 实现头文件、源码、二进制和库也按冻结 manifest 核验。

逐 token 链、真实原子字典、全部目标负结果、未访问/缺值/无映射/配额/回溯/溢出原因、完整模型、官方分数和独立检查见 results/round4 与完整归档。主要分析入口：[M_summary](../results/round4/analysis/M_summary.json)、[S_summary](../results/round4/analysis/S_summary.json)、[共同池比较](../results/round4/analysis/S_comparison.json)、[四目标清单](../results/round4/analysis/S_checklist.json)、[最终审计](../results/round4/audit_summary.json)。恢复方法与逐成员/分片 SHA 见 archives/round4/RESTORE.md 和 manifest.json。
