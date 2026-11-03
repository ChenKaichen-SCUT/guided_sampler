# Guided Sampler 保留新增观察的模型改进实现与实验指引

工作仓库：`https://github.com/ChenKaichen-SCUT/guided_sampler`。

已核对的第五轮基点：`ae85956068154207a442c0e2c8387c573dc32411`；固定上游 HighDiv：`f2c6e1756b13281d96cbf90a8bd940129e56cce4`。建议独立分支：`observation-preserving-refinement`。本文件不预设第六轮已经实施或成功。

**执行目标：实际完成代码修改、正确性验证、有限机会实验、符合晋级条件的性能实验、独立审计、中文报告、无损归档及独立分支推送。不要只返回另一个计划。** 本指引本身是待执行协议，并非已完成的实现或实验报告。

研究一个机制：原生生成器先产生合法模型；独立改进器在有限预算内寻找更有价值的替代模型；替代模型仅用于输出，原生模型及原生交换状态继续驱动搜索。每次替代必须保留原生模型相对于当前输出历史新增的全部实际观察。

要回答两个不同问题：

1. 能否低成本找到满足上述保留条件、并增加全式 covered bit 的模型？
2. 将改进器接入完整混合采样器后，额外成本是否仍允许等时间与等样本覆盖同时提高？

## 1. 先冻结边界和来源

### 1.1 需要读取的冻结证据

先读取并按仓库恢复说明核验以下材料，不重新执行旧正式队列：

1. `docs/round4_mapping_and_soft_reference_results.zh.md`。
2. `docs/round5_weak_targets_and_ccss_results.zh.md`。
3. `docs/round5/transfer_call_graph.zh.md`。
4. `manifests/round5_implementation.json`、`manifests/round5_W_evidence.json`。
5. `archives/round5/RESTORE.md`及对应逐成员哈希。
6. 第一轮完整 HighDiv 的冻结 16 项正式结果、8 个输入及官方 `calc_metric.py` 哈希。

第五轮已确认：convert 的共同前三个模型 Full 比 Ref 多 492 个 covered bit，但完整会话少 8789 个；random/real 在相同八模型下分别少 94/264 个。convert 的固定 CCSS 构造中，替换实际消费 map 可使 219 步成功变成 52 秒未成功。因此本轮同时处理模型贡献与反馈状态耦合，不能仅用更多目标命中宣称成功。

当前仓库保存补丁而不保存完整上游树。通过既有准备脚本恢复固定上游，在新的构建副本上应用补丁；不要因为 Git 中没有 `HighDiv/src/...` 就另找最新上游替换。

旧第四、第五轮协议中的“禁止整数移动”等限制针对那些已冻结阶段。本轮明确实施上述输出端整数移动，历史协议仅用于恢复证据与保护旧结果，不阻止当前已经指定的新机制。

### 1.2 本轮原生生成器的定义

本轮主要生成器固定为第五轮 **Ref：软参考、无覆盖相位指导**。这里的“原生”指这个冻结生成器，而不是未经修改的完整 HighDiv。完整 HighDiv 是最终外部历史基线，两者不可混称。

默认不启用新 CCSS 守卫。如果已有第六轮冻结结果证明守卫的正确性、快解保留及有用的端到端产出，可在运行本轮实验前固定使用该守卫版本；所有本轮配置使用相同守卫设置，并记录提交、参数与选择依据。只有方案或局部重放通过，不足以称为已验证的共同基础。

**不得在本轮结果不理想后切换守卫、添加冷却、改交替比例、改相位评分或更换生成器。** 守卫尚未验证时，本轮仍可在守卫关闭状态完成；其停滞会作为生成器限制保留。先前第六轮协议的完整守卫矩阵不是本轮的隐含前置任务。

### 1.3 明确允许与禁止的修改

允许：独立原变量快照、完整观察评价、LIA 整数方向、一维精确可行域、缺失 bit 命中候选、输出选择、独立账本与预算、必要的宿主接入和审计。

禁止：向生产 solver 添加改进目标/保留约束，改变 CDCL 选变量/相位、CCSS 初始化/move/restart/map，改变原生参考来源或 RNG，使用在线 SMT/MaxSMT 生成候选，增加线程并把成本藏在后台，改变官方观察语义或分母，使用未来样本/离线 oracle 答案指导在线选择。

诊断用完整 SMT 比较仅按第 10 节固定清单执行，与生产求解器完全分开，模型不注入采样器。

## 2. 把保留条件写成精确契约

### 2.1 观察不是任意求值结果

观察身份固定为：

```text
BitId = (input_sha, original_node_id, bit_index)
Observation = (BitId, value_in_{0,1})
```

`original_node_id` 来自冻结原 AST 的稳定遍历及结构/声明核验，不使用跨 manager 的临时 AST ID，也不合并原节点与其 NOT。Int 观察低 64 位，Bool 观察一位；负整数先按数学意义归一化到模 2^64 的非负余数。公式合法性始终是 SMT 整数语义，不是 64 位机器溢出语义。

`total` 及可计观察点集合完全沿用冻结脚本。未支持的方向、被跳过的表达式、尚不可达的目标都不能从正式分母删除。

`observe_official(model)` 必须严格复用冻结脚本的节点访问次序、短路规则、DAG 去重规则、运算支持及常量计数口径。**未访问节点即使纯求值正确，也没有产生观察。** 不能为了方便改成全 DAG 所有节点都计分。

### 2.2 每次替代的必要条件

设 `S` 为本次处理之前已正式输出的模型集合，`seen(S)` 为它们产生的全部单侧观察；`m` 是当前合法原生模型。

```text
base_obs  = observe_official(m)
protected = base_obs - seen(S)

候选 q 可替代 m，当且仅当：
    q 满足原公式 F 及本次真实外部硬条件；
    protected 是 observe_official(q) 的子集；
    q 的完整原变量赋值满足输出去重与期限要求。
```

逐节点实现保护掩码：

```text
need0[n] = base_obs.zero[n] & ~output_seen0[n]
need1[n] = base_obs.one[n]  & ~output_seen1[n]

保留成立：
    (need0[n] & ~candidate_obs.zero[n]) == 0
    (need1[n] & ~candidate_obs.one[n])  == 0
```

