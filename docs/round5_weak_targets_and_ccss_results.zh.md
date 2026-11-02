# 第五轮：弱目标额度与 CDCL→CCSS 交换成本的独立诊断

本轮的两个结论不同。弱 avoid 确实消耗很多覆盖额度，但没有记录到它挤掉仍可执行 support 的机会；删除 block tie-break 的 support-only 在三个实例上均未提高全式覆盖。另一方面，可信的原生 CCSS 交叉重放证明：在本次 convert 捕获中，长时间失败跟随实际交换 map。它改变了初始化区间和初值，主要代价发生在后续搜索，并非构造变慢。空 map 也失败，不能据此建议清空交换信息。

完成 9/9 次 W 短会话、2/2 个 X1 初始化重建和 8/8 次 X2 重放，无正式重试。81 个正式模型均通过冻结官方脚本及独立精确观察核验。三个重放 SAT 候选仅完成约简 CCSS 验证，未冒充原始 F 的正式模型。本轮没有完整 HighDiv、900 秒矩阵、新 seed 或 B 实验，不能宣称优于完整 HighDiv。

## 1. 执行边界与冻结版本

- 基点：`ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550`；独立分支：`round5-weak-target-ccss-diagnosis`。
- 完整执行协议：[第五轮指引](round5/execution_guide.zh.md)。先完成只读复核，再冻结实现；P0 提交 `be6496c`，实现提交 `65efdd7`，W/捕获提交 `6980ded`，X 执行前计划提交 `9b769d2`。
- W 三实例 × 三模式，seed=0，正式预算 60 秒，CDCL 查询上限分别 32/8/8。同一个新 Release 宿主和动态库，只切换评分策略。9 个新进程在固定 CPU 槽统一释放；CPU 0/1 为超线程同核，已在计划中披露。X 使用 8 个不同物理核的槽位，同批释放，原生 cutoff 均为捕获到的 **52 秒**，父进程保护为 65 秒。
- 运行窗口内没有编译、审计、压缩或上传。全部构造、观测、日志及后续 CCSS 成本保留在完整会话中。
- **退出延迟不能隐藏**：convert Ref/Full/Support 的实际进程墙钟为 60.015/62.633/62.474 秒，未达到严格“进程在 60 秒内退出”的要求。宿主仍配置 60 秒，正式收据独立截于 60 秒，超出部分没有加入正式模型。Full/Support 的末尾 CDCL query=5 超时；这不是追加会话或扩展计分预算，原始记录全部保留。

实现及二进制 SHA 见 [冻结清单](../manifests/round5_implementation.json)。Release 宿主 SHA256 为 `75b947afd6e9305748c8c1c2a0f02dea1d1632341b857ba62dddd699aa4b2dd4`，实际链接库为 `080743b240f79114e8726d87c95b4acde82e588e1d560be7ede18a740de623cc`。

## 2. 实现前只读复核与唯一评分修改

第四轮归档的 2659 个成员经完整流式解压，与恢复数据逐一 SHA 一致；实际补丁源树与第四轮冻结清单一致。未执行旧二进制。详细结果见 [P0 报告](round5/P0_readonly.zh.md) 和 `results/round5/readonly/`。

以第一次正式模型冻结共同需求池，原始 AST 节点加 bit 为观察单位。G1 是共同需求池；G2 是已观察一侧但不在池中的位；G3 是初始未观察位。G0 在这些实例上为空，净差为零。NOT 仍是独立官方节点。分区互斥且覆盖全部可计观察点；纯求值仅解释未观察原因，绝不计作 Reach。

第四轮 random 的全式净差 −94 分解为 G1 +78、G2 −160、G3 −12；real 为 −264，分解为 −37/−219/−8。第四轮 convert 完整会话 37 对 5 个模型的净差为 −8248，不能当作等样本结果。旧日志缺少逐次拒绝守卫、完整早退、内部 map、生产者和 R0–R3；这些记为 `not_recorded`，不是零。

本轮唯一新增评分消融在 [coverage_policy.hpp](../include/round5/coverage_policy.hpp)：S_full 保留第四轮 support/block 字典序；S_support 只在两侧 support 不等时选择较大侧，support 相等时完全取消 block 仲裁，包括“两侧 support 都非零”的情况。被取消的 avoid 不计额、不标记目标已尝试。仍保留每 check 四次覆盖建议、前 64 个原生决策窗口、同相位计额、先评分后去重、参考回退及暴露守卫。

