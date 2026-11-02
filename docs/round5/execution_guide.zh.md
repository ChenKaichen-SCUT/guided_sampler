# Guided Sampler 第五轮：弱目标集中与 CDCL→CCSS 交换成本的独立诊断

## 0. 执行任务、冻结版本和禁止事项

工作仓库：`https://github.com/ChenKaichen-SCUT/guided_sampler`。
基点：`ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550`。
上游 HighDiv：`f2c6e1756b13281d96cbf90a8bd940129e56cce4`。
建议新分支：`round5-weak-target-ccss-diagnosis`。

**本轮不是继续寻找更多局部命中，而是解释为什么已有局部命中没有转化为全式覆盖与完整采样效率。** 实际完成代码、有限实验、独立审计、中文报告及 GitHub 推送，不止返回计划。

独立完成两个任务：

- **W：覆盖选择是否过度使用弱证据。** 先只读分析第四轮完整记录；再比较同一软参考宿主上的 `S_ref / S_full / S_support`。其中 `S_full` 必须复现第四轮 S_cov 的决策规则，`S_support` 只禁用按 block 差值单独产生的覆盖建议。
- **X：CDCL 模型交换是否导致 CCSS 初始化和搜索困难。** 保存真实交换 map 与实际 CCSS 构造输入，验证可重建性，再对同一个 CCSS 构造配方只替换输入 map 做交叉重放。不能靠相同 seed 或原变量样本文件冒充相同内部输入。

原 `HighDiv/`、8 个输入、前四轮正式数据、归档、受保护二进制及冻结基线不变。禁止重跑完整 HighDiv、追加 seed、启动新 900 秒矩阵、开启 B、添加目标约束、宏观域分析、在线不可达检查、MaxSMT、整数移动、在线学习或新的候选过滤。

不自动缩短 CCSS 的生产超时，不跳过 CCSS，不改变模型交换策略，不为了匹配结果重新构造/清空原生 map。只允许在独立重放器中替换 map，且不能把重放结果注入采样历史。

本轮允许重新运行的是**同一新构建中的短诊断对照**，不是重跑已冻结的 HighDiv 基线。所有新增会话均独立编号，与历史正式数据分开。

固定观察语义：原 AST、官方短路访问、Int 低 64 位、Bool 一位、`seen0/seen1` 与双侧 covered。两侧未见和两侧已见不设置取值偏好；首次观察照常记录；及时合法不同的零 covered 增益模型仍可接纳。参考值继续是软参考，真实硬约束不变。

---

## 1. 已确认事实与待验证假设

### 1.1 从冻结代码/报告可以直接确认

| 事实 | 来源 |
|---|---|
| `PhaseEvidence::best()` 先比较两侧 support；相同时再用 block 少的一侧 | `include/round4/soft_reference/phase_evidence.hpp` |
| support 和 avoid 都执行 `++r.suggestions`，共用每外层 check 最多 4 次覆盖建议；同原生相位的建议也消耗额度 | `src/round4/soft_phase.inc` |
| 分数在 `preference_attempted` 去重过滤前计算；动作身份包含 key、phase、kind、node、bit、desired | 同上及 `phase_evidence.hpp` |
| 第四轮 random/real 均为两模式各 8 个正式模型，S_cov 全式 covered 分别少 94、264 | 第四轮报告 |
| random 的共同初始可映射池多命中 78，但全式少 94；real 共同池少 37，全式少 264 | `S_comparison.json` 与第四轮报告 |
| convert 的 S_cov 共 5 个正式模型，S_ref 为 37；S_cov 的 query 4 CCSS 约 59.058 秒后 Unknown | 第四轮报告 |
| 同一个 query 4 记录的 CCSS seed 为 1573007388，但之前的 CDCL 正式模型不同 | `CCSS_cost_source.json` |
| 模型生成器写 `ast_manager::last_CDCL_model`；CCSS 的 `build_instance()` 复制该 map，`calc_var_intervals()` 读取它 | 冻结上游和成本来源记录 |
| `calc_var_intervals()` 会经 `random_complement(..., mt, ...)` 消费 RNG，随后初始化还继续消费 RNG | 冻结 `sampler.cpp` |

必须在本机核对**实际应用补丁后的构建树**与上述冻结来源一致；报告中的行号仅作定位，不能代替源码哈希。

### 1.2 以下都还不是既定结论

- avoid 抢占了本来能命中的 support 机会。
- 少量缺口收益导致了其他位置的覆盖损失。
- 59 秒失败一定由新的 CDCL map 导致。
- `last_CDCL_model` 一定含有错误旧值或缺项；尚需核对写入来源、生命周期和消费语义。
- 关闭 avoid、清空 map、减少 CCSS 超时一定提高总体性能。

本轮要检验这些解释，而不是写代码证明预定结论。

---

## 2. 固定执行规模与顺序

### 2.1 矩阵

| 阶段 | 工作 | 新执行上限 |
|---|---|---:|
| P0 | 只读恢复第四轮 S 的六会话，核验原始日志、模型与来源 | 0 次求解 |
| P1 | 有限合成回归、ASan/UBSan、instrumentation-on/off 验证 | 预先冻结测试清单；不作真实实例调参 |
| W | 3 实例 × 3 策略，seed=0 | **9 次短会话，每次最多 60 秒** |
| X0 | 从 W 的 convert/S_ref、convert/S_full 捕获第二次 CCSS 的输入 | 与 W 共用会话，**不额外启动宿主** |
| X1 | 两个捕获配方的构造/初始化重放一致性检查 | 只重建，不调用新 SMT，不跑性能循环 |
| X2 | 2 配方 × 2 实际 map + 2 空 map 对照 + 2 原生对角重复 | **最多 8 次独立 CCSS 重放** |
| P2 | 官方计分、独立审计、报告、归档、推送 | 离线，无新增采样 |