没有访问到的候选节点，其 zero/one 都为零。检查顺序可先按保护掩码早退，再完整求值；最终接纳证据必须含实际 Reach。

本轮保护集合必须完整。不能只保留原变量、已 covered 位、G1、低位、被选择的目标，或随机抽取一部分保护观察。方向和候选数量可以有界，保护条件不能近似。

### 2.3 选择规则

相对于同一个 `S`，计算候选与原生模型各自的：

```text
gain_covered  = 新增双侧 covered 的精确 BitId 数
gain_observed = 新增单侧 Observation 数
```

在合法、保留、不同的候选中按 `(gain_covered, gain_observed)` 字典序选择。只有严格优于原生模型才替代；相同得分优先原生模型；候选间再以固定方向编号、参数绝对值、参数值排序。单侧观察增加可接受，但必须单列，不能冒充 covered 改善。

原生模型始终是回退候选。首个正式模型固定原样交付，不作改进，以保持起点与 G1/G2/G3 分区可比。原生模型合法且不同，即使 covered 增益为零仍按原规则处理。

### 2.4 必须实现的性质及其边界

对同一条输入原生模型序列，每一步输出要么保留当前原生模型新增的全部观察，要么该模型的全部观察已在输出历史中。归纳可得：处理完任意相同输入前缀后，输出观察并集包含该原生前缀的观察并集；因此双侧 covered 集合也包含原生前缀的 covered 集合。

归纳理由：已经见过的观察不会从输出历史删除；当前尚未见过的原生观察全部进入本次输出。保护集合必须相对于**改进后的输出历史**重新计算，不能永久使用旧 Ref 历史。

该性质不保证输出不同模型数不减，也不保证替代后的某个单模型包含原生模型的全部观察；已由早期输出贡献的观察可以在当前替代模型中缺失。它更不保证独立等时间运行必胜，因为额外开销、截止和内部超时可改变实际生成序列。期限前没有完成输出事务的最后一个输入不属于已完成前缀，必须单列。

## 3. 接入现有函数时保持两条状态路径

### 3.1 已核对的位置与新接口要区分

| 已有位置 | 本轮使用方式 |
|---|---|
| 生成树 `HighDiv/src/sampler/liasampler.cpp::LiaSampler::hybrid_sampling()` | 保留 CDCL/CCSS 路由与原生模型更新，在恢复完整原变量模型后的交付边界接入 |
| `include/round4/soft_reference/session.hpp::Session::commit()` | 其快照、合法性、去重、观察、收据和反馈现在耦合；需要有控制地拆分 |
| `scripts/patch_round4_host.py` | 展示软参考及 `m_ls = subgoal.convert_model(m_ls)` 后的原生引用记录接入点 |
| `collect_inherited_reference()`、`Session::ls_reference_source()` | 继续读取原生 `m_ls`，不得读取替代输出 |
| 生成树 `z3/src/smt/smt_model_generator.cpp::mk_values()` | 保留向 `ast_manager::last_CDCL_model` 的原有写入 |
| 生成树 `z3/src/sampler/sampler.cpp::build_instance()`、`calc_var_intervals()` | 保留实际交换 map 及其消费过程 |

第五轮构建还会生成自己的 `session.hpp`。以上头文件是已核对的源模板，不代表第五轮最终二进制直接包含它。实施前用编译依赖/预处理输出定位实际头文件，保存最终应用补丁树 SHA；禁止只改展示文件而未进入构建。

下面的类型与函数均为**建议新增接口，不是声称仓库已有 API**。

### 3.2 原生反馈与用户输出必须分开

维护两个相互独立的账本：

```cpp
struct NativeLedger {
    ExactModelSet unique;
    uint64_t accepted_count;
    NativeCoverageHistory coverage;
    // 原生反馈、参考选择资格、原生观察版本和动作结果仍由这里推进。
};

struct OutputLedger {
    ExactModelSet unique;
    uint64_t committed_count;
    ObservationHistory observations;
    // 只决定输出去重、正式覆盖、收据及 n20/n100 停止条件。
};

struct NativeAcceptance {
    bool legal;
    bool native_duplicate;
    bool accepted_for_native_history;
    uint64_t native_event_id;
    OriginalAssignment assignment;
    ObservationTrace trace;
};

struct DeliveryResult {
    bool committed;
    bool replaced;
    bool output_duplicate;
    DeliveryReason reason;
};
```

`Session::commit()` 原本返回的 bool、局部 `num_samples`、`unique`、`formal`、`guidance->commit()`、`formal_record()`、`pending_outcomes`、coverage version 及首次参考选择分支都要做数据流审计。凡参与后续搜索的，继续反映原生历史；凡代表用户收到的正式模型，反映输出历史。不能只拆开 map，而让输出数量或覆盖账本间接改动后续原生搜索。

对 Full 诊断配置，原生覆盖相位仍只读取自己的原生历史。对 Ref+改进配置，输出覆盖只提供给独立改进器。旧 action 的命中反馈也只能根据原生模型填写，不能把改进器后来得到的命中归给原生 action。

保留原生重复处理规则：原生去重判为重复时，本轮不额外启动改进。原生模型已通过原生去重、但恰好等于较早的某个替代输出时，输出侧应独立判断：若无新候选且原生模型已经输出过，记录输出重复，不增加正式样本数。此时它的观察已经被输出历史包含，不破坏前缀性质。

候选等于已输出模型时不替代；如果原生模型还未输出，回退原生模型。不能从输出重复倒推原生重复，不能靠双重输出 `m` 和 `q` 凑足样本数。

### 3.3 推荐调用顺序