实际软相位执行在 [soft_phase.inc](../src/round5/soft_phase.inc)，通过补丁进入生产 SMT context；没有更换原生决策变量、新约束、relevance 标记、B 表达式或路由。交换捕获位于原生 `mk_values` 写入之后，实际构造/搜索探针编入生产 sampler，重放器链接同一对象。调用链、map 作用域及 timer 起点见 [transfer_call_graph.zh.md](round5/transfer_call_graph.zh.md)；实际变更见 [完整增量补丁](../patches/round5/round4_to_round5.patch)。

Release、ASan/UBSan 各通过 29 项受控检查，另各通过 6 类真实构造边界测试。包含固定输入 S_full/R4 建议与 RNG 回归、关闭行为、四模式日志开关、相位/参考/额度/去重/回溯、负数及高 bit、原生配方重建、完整关闭 Probe 的初态对照、128 位溢出与差分溢出、缺项、空 map 和截断输入。保留原有精确的上游 32 字节泄漏例外，没有扩大抑制。冻结前保留 3 次工程失败：一次补丁定位失败、两次重放器链接失败；修复后才冻结，未重跑 W/X。

## 3. W：完整会话、同样本与集合外得失

覆盖列是双侧均实际观察的 bit 数；分母分别为 convert 179302、random 104639、real 66061。CPU 为 user+system；墙钟包含全部实际成本。

| 实例 | 模式 | 正式/原始/重复 | CDCL/CCSS 正式来源 | 全式覆盖 | 墙钟秒 | CPU秒 |
|---|---|---:|---:|---:|---:|---:|
| convert | Ref | 27/43/16 | 6/21 | 36550 | 60.015 | 11.234 |
| convert | Full | 3/3/0 | 2/1 | 27761 | 62.633 | 53.184 |
| convert | Support | 3/3/0 | 2/1 | 27761 | 62.474 | 53.182 |
| random | Ref | 8/8/0 | 8/0 | 11230 | 24.951 | 24.704 |
| random | Full | 8/8/0 | 8/0 | 11136 | 22.185 | 21.916 |
| random | Support | 8/8/0 | 8/0 | 11101 | 25.481 | 25.229 |
| real | Ref | 8/8/0 | 8/0 | 5961 | 5.543 | 5.285 |
| real | Full | 8/8/0 | 8/0 | 5697 | 6.110 | 5.805 |
| real | Support | 8/8/0 | 8/0 | 5687 | 5.739 | 5.453 |

完整会话相对同宿主 S_ref 的分区净差：

| 实例/模式 | G1 | G2 | G3 | 全式净差 |
|---|---:|---:|---:|---:|
| convert Full | +125 | −8914 | 0 | −8789 |
| convert Support | +125 | −8914 | 0 | −8789 |
| random Full | +78 | −160 | −12 | −94 |
| random Support | +73 | −206 | +4 | −129 |
| real Full | −37 | −219 | −8 | −264 |
| real Support | −26 | −248 | 0 | −274 |

convert 共同前三个正式模型中，两种覆盖策略相对 Ref **+492**，分解为 G1 +145、G2 +347、G3 0；前两个模型完全相同。随后 Full/Support 在第二次 CCSS 停留至截止，局部质量收益没有转化为完整会话收益。Ref 获得的 9308 个独有覆盖位中，8395 个由 CCSS 模型首次补齐另一侧、913 个由 CDCL 补齐；不能把后续供给损失从策略成本中扣除。Full/Support 只有两个 CDCL 正式模型，所以本轮无法给出“双方各四个 CDCL”的比较；数据明确保留 4 对 2 的不等供给标签。

random/real 都交付八个正式模型，完整结果同时是共同八样本结果。Support 相对 Full 分别 −35 和 −10。real 虽然 G1 改善 +11、G3 改善 +8，却被 G2 −29 抵消；random 为 G1 −5、G2 −46、G3 +16。Support 没有超过 Ref，也没有仅靠删除 avoid 超过 Full。

损失主要是本次模型集合没有给出另一侧的值，同时保留访问损失：random Full 相对 Ref 丢失的 1206 个位中，1176 个在其样本集合中缺少所需另一值，28 个纯值可得但未实际观察，2 个完全未访问；real Full 的 692 个对应为 664、28、0。Support 的对应计数是 random 1077/30/2，real 683/22/0。该纯值解释不扩大官方观察。首次观察模型、来源、节点指纹、bit、另一侧 Reach 及纯值均在逐位文件中。