W 实例：convert、SMT_random、SMT_real。convert 每会话最多 32 次 CDCL 查询，另外两例最多 8 次；沿用第四轮退出位置与正式收据规则，不因新模型数较少追加查询。达到任一上限即停止。

X2 每次保留其配方记录的原生 CCSS cutoff，且不超过 60 秒；父进程硬墙钟上限 65 秒（包括构造、搜索、退出）。同一配方下全部 map 变体使用相同限制。若构造耗尽父进程额度，则记录构造退出，不延长时间、不重试。X2 不属于正式样本生成。

除正确性合成测试之外，本轮新增真实搜索最多 **9 个短会话 + 8 个局部 CCSS 重放**；不得自动加一轮不同 seed、不同阈值或 900 秒确认。

### 2.2 资源与随机性

Linux、8 物理核/16 逻辑核。构建及离线分析最多 16 线程。计时搜索期间不编译、不跑消毒器、不压缩和上传。

W 冻结 9 个独立逻辑 CPU 槽并同批释放；X2 在 W 完成及输入审计通过后另行同批运行，最多 8 槽。允许利用可用逻辑线程，但不凭空增加任务填满 16 槽。保存 CPU 拓扑、SMT 同胞对应、绑定、CPU 时间和实际并发占用；不得看过结果后换核重跑。

W 的宿主 seed 固定 0。X2 使用捕获的 CCSS seed 和 RNG 状态，不引入新的随机 seed。两项预先规定的对角重复是输入确定性核验，不是失败后重试。

这些单 seed 短会话用于诊断和开发筛选，不估计普遍胜率或统计显著性。历史第四轮在 CPU 0 顺序执行，本轮环境不同；新旧墙钟不能直接解释为算法加速。

### 2.3 冻结次序

先完成只读分析、测试和计划，再冻结 W 构建及参数。W 完成后冻结两个捕获包，再冻结 X2 运行清单。不得看过交叉结果后挑另一个 map、seed、检查点或初始化区间。

使用独立 `STARTED/attempt/completed` 记录，禁止覆盖已开始的尝试。测试失败允许修复后再验证，但正式诊断会话开始后的实现改变必须停止该阶段、保留全部记录，不把失败尝试改名为不存在。

---

## 3. 建议新增文件与接口

所有下列名字是本轮拟新增的设计接口，不冒充现有 Z3/HighDiv API。实际文件位置可以按工程调整，但职责必须保持。

```text
include/round5/coverage_policy.hpp
include/round5/decision_audit.hpp
include/round5/ccss_exchange_trace.hpp
include/round5/ccss_replay_recipe.hpp
src/round5/soft_phase.inc
src/round5/ccss_probe.inc
src/round5/ccss_replay_main.cpp
scripts/round5/read_round4_evidence.py
scripts/round5/coverage_partition.py
scripts/round5/analyze_advice_budget.py
scripts/round5/freeze_plan.py
scripts/round5/run_short_controls.py
scripts/round5/compare_transfer_inputs.py
scripts/round5/run_ccss_cross_replay.py
scripts/round5/audit_round5.py
scripts/round5/report_round5.py
scripts/round5/archive_publish.py
configs/round5_diagnosis.json
results/round5/{readonly,W,capture,replay,analysis,correctness}/
docs/round5_weak_targets_and_ccss_results.zh.md
```

沿用已有观测器、官方计分适配、收据、模型验证与压缩归档代码。不要把完整历史实现都复制一遍；保留可追溯补丁与受保护旧版本。

现有 `soft_phase.inc` 会被补丁脚本嵌入编译产物；必须确认本轮改动进入了真正编译的文件，防止只改未使用的展示源码。为每个可执行文件记录实际 `libz3` 路径、SHA、配置和功能探针结果。

---

# 任务 W：覆盖选择是否过度集中于弱目标

## 4. P0：先只读复核第四轮，别马上改评分

输入至少包含：六个 S 会话的正式收据、完整原变量模型、actions、native encounters、覆盖版本、参考输入、query 结果及模型来源。按仓库恢复说明解压，逐成员核对SHA；不能只使用摘要表。

若旧日志缺少某个字段，记录 `not_recorded`。不能从“没有建议事件”倒推“没有可用建议”。可以在相同已存模型上离线重算纯评分，但必须标成 `recomputed_from_frozen_prefix`，不追加 solver.check。

### 4.1 单位统一

```text
BitId       = (input_sha, original_node_fingerprint, bit_index)
DemandId    = (BitId, desired_value)
ActionId    = (run, external_query, backend_provider, decision_ordinal, action_index)
Opportunity = 同一次真实原生决策中的可读评分机会
```

跨manager或跨run不使用原始Z3 AST ID直接关联；使用原始DAG稳定编号与表达式/声明核验。原节点与其NOT是两个官方观察点；可以额外按已证明语义等价关系分组诊断，但不能据此修改正式覆盖分母。