```cpp
// 伪代码：按真实调用链拆分，不能机械替换旧 commit 返回值。
void on_original_model_ready(NativeModel const& original) {
    auto native = extract_validate_and_accept_native(original);
    // 快照补全规则与原生有效约束均保留；不修改 original。

    apply_native_feedback_at_original_boundary(native);
    // map/m_ls 等已有更新仍在原位置；此处不得重复更新。

    if (!native.accepted_for_native_history) {
        record_native_rejection(native);
        return;
    }

    auto choice = identity_choice(native.assignment, native.trace);
    auto output_version = output.observations.version();
    if (!is_first_native_model() && refinement_budget.can_start()) {
        choice = refiner.try_refine(native, output.snapshot(), budget);
    }

    // 单线程执行；版本不一致应判实现错误，不能使用过期保护集合。
    require(output.observations.version() == output_version);
    recheck_choice_or_fallback(choice, native, output, budget);
    auto result = commit_output_transaction(choice, native.native_event_id);
    // 只有及时完成事务，才更新 output.unique / observations / count。
    record_delivery_result(result);
}
```

完整流程不得把候选写回 `m_ls`、solver model、`last_CDCL_model`、软参考、blocking 条件或采样 RNG。不要在改进器中调用 `check()`、`model.eval(..., true)` 修改原生模型，或借用原生 Z3 manager 构造新表达式。复制后的纯数值赋值与独立只读原 AST 表示即可完成改进。

既有补全策略在独立快照中为未定义 Int/Bool 填入 0/false，必须继承并验证完整原式；这不授权对内部交换 map 缺项补零。两者语义不同。

### 3.4 隔离验收

在合成实例与固定操作数测试中，比较 Ref 与接入后的 Identity 模式：原生模型序列、宿主 RNG 序列化、CCSS seed、实际 map 写入/消费、参考集合、原生接受数、下一次查询输入必须一致。Identity 只输出原生模型。

另加入至少一个**确实发生替代**的合成运行，验证替代后原生轨迹仍一致。否则“关闭时一致”没有验证隔离机制。

使用固定调用数和足够宽的时间边界检查确定性；墙钟限时真实运行只比较可核验公共前缀，不要求整段相同。哈希仅用于定位，关键差异用完整序列、map 键值和状态内容核验。不宣称上述记录覆盖了全部 Z3 内部状态。

## 4. 新模块与函数职责

建议新增 `include/refinement/`、`src/refinement/`、`scripts/refinement/` 和 `tests/refinement/`，不要覆盖历史轮次文件。

```cpp
using BigInt = boost::multiprecision::cpp_int;

ObservationTrace observe_official(OriginalAst const&, OriginalAssignment const&,
                                  CancellationToken const&);
ProtectedObservations make_protected(ObservationTrace const&, OutputSnapshot const&);
bool preserves(ProtectedObservations const&, ObservationTrace const&);
CoverageGain marginal_gain(ObservationTrace const&, OutputSnapshot const&);

CompileResult compile_affine_ir(OriginalAst const&, WorkBudget&);
EqualitySystem collect_mandatory_equalities(AffineIR const&);
DirectionPool build_integer_directions(EqualitySystem const&, WorkBudget&);
DirectionList select_directions(DirectionPool const&, OutputSnapshot const&,
                                uint64_t native_event_id, WorkBudget&);
LineDomainResult formula_domain_on_line(AffineIR const&, OriginalAssignment const&,
                                        IntegerDirection const&, WorkBudget&);
HitResult nearest_modular_hits(AffineTermOnLine const&, BitTarget const&,
                              IntervalUnion const&, WorkBudget&);

CandidateResult evaluate_candidate(OriginalAssignment const&, ProtectedObservations const&,
                                   OutputSnapshot const&, WorkBudget&);
RefinementResult try_refine(NativeAcceptance const&, OutputSnapshot const&, WorkBudget&);
DeliveryResult commit_output_transaction(ChosenModel const&, uint64_t native_event_id);
```

`ObservationTrace` 保存每个实际访问节点的值位掩码，不能只保存 `new_covered` 标量。`OutputSnapshot` 是只读快照。临时评价不更新历史；只有正式输出事务提交后才 `commit`。所有候选以同一个原生 `m` 为锚点，本轮不追加多轮贪心爬山或从已改进候选继续展开。

候选生成器与观察器是纯数值模块，首版不读取求解器 tableau。以后复用 tableau 方向需要单独证明坐标还原与无副作用，不能把未经验证的内部自由变量直接当原变量方向。

## 5. 利用 LIA 等式产生整数方向

### 5.1 只提取必需等式

首版仅从原公式顶层合取的递归展平结果中收集显式仿射整数等式。可做精确、保序的语法识别，不新增求解调用。

例如 `(and (= (+ x y) 15) (or (= x 0) (= x 10)))`：`x+y=15` 是必需等式，两个 OR 分支的等式都不是。不能将当前模型恰好满足的分支等式全部锁住。

将必需等式写成任意精度整数系数的 `A*x=b`，方向满足 `A*d=0`，于是 `m+t*d` 保留这些等式。每个输出方向都必须代回**全部已提取等式**精确核验，不能只验证参与局部构造的几行。

### 5.2 有界、确定性的方向构造

1. 按等式变量关联分量拆分；不出现在必需等式中的原整数变量可产生单位方向。
2. 对不超过 64 个变量、128 行、4096 个非零系数的分量，采用精确稀疏有理消元；为每个自由变量生成一个有理零空间方向，清分母后除以系数 gcd，得到本原整数方向。
3. 超过上述规模或消元预算时跳过该分量并记录原因；其他分量继续。不能转为浮点近似或把未处理等式丢掉后宣称保持可行。
4. 分母清除后的方向保证是合法整数方向，但不声称它们生成完整的整数核格。本轮不引入 Smith/Hermite 标准形，也不因此声称完整枚举所有可行移动。
5. 方向统一首个非零系数为正，去重，剔除零向量。系数超过 4096 bit 的方向跳过，原生模型仍照常输出。

方向池的构造顺序按稳定原变量编号固定；一次最多保留 256 个方向。超额分量使用固定轮转分配，记录未纳入的分量和方向数；不要让单个大分量耗尽全部容量。

每个原生模型最多选 16 个方向：按受影响的尚未双侧覆盖的官方 BitId 数排序，保留前 8 个；另 8 个从剩余池按 `native_event_id` 循环取，去重补位。影响关系是便宜的结构估计，不是假定目标可访问或可实现；同分按稳定编号。全式 G1/G2/G3 都可影响该结构计数。