全部共同正式前缀和实际共同墙钟点见 [W_prefix_comparisons.csv](../results/round5/analysis/W_prefix_comparisons.csv)，没有延长已到 CDCL 上限的会话来凑时间点。

## 4. W：真实建议额度，而不是展开 bit 数

下表为“建议数 / 实际改变原生相位数”；参考建议独立于四次覆盖额度。

| 实例/模式 | support | avoid | 参考 |
|---|---:|---:|---:|
| convert Ref | 0/0 | 0/0 | 17/4 |
| convert Full | 4/3 | 0/0 | 1/0 |
| convert Support | 4/3 | 0/0 | 1/0 |
| random Full | 6/4 | 10/10 | 0/0 |
| random Support | 7/5 | 0/0 | 0/0 |
| real Full | 7/3 | 17/15 | 0/0 |
| real Support | 6/3 | 0/0 | 0/0 |

random/real Ref 没有可用参考建议或覆盖建议。Full 的 44 次覆盖建议中，27 次是 avoid，实际改相位 25 次；random 占 10/16，real 占 17/24。real 有两次 avoid 与原生同相位，仍按冻结口径计额。这个占比是动作数，不是目标 bit 展开量。

**没有证实挤占有效 support。** 本轮每次拒绝同时记录原始评分、去重后目标、配额前后及成本/暴露守卫。严格“只因 quota 被拒且仍有目标”的 support 为零。real Full query=13、decision=38 虽记录 support 偏好且额度已用满，去重后目标数却为零，不能算被 avoid 挤占的有效机会。其余三个额度拒绝都是 avoid。real Full 共五次原始评分有偏好但目标已尝试，不能从这些原始分数推断可兑现收益。

avoid 有明显展开集中：random 的 10 次动作展开 556 条目标记录，398 个唯一需求，仅 7 个原变量；real 的 17 次展开 986 条，467 个唯一需求，仅 8 个原变量。高 32 位分别占 320、544 条，但仍只对应 10/17 次动作。random avoid 同查询唯一新增命中为 0，real 为 5；整个会话最终观察到的对应唯一需求分别为 16、5，后者不等于该动作的因果贡献。

support 的同查询唯一新增命中，Full 为 convert 4、random 3、real 13；Support 为 4、5、14。自选目标命中略增并没有提高全式覆盖。这也不是“没有 support 可以执行”：Support 在 random/real 分别执行 7/6 次，实际改相位 5/3 次；问题表现为目标兑现有限、其他位置损失，以及 convert 后续供给下降。

显式 guidance 开销 Ref/Full/Support：convert 0.509/0.157/0.149 秒，random 0.223/0.304/0.294 秒，real 0.144/0.174/0.150 秒。该账本不能冒充全部诊断成本；完整 CPU/墙钟保留生产者日志和 CCSS 捕获成本。分类累计账本与未单列字段见 [W_cost_and_limit_details.json](../results/round5/analysis/W_cost_and_limit_details.json)。convert Full/Support 的 CCSS 总成本约 52.4 秒，远大于相位回调成本。详细机会漏斗见 [W_advice_funnel.csv](../results/round5/analysis/W_advice_funnel.csv)。

## 5. X：实际 map、来源与重建可信范围

固定取 convert 的第二次 CCSS，即 query=4，三模式都保留第一次和第二次捕获。Ref/Full 的 query=3 正式模型哈希、参考集合、宿主 RNG 前后及 query=4 seed 与第四轮分别一致；seed 为 1573007388。第四轮 Full 调用约 59.058 秒、本轮约 52.169 秒，实际 cutoff 从 59 变为本轮剩余预算给出的 52 秒。**历史精确 59 秒未复现；长调用/Unknown 现象在本轮 52 秒截止下复现。** 历史内部 map/RNG 没有记录，不能因此声称恢复了第四轮完整状态。

实际 map 有 593 个键：544 个来自当前批次、49 个为旧批残留，所有生产者均由原始写入事件核验；没有来源未知键。CCSS 尝试读取 503 个不同名字，其中 **454 命中、49 缺项**，没有解析失败或 128 位溢出。旧批残留均未被读取。map 与正式原变量模型共同部分的数值差异为零，但有 505 个正式原变量不在 map 中，还有辅助项；因此 map 绝不是“完整正式模型”。缺项保持缺项，没有补零。发现旧键并不足以认定交换契约错误。