每项至少区分：机会数、建议数、改相位数、与无覆盖局部回退不同的相位数、action–target记录数、唯一Demand数、唯一原子数、唯一新covered数。

**556条avoid目标记录不是556次决策，986也不是986次独立失败。** 同相位建议消耗额度，但不等于改变了搜索。

### 4.2 全式覆盖得失：用集合而非只看累计数字

新增纯离线接口：

```python
replay_official_observations(formula, committed_models) -> PrefixObservationSets
partition_from_first_model(first_observation, frozen_mapping) -> BitPartition
compare_prefixes(left, right, alignment) -> CoverageDifference
```

调用冻结 `calc_metric.py` 的原观察语义；不另写一个“更容易提高”的覆盖定义。逐模型维护：实际访问节点、seen0、seen1、已双侧覆盖BitId集合、首次观察与首次covered模型序号/来源。

每个共同前缀计算：

```text
ref_only = C_ref − C_cov
cov_only = C_cov − C_ref
净差 = |cov_only| − |ref_only|
```

将这些集合按起始状态分成互斥组：

- G1：共同首模型时已单侧、且属于第四轮共同初始可映射需求池的BitId。
- G2：共同首模型时已单侧，但不属于G1。
- G3：共同首模型时两侧未见，后续才可能形成观察/覆盖。
- G0：共同首模型时已双侧覆盖；理论上后续净差应为0。

严格复用第四轮共同池的构造口径，不为凑数字重定义“可映射”。如果首模型不同，不能强行使用上述共同首模型分组：单列初始差异，并以双方共同状态与剩余不一致组构造完整分区。仍报告未筛选的正式覆盖比较。

必须验证：各组净差之和等于全式净差；集合并集覆盖所有正式BitId，交集为空。保存精确计数和逐BitId差异表。

在第四轮等8模型终点，应重现：

```text
random：全式 −94，G1 +78，G1以外 −172。
real：  全式 −264，G1 −37，G1以外 −227。
```

这些是观测分解，不是因果损失估计。G3差异也不意味着下一步必须主动给“两侧未见”设取值偏好。

### 4.3 访问与值分开

对只在一侧完成覆盖的每个BitId，额外列：

```text
另一模式是否曾访问该节点；
若访问，是否只看到同一侧；
若未访问，在完整模型中该位是否曾具备所需值；
覆盖发生于CDCL还是CCSS；
两侧最先被观察和补齐的模型序号。
```

完整模型的未访问位值只用于诊断，绝不进入正式seen/covered。不要用赋值Hamming距离代替覆盖。

### 4.4 对齐方式

random/real：旧数据比较共同8个正式模型的全部前缀，至少1、2、4、8。

convert：先比较共同前5个正式模型，再单独报告37对5的完整会话结果；额外给共同前4个CDCL结果及模型来源统计，标明这不是同一完整混合轨迹的等样本性能指标。

时间比较只使用双方实际观察到的共同墙钟区间，给1、5、10秒等确实到达点。因查询数上限提前结束的曲线，不外推到60/900秒并冒充继续采样结果。

保存整个模型的增益和目标命中，两者分别统计。不能把全模型新增覆盖全归因于某个action。

---

## 5. 建议额度、弱证据与局部回退审计

### 5.1 每个决策的完整结果

新增/重建 `DecisionAudit`（原64窗口内，按外层check共享额度）：

```text
run/query/provider/decision/coverage_version
native_var/key/negated/native_phase
support[false,true], block[false,true]
evidence_complete
reference_available/reference_phase
raw_preferred_kind/raw_preferred_phase
unattempted_demand_count_before_apply
quota_before/quota_after
quota_used_by_support/quota_used_by_avoid
reason_if_not_applied
actual_source/actual_phase
changed_vs_native
would_fallback_phase_without_coverage
changed_vs_local_fallback
target masks / dedup identities
```

`would_fallback_phase_without_coverage`按照**同一当前状态**的 `reference_attempted`、参考可用性和原生相位计算，不改变集合、不消耗RNG。这只是该决策的局部反事实，不是整条S_ref轨迹。

### 5.2 必须回答的六个问题

1. 4个覆盖建议中support/avoid分别占多少？其中多少与原生相位相同？
2. 有多少覆盖建议与同状态下参考回退本来就相同，即覆盖信息没有额外改变该次先试方向？
3. 有多少真正不同的需求被反复关联到不同原子、不同建议类型？
4. 是否存在support在额度用完后出现，且额度此前被avoid消耗？
5. 这些被拒的support除了额度，是否还会因去重、未知、成本、已有赋值而被拒？
6. 得分是否因已尝试需求继续参与计算而偏高，随后却没有任何可执行目标？

当前代码“先算分、后去重”，第6项是必须审计的实现风险，不预设它就是错误或主因。本轮support-only消融不顺手修改此顺序；如果观察到问题，单独记录为下一项候选修复。

### 5.3 额度挤占的严谨口径

只有满足以下条件，才能记为 `support_quota_only_blocked`：

```text
真实遇到的已有原子未赋值；
在64窗口内；
证据完整且两侧support非平分；
按实际去重状态仍有可建议的目标；
显式/暴露保护未拒绝；
唯一剩余拒绝原因是4次额度耗尽。
```

如果其中至少一次先前额度由avoid消耗，记为 `avoid_occupied_quota_before_support`。