本轮不增加随机方向、系数范围搜索或方向组合。若方向不足导致失败，应形成下一轮证据，而不是在正式实验中临时扩展。

## 6. 沿方向计算原公式的一维可行域

### 6.1 数值语义与支持范围

对原模型 `m` 和方向 `d`，候选是 `x(t)=m+t*d`，其中 `t` 是任意精度整数。原 Bool 变量首版固定为 `m` 中的值；算术比较产生的布尔结果可以随 t 改变。

首版精确支持：整数常数、原整数变量、加减、取负、乘整数常数组成的仿射项；`=、distinct、<、<=、>、>=`；原公式中的 AND、OR、NOT、蕴含、XOR 和布尔 ITE。多元关系按其实际 SMT 语义展开。数值 ITE、div/mod、非线性项和其他算子若依赖被移动变量，返回 `unsupported_on_direction`。

不受当前方向影响的非仿射子项，可以用原模型的精确值作为常量，前提是通过依赖分析证明其全部自由变量均不变，并且已有精确求值器支持其原语义。不能将一个会变化的 div/mod 或 ITE 用当前值冻结。

不支持整个一维域不等于原公式不支持采样；直接跳过该方向、保留原模型。报告必须列出各真实实例受支持方向比例，不能只在少量可处理公式上报成功率。

### 6.2 规范化的整数区间并集

每个仿射项沿方向写成 `c+a*t`。线性原子转换为整数区间、单点、两个半无限区间或空集。例如：

```text
c+a*t <= 0，a>0：t <= floor((-c)/a)
c+a*t <= 0，a<0：t >= ceil((-c)/a)
c+a*t = 0：a=0 时为全域/空域；否则检查 -c 是否被 a 整除
```

实现数学意义的 `floor_div`/`ceil_div`，不得直接采用 C++ 向零截断。所有无穷端点用显式类型，禁止拿最大 int64 代替。

AND 取交，OR 取并，NOT 在整数全集上取补。对布尔 DAG 缓存语义域，计算真值所需的域不等于官方短路访问域。先求合法 t，最后仍按官方访问器评价观察。

区间有序、互斥且合并相邻整数区间。最多 4096 个区间、每方向最多 200000 次域操作；超限返回 `domain_budget_exhausted`，**不允许截掉部分区间后声称结果是完整域或空域**。

每个支持方向必须确认 `t=0` 在域内；否则是原模型/硬条件/域计算不一致，停止性能实验并修复。输入真实硬条件也必须与 F 一起参与域计算。

本轮主候选使用完整区间并集。`component_only` 离线消融只取包含 0 的连通整数区间，用来检查跨 OR 分支是否有实际价值。不要将这个局部区间偷偷作为主实现的全部可行域。

### 6.3 必须通过的跨分支例子

```text
F = (x+y=15) AND (x=0 OR x=10)
m = (x=0, y=15)
d = (1,-1)
合法参数集合恰好为 {0,10}。
```

主实现必须能提出 `t=10`，即使 1 到 9 都不合法。只沿当前分支滑动的实现会漏掉它。最终是否替代还取决于当前输出历史的保护条件和完整官方观察，不能把“可行”当“保留且更优”。

## 7. 从缺失 bit 直接计算少量参数

### 7.1 目标和候选规模

目标优先取当前输出历史只见一侧的 bit，且原生模型本次没有补齐该位。每个方向最多 8 个目标；按稳定节点/bit 顺序形成列表，以 `native_event_id` 循环窗口取，避免永远只看最前面的节点。

两侧未见不设置位值偏好，但这些节点在候选真实评价中仍贡献新增观察；两侧已见不再作为目标。目标项必须在该方向上有精确仿射表示。Bool 比较目标可以直接使用其真假域；原 Bool 变量因固定而无移动机会。

每个方向—目标最多提出 4 个非零参数：正向两个最近命中、负向两个最近命中，遍历完整合法区间并集，按绝对值排序。全事件最多完整评价 64 个不同赋值。候选调度先让各方向获得一次机会，再轮转其余目标；不能让第一方向吃完额度。

先将域按 `t>=1` 和 `t<=-1` 切分，分别从靠近 0 的端点搜索；不能在包含 0 的无限区间上选择不存在的“左端点”。受预算限制只处理部分区间时标为未完成搜索，不得报告整个目标无解。

所有候选保留原始锚点 `m`；去重使用完整原变量赋值。`t=0` 已由回退模型代表，不重复消耗候选额度。

### 7.2 模区间命中的精确实现

整数项为 `v(t)=c+a*t`，位号为 b。令 `M=2^(b+1)`；目标 0 对应余数区间 `[0,2^b-1]`，目标 1 对应 `[2^b,M-1]`。余数采用非负 `floor_mod`，因此负整数和 b=63 同样适用。

不要枚举一个周期的所有余数。建议实现：

```cpp
BigInt floor_sum(BigInt n, BigInt m, BigInt a, BigInt b);
// 返回 i=0..n-1 的 floor((a*i+b)/m) 之和；n>=0,m>0。

BigInt count_residue_lt(BigInt n, BigInt m, BigInt a, BigInt b, BigInt u);
BigInt count_residue_interval(BigInt t0, BigInt length,
                             BigInt a, BigInt c, BigInt m,
                             BigInt residue_lo, BigInt residue_hi);
std::optional<BigInt> first_hit_in_finite_interval(...);
```

在区间起点 t0 处令 `a0=floor_mod(a,M)`、`b0=floor_mod(c+a*t0,M)`。对 `0<=u<=M`：

```text
count_residue_lt(n,M,a0,b0,u)
  = n - (floor_sum(n,M,a0,b0+M-u) - floor_sum(n,M,a0,b0))

count_[L,U] = count_residue_lt(...,U+1) - count_residue_lt(...,L)
```

用欧几里得递归实现 floor_sum，处理偏移超出 M 的情形。先用计数判断区间是否命中，再对前缀长度二分第一个命中位置；不对非单调的 bit 本身二分。