两个 H 的 constructor 参数、R0、literal 构造输入及顺序、原始 clause 顺序、配置、编译器/标准库和 literal 身份相同；Ref/Full map 有 19 个不同值，全部属于实际读集。map 只经按键查找消费；完整副本及副本迭代顺序均保存，没有改动生产容器。

X1 以 fresh 原生对象调用同一 `build_lits/build_instance/initialize`，首次搜索步前退出，不新增 SMT 或搜索。两个对角均通过完整 R1/R2/R3、intervals、实际读值、变量/literal/clause/closure/pair/重构栈、初值及未满足集合比较；R0 由完整 mt 序列化核验。交叉消费键均具有同一冻结 F 的原变量语义，没有删除、重命名辅助项来凑兼容性。见 [X_capture_fidelity.json](../results/round5/analysis/X_capture_fidelity.json) 和 [生产者/历史核验](../results/round5/analysis/X_capture_details.json)。

## 6. X：八次实际交叉重放

“SAT”仅指通过原生及独立约简子句验证的 `ccss_solution_only`。没有任何重放候选加入 W。失败是本次有限搜索未交付，不是 UNSAT。time-to-solution 包括从配方重建开始的探针时间，另列父进程完整墙钟。

| ID | H/map | 结果 | 初始未满足 | 首解步数 | 首解时间秒 | 完整墙钟秒 | 最佳 cost |
|---|---|---|---:|---:|---:|---:|---:|
| X_rr | ref/ref | CCSS SAT | 147 | 219 | 0.172 | 0.262 | 0 |
| X_rc | ref/full | native cutoff | 147 | NA | NA | 52.203 | 23 |
| X_cr | full/ref | CCSS SAT | 147 | 219 | 0.182 | 0.272 | 0 |
| X_cc | full/full | native cutoff | 147 | NA | NA | 52.214 | 23 |
| X_r0 | ref/空 | native cutoff | 279 | NA | NA | 52.168 | 21 |
| X_c0 | full/空 | native cutoff | 279 | NA | NA | 52.165 | 21 |
| X_rr_repeat | ref/ref | CCSS SAT | 147 | 219 | 0.183 | 0.276 | 0 |
| X_cc_repeat | full/full | native cutoff | 147 | NA | NA | 52.186 | 23 |

在固定 H 内，只交换 map 就得到相同方向的结果；两套非 map 配方实际上也一致。对角重复的初态完全一致，确定性进度公共前缀分别 147/147 和 596/596 点相同。这比“同 seed”严格，但仍只说明当前捕获及记录边界，不保证其他实例/seed。

Ref→Full map 改变 **19 个初始化区间和 19 个初值**；R0/R1/R2/R3 的 RNG 状态却全部相同，初始未满足子句集合也完全相同，均为 147。这一案例不能用“随机数不同”或“初始未满足更多”解释。例：`z34_31_0_` 从区间 [0,510]、初值 475 变为单点 [2147287039,2147287039]；`z42_31_0_` 从 [0,510]、初值 297 变为单点 65535。区间端点、有效不等式、负数整除、变量域、缺项及差分值已由 Python 任意精度独立核验。这些区间是原生部分约束/补集策略的结果，不能当作原式整体联合可行域。

Full map 的构造（扣区间）约 0.10–0.12 秒、区间约 0.03 秒、累计初始化约 0.03–0.04 秒；扣除初始化/重构后的搜索约 **51.97 秒**。Ref map 对应搜索约 0.003 秒。日志计时嵌套在这些墙钟中，不重复相加。两种 Full map 对角及交叉在约 1000358 步首次达到全局 best=23，最后记录点为 2097152；已记录的连续无全局改善段至少 1096794 步。原生共初始化 5 次，单纯再次随机初始化已没有在这次预算内解决问题。

空 map 的读缺项为 503，改变 255 个初值，RNG 从 R2 开始与非空 map 分叉，初始未满足为 279。两格都失败，best=21；这否定了“本例直接清空 map 就能恢复快解”的建议。不能把这个控制上线包装为覆盖策略收益。

结论的强度是：**本次捕获中的 map 引起了初始化状态差异，并稳定造成后续搜索退化。** 尚未把 19 个值中的某一项、某一条补集规则或 LIA move 定位为唯一根因；本轮没有为此追加消融。