离线移除avoid后重算额度，只能得到“在这条已发生决策序列上多出的候选机会”。改变早期相位后后续轨迹会不同，不能声称这些机会必然都会遇到、命中或改善覆盖。

### 5.4 目标是否过于集中

分开报告support与avoid的：

- 唯一原节点/变量/精确语义原子数；节点类型Bool/Int及低中高位分布。
- 最高频前10个Demand和原子占action/额度比例。
- 重复目标的累计尝试、同次正式模型命中与会话内命中。
- 直接支持、仅避免相反值、访问未知三种语义强度。

不要新增训练器或在线新颖性评分。这里的作用是解释现有选择，不是另起一个新算法。

---

## 6. W：只改一个评分因素的短对照

### 6.1 三个策略

| 模式 | 历史参考为软参考 | 直接support偏好 | support平分时按block仲裁 |
|---|---|---|---|
| `S_ref` | 是 | 不执行 | 不执行 |
| `S_full` | 是 | 执行 | 执行，严格保持第四轮S_cov |
| `S_support` | 是 | 执行 | **不执行，回到参考或原生相位** |

三者同一个Release宿主、同一个新Z3库，只用一个冻结配置选项切换。公平需要相同公共诊断，不要求S_ref故意做它不需要的在线评分来浪费时间。详细影子评分可离线重建，缺失则报告。

建议把新策略选择与原仲裁分开：

```cpp
enum class CoveragePolicy { ReferenceOnly, Full, SupportOnly };

struct CoverageChoice {
    bool canonical_phase;
    enum class Kind { Support, Avoid } kind;
};

// 纯函数；不修改quota、去重集、RNG或求解器。
std::optional<CoverageChoice> choose_coverage(
    const PhaseEvidence& e, CoveragePolicy p) {
    if (p == CoveragePolicy::ReferenceOnly || !e.complete)
        return std::nullopt;
    if (e.support[0] != e.support[1])
        return CoverageChoice{e.support[1] > e.support[0],
                              CoverageChoice::Kind::Support};
    if (p == CoveragePolicy::Full && e.block[0] != e.block[1])
        return CoverageChoice{e.block[1] < e.block[0],
                              CoverageChoice::Kind::Avoid};
    return std::nullopt;
}
```

这是拟实现逻辑示例，按现有命名空间/类型接入。由原有代码继续处理literal极性、去重、4次建议额度、64窗口、参考回退、正常传播和回溯。

### 6.2 不允许顺手改变的因素

不改变变量选择、原生RNG、继承值选取率、参考建议语义、soft/hard来源、同相位计额、support的位计数方式、去重键、relevance、B状态、CCSS算法/超时、交付和覆盖口径。

`S_support`在纯block差值时**不消耗覆盖quota，不标记相关Demand已尝试**；随后按原参考逻辑回退。它不能把avoid伪装成support，也不能因为配额被腾出就将总额度从4增加。

若support两侧相等且都大于0，`S_support`也回退；这是有意删除block tie-break，不再加另一个规则挑选相位。

### 6.3 验证与日志

测试三种模式在关键分支的输出：正向support差、仅block差、support相等且非零、完全平分、不完整映射、参考true/false/unknown、NOT极性、额度耗尽、重复目标、同相位、回溯重试、暴露取消。

`S_full`必须在受控固定输入下保留第四轮的建议序列与RNG序列；去掉新日志后行为不变。`S_support`差异只允许从一次被禁用的block仲裁开始。无需要求具有墙钟退出的所有真实会话逐模型完全一致。

本轮命中判据是合法最终模型与冻结官方访问器的新增观察，不强制要求复合门自身有直接理论assign_eh记录。缺少间接理论链依旧标unknown，但不抹掉已独立验证的目标实现。

### 6.4 W输出

每实例三模式都输出：正式/原始/重复模型数、来源、完整会话覆盖、共同样本前缀、共同时间点、G1/G2/G3覆盖分解、首次观察、support/avoid机会与额度、命中、CDCL/CCSS/观测日志成本、完整CPU/墙钟。

`S_support`比`S_full`好，只支持“本实现中block tie-break可能有代价”；还要看是否超过同宿主`S_ref`。任何结果都不等于超过冻结完整HighDiv。

---

# 任务 X：独立定位 CDCL→CCSS 交换造成的长时间失败

## 7. 需要定位的对象，不是“上一模型”这个模糊概念

实际链路至少有以下对象，必须分别保存：

```text
宿主收到的CDCL模型
  ≠ 自动等于 ast_manager::last_CDCL_model
  → 实际进入build_instance的map
  → 各CCSS变量可读取的模型值/缺项/转换失败
  → 单变量初始化区间及补集选择
  → 初始_solution、RNG状态、未满足子句
  → 后续CCSS搜索
```

`last_CDCL_model`按字符串名索引，写入只覆盖当次实际相关且可见的声明。不能未经检查断言它是完整、最新、无辅助变量的正式原变量模型。也不能仅凭发现旧键就断言这是bug：旧键是否被消费、值是否适用，需要证据。

以下均需要查实际应用补丁后的源树：