`a=0` 单独处理。否则余数周期为 `P=M/gcd(abs(a),M)`。寻找最近命中时，在每个候选区间的相应端点最多考察 P 个连续整数；若该完整周期无命中，则该方向对此目标不可达。负方向令 `s=-t`，同时变换区间和系数，再调用同一实现。下一命中从前一个位置之后继续，仍受候选和时间预算限制。

可以只找到有限数量的命中候选，不能把未枚举其他命中误记为无解。有限搜索未命中、精确周期不可达、域为空、保护拒绝必须用不同状态。

### 7.3 完整候选验收

候选按以下漏斗记录：参数产生 → 原变量赋值形成 → 原式及真实硬条件合法 → 官方实际访问完成 → 保护条件通过 → 非输出重复 → 完整得分优于原生 → 最终正式输出。

域计算可提供合法性筛选，但最终仍需独立完整求值；官方观察器不支持的算子不能默认取零。采用增量求值时，变化依赖及可能改变短路访问的祖先都必须失效；首版优先完整求值，通过后再做等价的增量加速。

无合法候选是正常回退；候选域声称合法而原式验证失败、保护判定与重放不一致则是实现错误，停止正式阶段。不要将错误候选简单丢弃后继续报“所有输出合法”。

## 8. 成本预算和期限是算法的一部分

固定首版参数，不作扫描：

| 参数 | 冻结值 |
|---|---:|
| 方向池上限 / 每事件方向数 | 256 / 16 |
| 每方向目标数 / 每目标参数数 | 8 / 4 |
| 每事件完整候选评价数 | 64 |
| 每事件可选改进阶段 CPU 与墙钟上限 | 各 20 ms |
| 一次性预处理 CPU 与墙钟上限 | 各 100 ms |
| 预处理加改进累计墙钟 / CPU 绝对预算 | 各不超过会话预算的 5% |
| 按已付原生生成成本挣得的预算 | 原生累计 CPU、墙钟分别的 10% |
| 合法区间数 / 每方向域操作数 | 4096 / 200000 |
| 中间整数位长上限 | 4096 bit，原生大整数模型仍照常输出 |

可选改进可使用的 CPU 和墙钟余额分别取“绝对预算余额”和“已挣得余额”的较小者，同时扣费。原生生成成本只计模型生成/恢复链，排除改进、等待预算、输出日志、后台空闲和故意延时。不得先睡眠来积累额度。

新增预处理在有预算后惰性执行。若 100 ms 或实际可用余额内不能完成，记录原因并关闭本会话改进，继续原生输出；不反复重建、不要求首个模型等待预处理。已有原生提取和观察代码可复用，但新增索引、复制、保护构造、候选、验证和审计事件的成本必须单列。

20 ms 是首版工程预算，不是已证明最优。实现合作式取消：遍历节点、区间、方向、floor_sum/二分循环和大整数操作前检查余额；未完成的候选不能进入评分。单个不可中断操作造成的超支要如实记录。不存在“设置了定时器就已证明硬实时”的结论。

输出账本维护和事务是必需成本，即使改进预算耗尽也不能停止正确维护。报告分别列出可选改进成本、必需交付成本及总端到端成本；如果必需开销本身很大，按真实结果判失败，不能从性能账本扣除。

全局剩余不足 10 ms 时不再启动改进，立即尝试原生回退。这个余量不保证 I/O 必然及时完成；逾期或中断的 prepare/commit/confirm 事务按冻结正式收据语义排除。记录“原生模型已就绪但改进/交付后错过截止”的数量及原生就绪时刻，不把它计入已交付样本。

所有解析、预处理、改进、验证、输出和日志都包含在 120/900 秒会话墙钟中。离线审计可在实验后执行，但在线决定候选是否合法和保留的必要成本不能挪到审计阶段。生产 `solver.check` 数量不能因改进器暗中增加。

## 9. 正确性测试和隔离测试先通过

本轮涉及观察语义、数学域计算和宿主状态，必须有以下有意义的测试；不要只测试 getter 或复述实现。

1. **观察与保护**：覆盖 0/1/双侧/未访问、节点与 NOT、共享 DAG、AND/OR/ITE 短路、负数、bit 0/31/32/63。专门构造“位值满足但节点未访问”的反例；应拒绝替代。
2. **集合性质**：保存首侧尚未 covered 的例子；构造只比较 covered 数量会丢失未来覆盖的反例；逐前缀核对双侧与单侧观察集合包含。不同输出数量时不强行按输出序号配对。
3. **等式与方向**：冗余行、零行、非单位 pivot、分数消元、无自由度、多分量、支路等式；每个方向用独立任意精度代码验证 `A*d=0`。
4. **一维域**：负系数、严格不等式、整除失败、无限域、补集、孤立点、跨 OR 分支、固定 Bool、unsupported 项；在小域穷举每个 t 与原公式精确值比对，不只看找到的候选。
5. **模命中**：小模数穷举所有 a/c/目标区间及有符号起点；验证计数和第一/第二命中，补充高位大数、a=0、gcd 不相容、半无限域。计数不能溢出 uint64。
6. **状态隔离**：Identity 与真实替代两类测试都核对原生后续模型、RNG、map、m_ls、参考与原生计数；强制让替代值与原生交换值不同以触发检查。
7. **输出事务**：候选重复、原生模型已在输出中、取消、预算耗尽、临近截止、写入失败、重启重放和日志截断；不重号、不重复计分、无未确认模型。
8. **快照与还原**：CDCL 与 CCSS 两类模型都经过原 model converter 后再提取；未定义原变量沿用独立快照补全；不把约简 CCSS SAT 当原式 SAT。
9. **禁用回归**：改进完全关闭时，在固定操作测试中保留第五轮 Ref/Full 行为；共享构建切换功能，不依赖另一个旧二进制拼比较。

Release、ASan/UBSan 及 Python 独立算术审计通过后冻结实现。只保留已核实的上游泄漏例外，不扩大抑制。合成穷举测试的固定种子/枚举范围写入 manifest；这不是新增真实性能 seed。

## 10. 先用已有模型检验改进机会和成本

### 10.1 固定输入与两种离线分析