## 7. 独立审计、缺项和负结果

独立审计没有新增求解或搜索：冻结官方计分与独立原 AST 观察一致；81 个正式模型合法，97 个原始模型中有 16 个重复、0 个非法；W 有 2 个 CDCL Unknown、45 个 CCSS Unknown，进程非零退出为 0。random/real 的 42 个 CCSS Unknown 保留原文，未安装完整交换捕获，内部原因仍未知；convert 固定第二次 Full/Support 的原生原因明确为 `native_cutoff`。

X 为 3 个约简 CCSS SAT、5 个原生 cutoff、0 个跳过、0 个非零进程退出、0 个父进程强杀。三个候选再次用任意精度验证全部保存的原生子句、字面量值、变量硬界及零未满足数，均通过；**没有可靠恢复原 model converter，因此原始 F 合法性和官方覆盖为 NA**。这是验证范围限制，不把候选视作正式成功。

仍有以下缺项：cutoff 时精确最终 `_step` 未单独写出，只能报告最后进度点下界；交换逐次日志 CPU 未单列；复合目标的完整间接理论赋值链未记录，但合法最终模型的访问/bit 命中已独立验证。所有有界 trace 的溢出标记均为零。缺记录、历史未复现、超时、工程失败和负收益都保留，未用“所有测试通过”替代机制成功。

最终审计核对全部 8 个原输入、2935 个上游源码文件、历史结果元数据/保护 SHA、本轮 Release/SAN 实际源码与二进制、417 个已冻结 W/捕获文件、全部限定 attempts 和 X 输入 SHA。详见 [audit_summary.json](../results/round5/audit_summary.json)、[BASELINE_UNCHANGED.json](../results/round5/BASELINE_UNCHANGED.json) 和 [X 独立算术审计](../results/round5/analysis/X_independent_arithmetic_audit.json)。审计通过表示上述证据与限定验证成立，不表示严格退出墙钟无偏差或性能获胜。

## 8. 唯一优先的下一项单因素改进

建议下一轮只检验 **CCSS 连续无全局 best 改善的提前交还守卫**，候选阈值为 65536 个原生步：正常返回 Unknown，将剩余会话时间交回宿主；保留 map、初始化、RNG、move、原有 cutoff、A 评分与路由，其余不动。本轮没有实施或运行这一改进。

依据是成功 M_ref 的记录中最长无改善段仅 20 步，而 M_full 与空 map 的已记录段分别超过 109 万与 56 万步；W 的供给损失主要来自约 52 秒的失败搜索。预期先降低失败 CCSS 的 CPU/阻塞成本，再检验同预算合法模型供给及全式覆盖。它并不自动修复搜索能力，也可能截断其他最终会成功的长搜索。必须保留冻结原版与全部成功/失败捕获作为对照；打断 219 步快解、未降低成本、同预算全式覆盖/供给净下降或出现正确性/RNG异常，均应判失败。

本轮不优先继续调 avoid：没有有效 support 被挤占的证据，support-only 也没有全式收益；不优先清空 map：两个空 map 控制都失败。完整决定及失败判据见 [next_change_decision.json](../results/round5/analysis/next_change_decision.json)，逐结论、run/query/action、源码及证据 SHA 索引见 [root_cause_matrix.csv](../results/round5/analysis/root_cause_matrix.csv)。

## 9. 证据恢复与上传

全部原始 W 收据/模型、第一次及第二次真实 map、生产者事件、配方/RNG/初始化状态、X 原始进度与负结果、构建/正确性日志都在 [第五轮归档](../archives/round5/RESTORE.md)。在克隆仓库根目录按 RESTORE 指令恢复；分片与全部成员 SHA 见归档 manifest，完整流式解压校验记录见 verification。原始基准不上传，保留既有输入来源和 SHA；不复制历史归档或上传构建树/第三方二进制。

W/捕获原始 SHA 见 [round5_W_evidence.json](../manifests/round5_W_evidence.json)，X 及其余原始证据 SHA 见 [artifact_hashes.json](../results/round5/artifact_hashes.json)。数据文件中的本机路径仅是原始执行记录；恢复不依赖这些绝对路径。正常非强制推送独立分支后，以 `git ls-remote` 核对实际远端 SHA；最终回复给出经核对的完整提交号。