1. `z3/src/smt/smt_model_generator.cpp` 中实际写入 `m.last_CDCL_model[...]` 的全部位置。
2. `z3/src/ast/ast.h` 的容器声明，以及全树所有clear、赋值、更新和跨manager转换。
3. `context::setup_and_check()` 的 `expr_bool_var_map / build_instance / ls_sampling` 调用链与异常分支。
4. `ls_sampler::build_lits()`、`build_instance()`、`calc_var_intervals()`、`initialize()`、`construct_solution_score()`、`ls_sampling()`及其实际search循环。
5. `choose_value_for_pair / print_var_solution / mk_model_sampling` 与原有模型恢复路径。

输出 `transfer_call_graph.zh.md`：给出实际函数、参数单位、timer起点、RNG建立/重置位置、map读写作用域。不能只复制本指引中的预期图。

---

## 8. 捕获点、来源和日志契约

### 8.1 捕获会话与检查点固定

在W的convert三模式中都安装相同的只读捕获；X主要使用`S_ref`、`S_full`的**第二次CCSS调用**（按现有混合流程通常是query=4）。用角色与序号选择，不按“哪次最慢”事后选点。

从进程开始跟踪map生产者，保留第一次和第二次CCSS入口快照。仅第二次进入交叉矩阵。若该调用未发生、上游查询先超时或记录不完整，则记录`capture_missing`并停止相关矩阵，不追加宿主捕获。

将新会话query=3的正式模型哈希、参考集合、query=4 seed、结果和时间与第四轮比较。历史完整map未记录，不能声称恢复历史完整状态。没复现59秒也照实保留，不能重新运行到出现慢例。

### 8.2 生产者快照

新增只读接口示意：

```cpp
void note_exchange_write(const ProducerId&, const DeclIdentity&,
                         std::string_view raw_value,
                         const GenerationId&);
void snapshot_exchange(const ExchangeMap&, const ConsumerId&, TraceSink&);
```

在原有写入发生时，旁路记录：manager/模型生成批次/外层query/叶子provider/原生角色、声明身份、名称、sort、raw字符串、写入或覆盖、是否hidden/relevant、源阶段。

禁止额外调用 `get_model()`、强制model completion、求值新项或修改map来制作日志。日志中的排序只能作用于拷贝，不改变生产容器或构造顺序。不用进程地址充当跨进程稳定身份；使用generation与语义字段。

消费点保存：

```text
实际map完整原始键值与稳定内容SHA
生产者来源表与每键最后写入批次
本次新写/前代残留/来源未知/从未被消费键
宿主正式模型哈希（单独字段）
原生参数、CCSS seed、实际超时及单位
父会话剩余墙钟、请求起止与退出原因
```

所有map捕获必须先做副本；对底层哈希桶/遍历顺序，如果源码确实只按键查找，可记录这一审查结论；如果有依赖迭代顺序的代码，必须同时保存并复现插入/遍历语义。不能假定排序后的JSON天然足够重放。

### 8.3 构造配方与确定性状态

优先使用**原生构造配方重建**，不复制内存地址，不对带watchdog线程的进程fork，不memcpy不可拷贝的`ls_sampler`。

拟新增：

```cpp
struct CcssConstructionRecipe; // 稳定值数据，不含指针
CcssConstructionRecipe export_construction_recipe(...);
std::unique_ptr<ls_sampler> rebuild_from_recipe(
    const CcssConstructionRecipe&, const ExchangeMap&, ProbeSink&);
```

至少记录：

- 原生constructor参数、seed、实际所有非默认配置，包括`_use_interval_move`等影响路径的值。
- `make_lits_space`参数与**实际顺序**的`build_lits`输入；原生variable/literal/clause身份。
- `build_instance`入口前原始`clause_vec`及顺序。它会被原生函数修改，每次重放必须从新副本开始。
- 构造后变量、literal、clause、硬界、差分变量对、重构栈、closure与occurrence信息的结构摘要。
- 原生mt的完整序列化状态，而不只是seed；记录标准库/编译器版本。
- 相关timer、资源限制、异常状态、正常停止判据。
- 后续恢复原变量所需的原生转换/重构信息。

应通过同一生产`build_lits/build_instance`函数重建，避免另写一个“类似的CCSS”。如果构造配方仍漏掉历史可变状态，显式补充稳定值序列化；不能以“同seed”为由忽略。

### 8.4 四个RNG/状态边界

```text
R0：新CCSS构造入口
R1：calc_var_intervals之前
R2：calc_var_intervals之后
R3：首次initialize完成、首次搜索步之前
```

用流序列化或复制后序列化保存mt，**不通过调用mt()取样来测状态**。保留每阶段摘要；计数器也不能调用新随机数。

不同map可能让`random_complement`消费不同数量的随机数。因此交叉map的后续RNG分叉本身属于map效应，主实验不强行重置它。不能把这种总效应进一步说成“只由区间宽度造成”，除非另有证据。

---

## 9. 初始化与搜索诊断：实际在哪里花时间

### 9.1 分阶段计时

至少分离：

```text
宿主LS调用前的准备
expr_bool_var_map / literal构造
build_instance不含calc_var_intervals
calc_var_intervals
initialize（值生成、literal统计、clause统计可再分）
原生search循环
正常重启/重新初始化
模型重构和验证
日志/输出
```

使用不重叠的主阶段字段；嵌套分项明确标注，不能把它们重复相加。父进程墙钟、原生CCSS计时、宿主LS调用计时同时保留。

`context::setup_and_check()`可能捕获异常后统一返回Unknown；诊断旁路必须保留原始退出原因：原生cutoff、外层取消、整数域异常、溢出、停滞耗尽、构造失败等。无法识别则原样unknown，不强归为“搜不到”。