使用第五轮 Ref 的全部正式序列：convert 27 个、random 8 个、real 8 个，共 43 个。按原收据顺序和模型哈希恢复，不筛选高收益模型。缺文件时恢复归档；无法恢复则如实停止本阶段，不重新跑旧队列补样本。

**L1 单步机会分析**：每实例跳过首模型，得到 40 个位置。每个位置使用原生历史前缀作为 S，执行冻结候选生成器；在同一批候选上同时计算“严格保护”和“仅看最终分数、不检查保护”的选择，后者只作离线诊断。记录保留条件过滤了多少高分候选、具体丢失哪些观察。不能把不保护候选作为正式算法输出。

**L2 顺序变换分析**：对三条序列分别重放主候选和 `component_only`，每种重放维护自己的输出历史并重新计算保护集合。核验所有已处理原生前缀的观察包含，报告实际输出去重后的数量。两种策略历史可能分叉，因此它们的候选池不必相同，不宣称单个共同候选上的因果差异。

L1/L2 不启动生产 solver，不生成正式在线成绩。使用与在线同样的计数、20 ms/100 ms 上限和累计预算；其时间信用来自冻结原生生成成本。若旧日志不足以分离某项原生成本，则只报固定上限机会结果及缺项，不能编造在线预算通过。

离线绝对预算按拟进入的 120 秒会话计算；时间信用仅累计当前原生模型就绪前已经发生的生成成本，不能提前使用历史后续长失败的耗时。重放耗时与历史原生耗时只用于预算与机会分析，不能拼接成一条声称实测的在线时间曲线。

全部模型只处理一次；不得看结果后增候选、换方向窗口或放松保护。实现错误修复必须保留旧尝试并冻结新版本，不把修复前后最有利的结果拼成同一实验。

### 10.2 与重新求解比较同一个改进问题

固定每实例第 2、3、4、5 个原生位置，共 12 个案例。都使用 L1 的相同 S/m/protected，不根据候选是否成功挑选。

独立 oracle 求解：原公式及真实硬条件，加完整 protected 观察条件，再加“比原生模型多至少一个 covered bit”的条件。每案最多一次 check、2 秒；编码与初始化成本另计，整个 oracle 案例最多 3 秒，超时取消且不重试。明确记录是否采用新建 solver、加载成本、增量状态及版本；首版统一使用同一个固定的冷启动 oracle，不能混用不同模式拼加速比。

保护观察的约束必须同时表达官方 `Reach(node)` 和位值。为冻结访问器逐运算构造 Reach 条件，并用小公式穷举验证；若实际 DAG 缓存/访问语义无法精确编码，标记该案 `oracle_encoding_unsupported`，不使用仅约束值的弱问题冒充同题比较。

严格额外 covered 条件可用以下集合构造：取在 S 中只见一侧、但没有被 m 补齐的所有 BitId，要求候选至少实际观察到其中一个缺失侧。配合 protected，这与“当前 covered 严格超过 m”一致。集合为空时无需调用 check，记录 `no_strict_covered_target`。Bool/Int 按原观察语义编码；数值位条件可用正模数整数 mod，不引入机器溢出。

若编码超过案例总预算，记录编码超时，不缩减 protected 或额外目标集合。oracle 的答案和模型只作诊断，不用于在线方向、排序或模型供给。

分别报告：候选改进成功数、oracle SAT/UNSAT/Unknown/编码不支持、两者成功时的端到端 CPU/墙钟、每个改进位置的全部失败候选成本、预处理摊销及总成本。Unknown 是删失结果，不能当 2 秒“求解成功时间”计算平均加速比。

若双方同题成功的案例不足 3 个，或未覆盖至少 2 个实例，不宣称“远低于重新求解”；只报告逐案证据。即使样本充分，也把结论限定为这 12 个固定案例。预注册的“明显更低成本”描述门槛为：共同成功案例的端到端 CPU 和墙钟中位数都不超过 oracle 的 20%；同时列出全部逐案比值，不隐藏失败。

### 10.3 进入在线实验的门槛

必须同时满足：

1. 正确性、完整保护、观察包含和状态隔离全部通过。
2. L2 主候选至少在两个实例上各出现一次严格额外 covered，且实例终点覆盖均不低于同一输入序列。
3. 有实际改进在冻结在线可用预算内完成；包含预处理、失败候选和必要评价后仍满足预算账本。
4. 不是仅通过多输出模型或不计 Reach 获得收益。

完整 SMT 比较用于说明成本与机会，不要求本轮一定先达到“5 倍”才能验证端到端价值。但若只有超预算候选或离线 oracle 能改进，判 No-Go，不启动短会话。

失败原因至少区分：没有自由方向、分量/位长上限、unsupported 运算、域计算超限、目标不可达、候选未访问、保护条件过强、合法但不更优、评价成本过高、输出重复。有限候选失败不能解释为“满足保护条件的模型不存在”；只有精确 oracle UNSAT 才支持其特定编码问题的无解结论。

## 11. 完整宿主的短会话实验

### 11.1 四个配置使用同一构建

| 配置 | 原生策略 | 独立模块 | 输出 |
|---|---|---|---|
| Ref | 第五轮无覆盖软参考 | 关闭可选改进 | 原生模型 |
| RefObserve | 同 Ref | 双账本、观察与结构准备；不生成候选 | 原生模型 |
| RefImprove | 同 Ref | 完整冻结改进器 | 满足保护的最佳候选或原生回退 |
| Full | 第五轮 support/block 覆盖相位 | 关闭后处理改进 | 原生模型 |

所有配置共用新宿主的必要接入、合法性与正式事务代码。RefObserve 测量额外结构准备/观察维护负担，不把它当正式主基线；RefImprove 必须相对 Ref 取得收益，不能仅比一个人为更慢的观察对照好。Full 用于展示旧的相位机制与新机制的区别。

RefObserve 与 RefImprove 的持久索引准备相同，运行成本实际计入；RefObserve 不空转模拟候选成本。若改进器未完成准备，它的状态按真实规则处理。

### 11.2 独立预算矩阵

实例固定为 convert、SMT_random、SMT_real；seed=0。

1. `time120`：最多 120 秒，无正式模型数和人为 CDCL 次数上限。
2. `n20_t120`：交付 20 个合法、不同、及时提交的输出模型即结束，否则最多 120 秒。