### 9.2 对每个CCSS整数变量记录

在`calc_var_intervals()`及`construct_solution_score()`中记录原生已算出的中间量，不重复执行随机选择：

```text
稳定变量名/索引、原声明或辅助/差分来源
is_lia/in_equal_closure/in_occs_closure/occs
low_bound/upper_bound/s_lower_bound/s_upper_bound
模型值：present/missing/parse_error/128bit_overflow
_new_var_的原生pair_x/pair_y映射与差值是否成功
参与初始化的有效不等式数、未知/溢出的不等式数
clause_intervals、按原流程合并后的feasible区间
选择feasible或complement的分支
最终初始化区间、空区间回退到domain的原因
实际初值、RNG阶段摘要
```

全部整数用精确十进制字符串；不能用double计算巨大区间宽度后比较。单变量保留部分真实literal的区间，不自动等于整个公式的联合可行域。

要核验：区间端点与选值在硬界内、负数整除边界、空区间回退、缺失值未伪造为0、差分变量值正确、数组索引和序列化长度一致。若发现真正确性问题，停止搜索性比较，保存最小复现；不修完后继续把旧数据算进同一冻结版本。

### 9.3 搜索进度而不轰炸日志

复用原生变量和计数点，记录：

- 初始未满足子句数及分类型计数、原生best cost。
- 首次改善时间/步数，best cost变化序列，最长无改善段。
- `_step`、`_outer_layer_step`，实际Bool/LIA切换、restart/initialize、random walk、权重更新、溢出计数。
- 原生停止原因和最后阶段。

阶段边界记录完整摘要，循环中仅在best改善、原生重启及预先指定的步号（1、2、4、8……）记有界摘要；不逐move打印模型。不为诊断增加新搜索动作或“修复”步。

如果第一个SAT模型已经找到，记录真实找到时间、步数、原生验证和重构情况。不要为凑满60秒继续搜索。

---

## 10. X1：先证明重建可信，再交换map

两个捕获输入分别称：

```text
H_ref：来自convert/S_ref第二次CCSS的非map构造配方与固定参数
M_ref：该入口实际消费的完整map
H_full、M_full：来自convert/S_full的对应对象
```

构造与初始化重放不启动额外SMT或局部搜索循环。允许通过正常原生initialize生成初值，然后在首个搜索步前退出。

对各自对角输入验证：

1. 变量/literal/原始及约简clause顺序、closure、pair与重构结构一致。
2. R0/R1/R2/R3摘要一致。
3. 模型值读取状态、初始化区间、初始_solution、未满足子句集合一致。
4. map实际消费集合及值一致。

允许对不可稳定的地址、绝对时间做明确排除；不能排除会影响搜索的字段。若无法建立一致性，输出`reconstruction_not_validated`，停止对应交叉矩阵。不要把不一致的重建跑得很久来“验证最终结果差不多”。

如果捕获过程中外部诊断改变了截止，先比较确定性的公共步前缀，不强求墙钟完全相同。此处也不是历史HighDiv完整状态克隆，只是当前捕获的CCSS输入/初始化重建。

---

## 11. X2：只改变map的交叉矩阵

固定以下8个运行ID，在执行前提交计划：

| ID | 非map配方 | map | 目的 |
|---|---|---|---|
| X_rr | H_ref | M_ref | 原生对角 |
| X_rc | H_ref | M_full | 固定H_ref，只换map |
| X_cr | H_full | M_ref | 固定H_full，只换map |
| X_cc | H_full | M_full | 原生对角 |
| X_r0 | H_ref | 空map | 无CDCL初始化信息的诊断对照 |
| X_c0 | H_full | 空map | 同上，另一个配方 |
| X_rr_repeat | H_ref | M_ref | 预先指定的确定性核验 |
| X_cc_repeat | H_full | M_full | 预先指定的确定性核验 |

每行都是新进程/新CCSS对象；从原生构造入口执行，不能在上一个对象上覆盖map继续跑。`ls_sampler`本身禁止拷贝，不能偷用浅拷贝。

在同一个H内，seed、R0状态、所有非map参数、子句/literal顺序和cutoff固定；允许map改变后续区间、RNG消费和搜索。这是“固定构造输入中的map总效应”检验。

若H_ref与H_full本身相同，两个行块仍保留为独立来源的冗余验证。若不同，不能跨行块把耗时差全部归map；主因果比较是X_rr↔X_rc和X_cr↔X_cc。

空map是独立诊断控制，不是建议上线清空map，不给丢失变量补0。只验证原生产代码在无模型初始化信息时如何自然回退。

### 11.1 输入兼容性

在对方H上使用map前，核对值所指变量/辅助名是否有相同语义。跨manager的相同字符串名不自动意味着同一内部变量。无法验证的辅助项不得默默删除或改名后声称“只换map”；应记`incompatible_recipe_map`，停止该格，或仅报告原生对角与语义明确的空map对照。

副本中包含未被消费的多余键可以保留并统计，不为让结果更好而精简。需指出map对当前CCSS仅是初始化信息，不保证是完整合法赋值；输出的解仍必须由原生约束验证。

### 11.2 有限重放输出