总计 **3 实例 × 4 配置 × 2 独立模式 = 24 次会话**。不得用 time120 前 20 个模型代替独立 n20 会话，不得保留第五轮的 32/8/8 查询上限。

每个实例四配置绑定四个不同物理核，同步起跑；提前登记配置到 CPU 的轮换。按冻结实例/模式顺序执行六批。计时期间不编译、不审计、不压缩、不运行离线 oracle。记录 CPU 拓扑、亲和性、wall、user+system、RSS、实际退出延迟和异常。

### 11.3 必须同时报告四层效果

1. **固定输入前缀**：本会话实际生成的原生模型前缀与其改进输出作集合比较，验证保留性质。这是机制检查。
2. **真实供给**：RefImprove 与 Ref 的 CDCL/CCSS 检查数、合法原生模型数、原生重复、不同正式输出数、到达 20 输出的时间。这反映计算机会成本。
3. **真实覆盖**：完整 120 秒终点 covered/total、精确百分点差、每输出新增 covered、新观察、时间曲线和 AUC；以及严格相同输出样本数的集合覆盖。
4. **旧机制对照**：RefImprove 与 Full 的同预算结果；同时保留 RefObserve−Ref 解释接入成本。不能把历史 Full 数据拼成同构建对照。

G1/G2/G3 使用共同首个原生/输出模型与冻结映射口径。若首模型意外不同，记录原因并使用明确完备分区，不强行制造共同起点。逐分区增益和损失必须加总为全式差；G2 不能解释成永远不可映射。

每个候选都保留被拒原因及成本，每次替代都保存原生与输出赋值、保护掩码、实际访问和完整集合差。必须可以回答：某次替代多了多少 covered，是否损失任何保护观察，后来原生查询是否继续使用旧反馈。

### 11.4 严格等样本和晋级判据

只有双方在各自独立 `n20_t120` 会话中完成 20 个不同正式输出，才能比较严格 20 模型。未完成记录实际数量、期限状态与双方共有前缀；不能算平局、胜利，也不能用另一模式补齐。

正式晋级以 **RefImprove 对 Ref** 为主，全部满足才进入 900 秒阶段：

1. 三实例等权的 120 秒精确覆盖百分点均值差为正，至少两个实例严格为正。
2. 至少两个实例双方都完成严格 20 模型；在这个明确列出的共同完成集合上，平均覆盖百分点差为正，至少两个实例严格为正。
3. 任一实例的等时间或适用的严格等样本退步，不得超过 0.5 个覆盖百分点，且不得超过 Ref covered 数的 5%。这是预注册工程停止线，不是统计显著性。
4. 实际在线替代至少在两个实例上带来严格额外 covered；不能只有首次单侧观察增加。
5. 无非法模型、保护丢失、反馈污染、异常 RNG 消费、错误截止计分或未解释的预算超支；额外成本和原生供给损失已全部进入统计。

只有样本质量提高、时间终点下降：判“改进可行但成本未回收”；只有模型变多、严格等样本不提高：判“尚未达到本轮模型质量目标”；两者都未提高则 No-Go。不得为晋级追加 seed、延长短实验、调整预算/方向数或新增另一算法。

## 12. 晋级后才运行八实例正式确认

冻结唯一候选、全部参数、生成器和守卫状态、Release 宿主与动态库、8 个输入、官方指标脚本、日志设置和运行队列。正式运行前提交冻结 manifest。

配置仅 Ref 和 RefImprove：

1. `time900`：最多 900 秒，不限模型数。
2. `n100_t900`：100 个合法、不同、及时正式输出或最多 900 秒。

总计 **8 × 2 × 2 = 32 项新正式会话**，均 seed=0。使用固定 16 逻辑 CPU 槽与预登记的配置轮转队列，记录物理核/超线程同胞和资源竞争。不为单个不理想结果重跑。

完整 HighDiv 继续复用第一轮已冻结 16 项结果，不重新执行。主结论区分：

1. RefImprove 对 Ref：本轮改进器的净收益。
2. 短会话 RefImprove 对 Full：新机制相对于旧相位机制的开发集证据；本轮没有新 Full 正式矩阵，不外推 900 秒胜负。
3. RefImprove 对冻结完整 HighDiv：项目最终目标的历史基线比较，明确环境/资源不完全配对的限制。

8 实例等时间主指标使用等权平均精确覆盖百分点差，附逐实例 covered bit 差、AUC、原生与输出吞吐、重复率、首次/第 10/20/100 模型时间。AUC 对固定 T 用从 0 起的右连续阶梯覆盖曲线积分，再除以 `T*total`，未产生模型时覆盖为零。

严格 100 模型只在双方完成的交集上计算，列出分母和所有未完成项；比较 HighDiv 时重新列各自交集，不能沿用 Ref 的集合。没有八例都完成，就不能写“八实例严格等 100 样本总体提高”。

仅当等时间平均与适用的严格等样本平均都为正、各至少两例严格改善、且没有未披露的大退步，才可写“本轮观察到整体改进”。只有一个 seed，不宣称稳定、统计显著或普遍优势。成功的短会话并不保证正式阶段成功。

## 13. 日志、独立审计与最终交付

### 13.1 每次事件最低字段

```text
run_id, build_sha, binary_sha, library_sha, input_sha, metric_sha
query_id, native_event_id, backend_source, native_ready_time
native_assignment_hash, native_acceptance, native_duplicate
native_history_version, output_history_version, protected_count
direction_id, equality_component, t, target_node, target_bit, desired
domain_status, interval_count, modular_status, candidate_assignment_hash
original_formula_valid, hard_conditions_valid, visited_nodes_digest
protected_missing_count, missing_observation_ids, output_duplicate
base_gain_covered, candidate_gain_covered, base_gain_observed, candidate_gain_observed
selection_reason, fallback_reason, native_feedback_digest
preprocess_cpu/wall, generation_cpu/wall, validation_cpu/wall
observation_cpu/wall, selection_cpu/wall, mandatory_delivery_cpu/wall
budget_before/after, cancellation_reason, deadline_missed_after_native_ready
prepare/commit/confirm times, output_formal_index
```