各格至少报告：实际map读集/缺项、区间差异、RNG最早分叉边界、初始_solution差异、初始未满足子句、best改善曲线、SAT/原生失败/父进程截止、time/steps to first solution、完整耗时与上限。

无解返回/timeout只是本次有限搜索没有交付，绝不报告UNSAT。不同map下发生不同溢出或构造异常，也必须原样保留，不能归并成“搜索慢”。

所有重放得到的候选先用原生`check_solution()`与相关内部约束核验，再按原生差分/布尔重构及已保存模型converter恢复原变量，独立检查F和官方覆盖。若只能验证约简CCSS公式、不能可靠恢复原变量，应明确标为`ccss_solution_only`，不得当作正式合法输入。所有这些模型都不进入W或历史采样集。

### 11.3 可以和不能得出的结论

- 同一H中更换map导致稳定初始化/搜索差异，且对角一致性通过：支持该捕获案例中的交换map作用。
- 慢状态跟随M_full跨两个H出现：强化map相关解释，但仍只是本例、此seed。
- 只有某H慢，无论map：优先查结构、预处理或其他状态差异。
- 区间变了、初始状态变了、但有限搜索表现不变：有机制影响，没有速度影响证据。
- 初始状态相同、固定步前缀相同，墙钟却不同：先查系统资源、计时/诊断；不能归模型。
- 原生对角重建失败：停止因果解释。
- 本轮没有复现历史长调用：保留“历史现象未被本次捕获重现”，不得删除失败证据或重新选择检查点。

---

## 12. 不提前修复的几个CCSS风险，要先获得证据

### 12.1 旧map条目与生产者混合

审计全部write/clear操作，输出每个消费键的最近生产者。若当前批次没写某键但map仍有它，先验证消费语义是否需要该值、是否与当前模型/约简变量对应。

只有确认旧信息被不当消费，才提出“原子性替换交换快照/明确缺项”的后续修复。不能本轮直接清空map并把改善包装成覆盖机制收益。

### 12.2 有限整数表示

现有CCSS使用精确检查的128位中间值和64位初始化区间。记录parse/overflow/fallback，不将原始QF_LIA解释为64位有界语义。诊断脚本用任意精度交叉核验关键转换。

### 12.3 补集初始化可能刻意偏离CDCL模型

高频变量、普通变量、等式closure的初始化规则不同；普通变量可能选择模型可行区间的补集。这是原HighDiv策略的一部分，不能把“初值离CDCL更远”直接当bug，也不能因为初始化未满足子句多就断言必慢。

需要证据连接：实际map值 → 哪些区间/补集变了 → 哪些初值/子句变了 → 后续改善/停滞行为。不要仅用数值距离推断覆盖或运行时间。

### 12.4 全程成本不等于相位回调成本

W中CDCL改变可能影响随后CCSS调用乃至下个参考模型。这些都保留在完整策略成本中，不能从S_support/S_full比较里扣除。X的重放隔离只是定位原因，不是免费替新方法免去后续负担。

---

## 13. 正确性、非侵入性和诊断质量测试

至少覆盖：

1. `S_full`固定输入回归；`S_support`仅在block tie-break时改变建议资格。
2. 位状态、负数、第63位、原AST短路、共享节点、精确原变量身份与官方观察一致。
3. 4次quota和64窗口跨tactic叶子/重启共享；同相位、去重、仅avoid、参考unknown与false均正确。
4. 无新增B表达式/断言/literal/relevance标记，真实硬约束和soft reference来源不变。
5. 日志开/关在无墙钟截断的合成输入上，原生决策、RNG、交换map、初始化值与模型相同。
6. 交换map原始字符串、缺项、超128位值、负数、辅助差分变量、空map的读取与序列化往返。
7. 构造配方往返后结构与RNG一致；对不可拷贝类不用memcpy；每次运行fresh对象。
8. snapshot不调用`mt()`/额外get_model，不改变map，不改变clause顺序。
9. trace缓冲溢出、EOF、模型文件截断、超时/取消均有明确状态，缺记录不能记为0。
10. 所有新候选的原式合法性、变量投影、去重、收据、及时交付和官方精确覆盖审计。

Release与ASan/UBSan分别通过。保留既有精确的上游32字节泄漏例外，禁止扩大抑制以掩盖新问题。查到非法模型、未定义行为或不匹配输入指纹时，不继续性能解释。

测试计划事先编号；构建/测试失败现场保留。编译和审计的工程失败可以修复，但不能反复重跑已执行的W/X会话挑选正例。

---

## 14. 结果表和必须回答的问题

### 14.1 必须交付的数据文件

```text
readonly/coverage_bit_partition.csv
readonly/advice_quota_audit.csv
readonly/old_log_missing_fields.json
analysis/W_performance.csv
analysis/W_prefix_comparisons.csv
analysis/W_coverage_partition.csv
analysis/W_advice_funnel.csv
analysis/W_target_uniques.csv
analysis/W_quota_opportunities.csv
analysis/X_capture_fidelity.json
analysis/X_producer_consumer_diff.csv
analysis/X_initialization_diff.csv
analysis/X_replay_results.csv
analysis/X_search_progress.jsonl
analysis/root_cause_matrix.csv
analysis/next_change_decision.json
BASELINE_UNCHANGED.json
audit_summary.json
```

每个结论关联run/query/action或重放ID、源码函数及原始文件SHA。缺失数据为NA/unknown，不能把未执行或未记录填0。

### 14.2 最终中文报告必须回答

**W部分：**

- 现有coverage建议中，弱avoid实际占多少决策/额度，而不是多少展开bit记录？
- 是否挤占直接support？拒绝原因是否只有quota？
- 自选目标成功是否掩盖G2/G3等集合外损失？具体哪类值/访问/模型来源受到影响？
- 支持-only是否改善同样本覆盖、完整短会话覆盖和总成本？超过S_ref还是仅超过S_full？
- 如果没有改善，是没有可执行support、support自身不兑现，还是供给/其他位置损失抵消？

**X部分：**

- 第二次CCSS实际消费的map与正式CDCL模型有何不同？是否混入未核实的历史来源？
- 长时间发生在构造、区间、初始化还是搜索循环？实际退出原因是什么？
- 只换map是否让初始化/停滞/时间变化跟随map？同一H的输入与RNG控制是否可靠？
- 影响是通过区间、初值、缺项/溢出、RNG消费，还是尚未定位？
- 历史59秒是否重现？未重现就保留未知，不编造根因。

**综合部分：**

区分至少三层：

```text
局部目标观察有效
完整短会话的模型质量/供给有效
相对完整HighDiv的性能优势
```

本轮不运行完整HighDiv，也没有新的900秒矩阵；最后一项只能引用历史参考与明确局限，不能宣称已经完成最终验证。

---

## 15. 根据证据选一个下一步修改，不能默认把所有建议一起实现

| 新证据 | 合理的后续方向 | 当前不能声称 |
|---|---|---|
| avoid占额且support-only在共同样本和成本上改善 | 限制弱avoid、给support保留机会；冻结一个简单版本进一步验证 | 所有avoid必然无用 |
| 主要浪费来自同相位额度或去重前评分 | 下一轮单独检验计额/重算修复 | 本轮support-only结果已证明该修复 |
| support-only仍损失G2/G3，而自选目标增加 | 研究降低覆盖干预频率/保留全局探索，或扩大有意义的目标表达 | 自选池命中提高就是成功 |
| 单纯放软后CDCL重复很多 | 独立研究参考的多样性与继承强度，不重启硬锁定全部目标 | 减少硬约束必定提升采样 |
| 在可靠重放中慢状态跟随实际交换map | 研究交换信息质量判据、初始化保护或有界回退 | 删掉CCSS/清空map必定更好 |
| 确认不当跨代键、声明或数值转换 | 优先修交换契约的正确性，单独回归 | 是覆盖启发式本身不行 |
| 同初态仍有明显不稳定或未复现 | 先补足状态/资源解释，停止扩大搜索 | seed相同即已完成强因果对照 |
| 两条任务都没有足够证据 | 给出有边界的负结论和缺失项，归档结束 | 继续追加参数/seed直到出现好结果 |

`next_change_decision.json`选择0或1个首要改进方向，并写：依据、预期改善的指标、需要保留的对照、失败判据。另一方向可以列为未优先事项，但本轮不自动实现第三套策略。

---

## 16. GitHub与最终交付

独立分支按阶段提交：只读分析与协议 → W/X代码和回归 → 冻结W结果及捕获 → X结果与审计 → 中文报告和归档。

上传新增源码、实际补丁、配置、版本/二进制/输入哈希、全部尝试、官方输出、精确位计数、模型收据、map/recipe/RNG/初始化快照、重放负结果和正确性日志。大型数据无损压缩分片，逐分片及全部成员SHA校验，并实际解压核验。

不上传构建树、第三方二进制、凭据；原输入仍按前轮权限只保存哈希与来源。归档恢复须能在克隆仓库后重建本轮全部证据，不得只给本机绝对路径。

历史基线不重复上传、不重跑。检查其保护SHA、attempt记录与受保护文件未变化。推送使用正常非强制Git操作；用`git ls-remote`核验远端提交。推送失败时保留本地提交并明确错误，不能声称已上传。

最终答复包含：完成/未完成数量、W各模式全式与分区差值、真实建议和额度结论、X交叉表、捕获/重建可信范围、非法/失败/Unknown数量、唯一优先改进方向、提交SHA及报告路径。

不要把“所有测试通过”当作机制或性能成功。目标是给出**可操作的原因定位与下一项有证据支持的修改**；零收益和未能定位同样完整交付。

---

## 17. 源码与证据索引

以下是撰写本指引时读取的固定来源。执行时以基点下实际文件及应用补丁后的哈希为准。

1. [第四轮中文报告](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550/docs/round4_mapping_and_soft_reference_results.zh.md)
2. [第四轮相位执行](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550/src/round4/soft_phase.inc)
3. [support/block评分](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550/include/round4/soft_reference/phase_evidence.hpp)
4. [CCSS成本与实际源树信息](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550/results/round4/analysis/CCSS_cost_source.json)
5. [共同需求池](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550/results/round4/analysis/S_comparison.json)
6. [冻结HighDiv sampler.cpp](https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/sampler/sampler.cpp)
7. [冻结HighDiv sampler.h](https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/sampler/sampler.h)
8. [冻结模型生成器](https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/smt_model_generator.cpp)
9. [冻结SMT context](https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/smt_context.cpp)

本文件是执行协议与拟实现接口，不是第五轮已完成结果。除引用的第四轮数据和源码事实外，根因判断、support-only收益、map交换效应均必须由本轮实际证据回答。