哈希旁保存可恢复的原始内容；保护缺失不能只留一个数量。首次大规模索引和未完成预处理也要计时。内存缓冲、日志截断及采样日志策略必须披露；正式模型与替代证明不能因日志节流丢失。

### 13.2 独立审计不能只重用在线判定

使用冻结官方脚本重算所有正式输出；独立 Python 任意精度解释器核对原式合法性、实际访问、负数低 64 位、protected 包含和逐前缀观察包含。核验实际完整原变量模型，不只核验约简子句或目标项。

生产候选失败、Unknown、超时、退出延迟、预算超支、未确认模型和重复模型无损保留。原生流与输出流分开归档，不能将原生输入模型写进官方输出样本文件来虚增覆盖。

所有通过的指标应满足：官方总覆盖 = 独立精确覆盖；分组差值之和 = 全式差值；正式样本数 = 及时完成且合法不同的输出事务数。任何不一致应先修复并重新界定失效阶段，不能先报告性能优势。

### 13.3 推荐目录与可执行入口

```text
docs/refinement/execution_guide.zh.md
docs/refinement/implementation_contract.zh.md
docs/refinement/hook_map.zh.md
docs/refinement/results.zh.md
include/refinement/{observations,history,affine_ir,directions,line_domain,modular_hits,
                    refiner,budget,native_output_split}.hpp
src/refinement/
tests/refinement/
scripts/refinement/{build,correctness,freeze_plan,replay_opportunity,oracle_compare,
                    run_short,analyze_short,run_formal,audit,archive_publish}.py
configs/refinement.json
manifests/refinement/{plan,implementation,offline,short,formal}.json
results/refinement/{correctness,offline,oracle,short,analysis}/
results/refinement/formal/       # 仅晋级后创建
archives/refinement/
```

脚本必须拒绝覆盖已开始的 attempt。构建器保存真正使用的补丁、头文件依赖、编译参数和 `libz3` 路径；执行器自动移除遗留测试查询上限，检查冻结哈希后才启动。正式队列不允许“失败后自动重试”。

### 13.4 中文报告按这些问题作答

1. 保护的是哪些实际单侧观察，是否含访问条件？
2. 在发生真实替代后，原生模型、map、m_ls、参考、RNG、计数和反馈是否仍隔离？
3. 多少真实位置存在预算内合法改进？失败主要位于哪个漏斗阶段？
4. 必需等式方向和完整区间并集分别产生什么实际机会？跨 OR 是否真的有用？
5. 保留条件拒绝了多少高分候选？是保护过强，还是原本的候选不够好？
6. 严格额外 covered、仅新增单侧观察分别有多少？G1/G2/G3 的变化如何？
7. 包含失败和预处理后，每次改进的全部成本是多少？同题 oracle 支持多强的“便宜”结论？
8. 等时间下是否减少了原生生成机会？有多少模型因改进错过截止？
9. 等样本优势与等时间优势是否同时成立，比较集合各包含哪些实例？
10. 未晋级时具体哪条预注册门槛失败？不得把未跑的正式矩阵写成待补正结果。
11. 对 Ref、Full、冻结完整 HighDiv 分别能得出什么范围的结论？
12. 哪些是已证明的同序列性质，哪些是有限实测，哪些仍未知？

完成无损归档及哈希复核；正常提交并推送独立分支，使用 `git ls-remote` 核对远端完整 SHA，工作区保持干净。不上传虚拟环境、构建树、第三方二进制或凭据，不改历史受保护文件。若远端不可写，保留本地完整提交和原因，不声称已推送。

## 14. 冻结执行顺序与停止规则

1. 读取来源、恢复原始证据，定位实际构建入口，冻结本轮生成器与守卫状态。
2. 建立两类历史账本及观察契约，完成 Identity 和真实替代隔离测试。
3. 实现方向、完整一维域、模命中与有限候选选择；完成 Release/ASan/UBSan 和独立穷举测试。
4. 冻结唯一实现与参数；执行 43 模型离线顺序分析、40 位置单步分析和最多 12 个固定 oracle 案例。
5. 离线门槛不通过：停止性能扩展，完成负结果报告、归档与提交。
6. 门槛通过：运行 24 次独立短会话，独立审计，按预注册规则判断晋级。
7. 短会话不通过：停止，不启动 900 秒，不另加候选机制或调参。
8. 短会话通过：冻结候选并执行 32 项正式会话，完成审计、报告、归档和推送。

正确性错误允许修复，但必须保留已开始的失败记录、明确废止受影响阶段，并重新冻结；不能把多次尝试当成同一轮只执行一次，不能为了性能好看重跑正确但不理想的结果。

本轮的成功标准是：**完整原式合法、完整新增观察保留、原生反馈隔离，并在全部计算成本计入后提高真实输出覆盖。** 找到单个更漂亮的模型、证明同序列包含、或完成全部工程测试，都不能单独代替这一端到端目标。

## 来源索引

1. [第四轮实际报告](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550/docs/round4_mapping_and_soft_reference_results.zh.md)。
2. [第五轮实际报告](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae85956068154207a442c0e2c8387c573dc32411/docs/round5_weak_targets_and_ccss_results.zh.md)。
3. [实际交换调用链](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae85956068154207a442c0e2c8387c573dc32411/docs/round5/transfer_call_graph.zh.md)。
4. [软参考 Session 源模板](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae85956068154207a442c0e2c8387c573dc32411/include/round4/soft_reference/session.hpp)。
5. [宿主补丁入口](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae85956068154207a442c0e2c8387c573dc32411/scripts/patch_round4_host.py)。
6. [原生参考收集实现](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae85956068154207a442c0e2c8387c573dc32411/include/round4/soft_reference/inherited_reference.hpp)。
7. [第五轮构建冻结清单](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae85956068154207a442c0e2c8387c573dc32411/manifests/round5_implementation.json)。

上述链接支持历史事实与接入位置；本指引的新接口、参数、算法和晋级门槛是本轮预注册设计，不是已经获得实验证实的收益。
