# Guided Sampler 第一轮：实现、验证、实验与上传执行指引

## 0. 任务与已冻结边界

请在本地实际完成代码实现、构建、正确性测试、正式实验、覆盖计算、中文总结与 GitHub 推送，不要止于给出计划。

工作区已有 `benchmarks/` 和从 GitHub 下载的完整 `HighDiv/`。用户最终确认：**benchmarks 中是 8 个实例，不是 9 个**；Linux，8 个物理核、16 个逻辑线程，内存足够。新项目放入独立的 `guided_sampler/` 文件夹，远端为 `https://github.com/ChenKaichen-SCUT/guided_sampler`。现有 HighDiv 与 benchmarks 不原地修改。

### 0.1 本轮只实现两种引导

- **A：已有原子软相位。** 在完整 HighDiv 原有的 CDCL(T) 决策中，对已经存在并被正常选中的原子提供取值偏好，不更换 A 的决策变量。
- **B：新增可回溯目标。** 为少量缺失 bit 观察建立精确目标表达式，将其接入 SMT 内核的普通决策过程；目标可以被回溯放弃，不是 `check(assumptions)` 中必须满足的条件。
- 正式新配置为 `a_only`、`b_only`、`a_plus_b`，每个配置只用 **seed=0**。
- 原生 CDCL(T)、CCSS、HighDiv 原有预处理、模型恢复、原有随机化和变量固定流程保留。只在 CDCL(T) 路径安装新机制，CCSS 不安装新机制；两种来源正式交付的模型都更新引导器的共同观察状态。

### 0.2 明确禁止

不实现 LIA 数值移动、tableau 改值、算术候选池、有限取值域推导、宏观选择组分析、区间/同余抽象、不可达证明、目标 core 学习、MaxSMT、在线学习、批次排序、额外修复求解器或新的 CDCL/CCSS 调度。

正常 Z3 的理论传播、冲突分析、学习子句和回溯当然保留，但不得新增“根据失败永久删除某个 bit 目标”的逻辑。

尤其不要搬入旧 `lia_cover_sampler` 的持久 simple-solver 枚举框架、完整模型阻塞、随机 1–4 干预或旧补丁栈。本任务是在**完整 HighDiv**上增加 A/B，不是再实现一个简化枚举器。

### 0.3 正式实验必须完成两套独立任务

| 预算模式 | 停止规则 | 输出要求 |
|---|---|---|
| `time900` | 900 秒，没有模型数量上限 | 统计截止前全部正式输出 |
| `n100_t900` | 达到 100 个不同、合法、及时的正式模型，或 900 秒到达 | 不足 100 时原样输出实际数量，报告未完成 |

配置为 HighDiv、A-only、B-only、A+B，每配置 8 实例 × 2 模式，共 **64 次正式会话**。其中 HighDiv 为 **16 次**：每个实例、每种模式各一次，以后只复用本次基线。其余为 **48 次**新方法运行。

两个预算模式应启动独立进程，不能把 `time900` 的前 100 个事后当作已执行了 `n100_t900` 实验。可以另外报告该前缀，但必须注明来源。

所有正式任务 seed=0；不追加 seed，不用较好重复替换较差结果。功能与正确性通过后，完整执行上述正式矩阵，**不设置基于短跑覆盖输赢的性能晋级门槛**。

---

## 1. 已核对的上游代码与容易误用的接口

本指引核对的 HighDiv 提交为：

```text
f2c6e1756b13281d96cbf90a8bd940129e56cce4
```

执行时先记录本地提交号及工作区状态；本地是 ZIP 下载且没有 `.git` 时，用对应公开提交的逐文件哈希核对，不因缺少 Git 元数据重新下载或覆盖原目录。若实际内容不同，列出差异并选定一个可追溯基点，不能悄悄混用版本。

以下为上游事实，后面的 `guided_*` 名称则是**本轮建议新增的接口/函数，不是现有 Z3 API**。

| 现有路径/函数 | 当前作用 | 本轮边界 |
|---|---|---|
| `HighDiv/src/sampler/liasampler.cpp::LiaSampler::hybrid_sampling` | 建立预处理后的 LS solver 与原式 CDCL solver，交替运行 | 保留主流程，只在原有 CDCL check 周围准备/提取指导信息 |
| `liasampler.h::cdcl_epoch` | 当前为 1 | 不改 |
| `liasampler.h::fixed_var_pct` | 当前为 0.5 | 不改 |
| `mk_preamble_tactic` | simplify、propagate-values、ctx-simplify、solve-eqs 等 | 不删除、不替换为自己编译表示 |
| `record_model` / `print_unique_sample` | 原式验证、样本去重和输出 | 共同适配原变量投影、截止时间与收据 |
| `gen_random_seed` 与 `mt` | HighDiv 自己的随机流 | 新模块不能消费它 |
| `z3/src/smt/smt_context.cpp::context::guess` | 原生相位生成 | 保留原调用和随机消费；不再另写一套替代实现 |
| `context::decide` | 正常 case split、特殊决策处理、push_scope、assign | 只加入一个统一 broker，A/B 不相互覆盖 |
| `smt_context.h::internalize` / `get_literal` / `mark_as_relevant` | 表达式内部化、布尔 literal 与 relevance | B 需要审查这些入口的调用顺序与生命周期 |
| `z3/src/smt/smt_solver.cpp::check_sat_core2` | 转发到 `m_context.check` | 新元数据转发到实际 SMT context |
| `z3/src/solver/combined_solver.cpp::check_sat_core` | 在 tactic solver1 与 incremental solver2 间路由 | 不因指导接口注册而改变路由条件 |
| `z3/src/sampler/` | CCSS | 不修改算法 |
| `HighDiv/my_scripts/calc_metric.py` | 用户指定的统一覆盖指标 | 冻结原脚本及哈希，不改口径 |

### 1.1 三个必须避免的隐式算法变更

**不得把 `z3::solver(c)` 换成 `z3::solver(c, z3::solver::simple{})`。** 这改变了 HighDiv 原有求解路径。

**不得在每个模型后添加完整赋值阻塞。** 当前 HighDiv 主要在输出端去重，本轮不能把旧枚举器的 no-good 机制夹带进来。

**不得把原有查询上限改成旧项目的 2 秒。** 上游 CDCL check 使用最多 50,000 ms，LS 使用最多 60 秒且都受会话剩余时间约束。保留这些设置，仅统一严格截止适配。

### 1.2 特别审查 combined solver

实际源码中，`push()`、check 之后再 `assert_expr()`、以及非空 assumptions 等会影响 incremental 路由。注册指导元数据不能借用一次空 push/pop；也不能为了方便，把 `a → goal` 直接从外层不断 `solver.add()` 后仍声称没有改变路由。

第一版采用以下可控支持范围：

1. 保留 HighDiv 的默认 solver 和其原始路由判断。
2. 把新指导安装到**自然选择到的持久 SMT/incremental 内核**。
3. tactic/其他不支持的执行分支原样运行，记录 `guidance_backend_unsupported`，不得静默替换成 simple solver。
4. 记录每个 check 实际走了哪个后端、有无 fallback、机制是否真的进入 `context::decide`。
5. 第一版不为了让所有 check 都有指导而改写整条 tactic/预处理流水线。此适用边界必须在最终报告中披露。

HighDiv 在后续 CDCL 查询中会根据 LS 模型构造原有变量固定 assumptions；这些非空 assumptions 本来就能进入 incremental 路径。新机制利用真实接入机会，而不是伪造一个新 assumption 来强制切换。

---

## 2. 新项目布局与版本隔离

建议结构如下，允许调整目录名，但不得混用已测依赖：

```text
workspace/
  benchmarks/                       # 原目录，只读；恰好8个SMT2实例
  HighDiv/                          # 原目录，只读
  guided_sampler/                   # 新Git仓库
    README.md
    CMakeLists.txt                   # 或保留上游Make并用脚本驱动
    src/
      original_ast.cpp
      observation_tracker.cpp
      demand_manager.cpp
      atom_hint_catalog.cpp
      reach_builder.cpp
      target_encoder.cpp
      guidance_bridge.cpp
      sample_sink.cpp
    include/guided/
      original_ast.hpp
      observation_tracker.hpp
      demand_manager.hpp
      atom_hint_catalog.hpp
      target_encoder.hpp
      guidance_bridge.hpp
      sample_sink.hpp
    patches/
      00_highdiv_common_measurement.patch
      10_highdiv_guidance_host.patch
      20_z3_guidance_metadata.patch
      21_z3_decision_broker.patch
      22_z3_target_internalization.patch
    configs/round1.json
    scripts/
      inspect_workspace.py
      prepare_sources.py
      build_all.py
      run_correctness.py
      freeze_plan.py
      run_experiments.py
      finalize_samples.py
      evaluate_official.py
      audit_results.py
      summarize_round.py
      archive_results.py
      publish_round.py
    tests/
    docs/
      source_map.zh.md
      algorithm_contract.zh.md
      round1_protocol.zh.md
      round1_results.zh.md
    manifests/
      upstream.json
      inputs.json
      builds.json
    results/
      baseline_seed0_v1/
      round1/
    worktrees/                      # 不提交：上游干净副本及两个独立工作副本
    build/                          # 不提交：release、sanitize
    deps/                           # 不提交：baseline/guided各自Z3和venv
```

### 2.1 两套依赖

- `baseline`：冻结上游 Z3 + HighDiv 共同测量适配，不包含 A/B 改动。
- `guided`：同一上游 Z3 加新增机制，A/B/AB 使用同一新可执行文件与同一新 libz3，仅配置不同。
- 另外提供 `off` 模式，在 guided 二进制中彻底关闭新机制，用于小规模兼容性测试；不把它再安排成一套 900 秒正式基线。

HighDiv 外层与新方法统一使用 `-O3`/Release，Z3 也使用一致的 Release 构建规则。ASan/UBSan 构建仅用于正确性测试，不能用于正式计时。

用 `ldd`/RPATH/实际加载路径核对每个进程的 `libz3.so`；Python 官方指标使用冻结的 baseline venv。将编译器、C/C++ flags、上游源码、补丁、二进制、共享库及指标脚本 SHA-256 写入构建清单。

不提交整份修改后 Z3 或生成二进制充当“我们的实现”；保存上游固定引用、新增代码、必要补丁、构建脚本及相应版权信息，确保从干净源树可以重建。

---

## 3. 原始 AST、观察状态和目标语义

### 3.1 `OriginalAst::load()`

从**未被任何新目标修改的原始 SMT2 文件**构建原 AST，并保留原 assertion 顺序和 children 顺序。

需要记录：

```cpp
struct OriginalNode {
    NodeId id;                      // 本公式内稳定编号，不跨进程使用Z3裸AST ID
    SortKind sort;                  // Bool 或 Int
    OpKind op;
    std::vector<NodeId> children;
    std::vector<ParentEdge> parents;
    std::optional<unsigned> original_variable_index;
    ExactInteger numeral;
    StrongExprRef expr;
};
```

按原始结构识别共享节点，不把两个不同原 AST 节点因代数等价就合并为一个计分节点。反之，相同 Z3 AST 的共享节点按官方统计去重。稳定身份绑定输入哈希、sort、结构和原节点编号。

使用显式栈处理深层 AST，避免再引入固定 512/1024 的递归深度上限。Bool/Int 运算支持必须与官方 `ManualSatisfiesMetric` 在本轮 8 个实例上逐项一致。

### 3.2 `ObservationTracker::evaluate(model)`

对原变量的完整精确赋值做纯值求值，返回每个实际访问节点的值及 visited 集合。保留：

- AND/OR 的从左到右短路；
- Int ITE 只访问所选分支及条件；
- Python 官方脚本中的数值、布尔及子项求值顺序；
- Int 精确数学运算，只有观察时截取低64位；
- 共享节点对 seen 掩码的幂等累计。

不得为评分调用新的 solver.check，也不能在求值时求解缺失变量。输入必须是完整原变量投影，不能借用官方脚本的缺变量默认0来掩盖不完整输出。

### 3.3 状态更新

```cpp
struct SeenBits { uint64_t seen0, seen1; };
```

Bool 使用 mask=1，Int 使用低64位 mask。负整数采用数学整数对 `2^64` 的非负余数，禁止依赖 C++ 有符号移位或窄整数溢出。

对实际访问节点的观测值 `v`：

```text
ones  = low64(v) & mask
zeros = (~ones) & mask
new_observed = popcount(ones & ~seen1) + popcount(zeros & ~seen0)
new_covered  = popcount((seen0 | zeros) & (seen1 | ones))
               - popcount(seen0 & seen1)
```

只有正式模型交付事务成功后更新 seen，重复、非法、未交付、迟到候选不更新。CDCL 和 CCSS 的正式模型使用同一套 tracker。

### 3.4 `DemandManager`

只对单侧已见的 bit 产生相反取值偏好：

```text
demand_one  = seen0 & ~seen1 & mask
demand_zero = seen1 & ~seen0 & mask
```

两侧未见、两侧都见过：都不指定0/1偏好。首次观察仍增加 `new_observed`，可保留模型，但不冒充 `new_covered`。

所有及时、合法、不同模型均按 HighDiv 的接纳规则保留，不以 covered=0 过滤，不以一批零收益为理由提前终止。

结构字面常量（Int numeral、true、false）可以不放入工作目标队列；这是输入节点类别过滤，不建立“已证不可达”状态，官方分母完全不变。除此之外，不推导常量域或全局不可达。

### 3.5 目标选择不训练、不扫描全部bit

`select_window()` 使用稳定的轮转游标遍历有单侧需求的节点及位，去除重复目标。游标跨查询继续前进，避免每次只取 AST 开头或最低位；低/中/高位都必须有机会进入窗口。

本轮默认窗口至多 8 个目标。目标不足时不填入已覆盖或双侧未见目标。一个 check 内使用冻结的 coverage_version，不能在搜索中根据尚未交付的候选更新状态。

目标身份：`(formula_sha256, original_node_id, bit_index, desired_value)`。这是原节点的观察目标，不是仅原变量的值目标。

---

## 4. 通道 A：已有原子软相位

### 4.1 只允许的直接匹配

实现 `AtomHintCatalog::build()` 与 `bind_existing_atoms(context)`，允许以下有限规则：

1. **原 Bool 原子自身的观察。** 该原子只见过 false 时偏好 true，只见过 true 时偏好 false。处理语法 NOT 的极性转换。
2. **显式常量等式。** 形如 `e = c` 或 `c = e`，e 是一个原 AST Int 节点，c 是整数常量。当原子为 true 时，e 的位值由 c 决定；如果命中 e 的单侧缺口，可以给该原子 true 偏好。
3. 允许无约束语义下可靠的语法重写/规范化建立原子别名，例如去外层 NOT、等式交换两侧；规范化不修改被评分的原 AST。

明确不允许：由原公式推导 `x∈{0,10}`、从多个不等式推导区间、从样本猜测域、扫描求解器 tableau、传播等式组、从 `(e=c)=false` 推断 e 的某位一定相反。

同一原子可能对应多个原 bit，按不同 TargetId 去重后计分，不重复算同一目标。A 的分数只是可能收益：即使原子满足，相关原节点的 Reach 也可能不成立，不能称为保证新增覆盖。

### 4.2 增量分数

建议接口：

```cpp
struct AtomHint {
    StrongExprRef atom;
    uint64_t atom_key;
    std::vector<TargetId> support_true;
    std::vector<TargetId> support_false;
};

class AtomHintCatalog {
public:
    void build(const OriginalAst&);
    void on_demands_changed(std::span<const NodeId> changed_nodes);
    PhaseSuggestion lookup_existing_atom(ExprRef atom, bool native_phase,
                                         CoverageVersion version) const;
};
```

维护反向索引，正式模型提交时更新受影响项，而不是每次 decision 全量扫描 AST。选择偏好时仅比较两个 polarity 当前能支持的未完成目标数，平分则保留原生相位；不引入收益学习器或新的概率调参。

A 不主动把任何原子加入 solver，不改变 variable order。原子未被实际选到或已被传播赋值时，不做强行重赋值，记录未介入原因即可。

### 4.3 在 `context::decide()` 的位置

保留原有 case-split queue 选择、`guess()`、特殊理论 split 和 user-propagator 行为。获得原生变量和原生相位之后，在普通决策上查询 A；有建议时最多改相位，没有建议走原路径。

对 user propagator 已接管的决策、已有赋值、特殊 split 不介入。不要把建议插入传播并覆盖已经确定的 literal。

保留 `guess()` 原来的调用与随机消费，新引导不得使用 HighDiv 的 `m_random` 或外层 `mt` 来抽额外随机数。新模块需要随机打破选择顺序时使用独立、确定种子的 RNG。

---

## 5. 通道 B：惰性、精确、可回溯的目标决策

### 5.1 精确观察谓词

先实现 `ReachBuilder::reach(NodeId)`，只做原 AST 访问语义翻译，不是宏观整数分析：

```text
Reach(root) = true
普通算术/比较子节点：继承父Reach
AND的第k个子节点：父Reach 且 前k个子节点均为true
OR的第k个子节点：父Reach 且 前k个子节点均为false
ITE条件：父Reach
ITE真分支：父Reach 且 条件为true
ITE假分支：父Reach 且 条件为false
共享节点：来自所有父边的可达条件取OR
```

使用 DAG 共享、前缀条件共享与惰性构建；不展开成所有根到叶路径。对构建过大或超额度目标，保留 `encoding_incomplete`，以后可以再尝试；不能标不可达。

`TargetEncoder::make(TargetId)`：

```text
Bool:
  g = Reach(node) AND (node 或 NOT node，按desired)

Int，bit号j从0开始，j∈[0,63]:
  P = 2^(j+1)，H = 2^j       # 精确大整数
  r = mod(node, P)           # P>0，SMT-LIB非负余数
  desired=1: g = Reach(node) AND r >= H
  desired=0: g = Reach(node) AND r < H
```

优先使用精确常模表达式，不把所有原 Int 转为64位 BitVec，也不把原整数运算改成溢出运算。常数 `2^64` 必须用大整数/十进制数值构造，不能写 `uint64_t(1)<<64`。

此编码是原观察的表达：整数算术仍保持无界。常模若内部引入商/余数变量，它们是辅助变量，不能进入输出、覆盖分母或 HighDiv 固定变量交换。

### 5.2 本轮采用的具体软化方式：内部目标代理，不断言目标为真

为避免外层 `add()` 改变 combined-solver 路由，推荐在**已经自然选中的 SMT 内核**中，通过原生 internalization 把 `g` 转成一个 Boolean literal/proxy。记为 `lit(g)`。

含义是：让求解器认识“这个目标是否成立”，随后在正常 decision 中优先尝试 `lit(g)=true`。**不能把 g 当作新的必真 assertion。**

复合公式的内部 proxy 与 g 的定义关系，由 Z3 原有 internalization 管理；不要手工编造不带理由的理论公理。若需要显式命名 proxy，应当是语义透明的定义性扩展，而不是在根层断言该 proxy 为 true。

这与此前讨论的 `a → g` 软开关目的相同：把目标纳入可回溯选择。本版只实现一种经过测试的内部代理方式，不同时实现两个不同的 B 编码策略再挑赢家。若实际源码必须采用显式 guard，请在协议冻结前说明等价关系、调用路径和生命周期，并通过同样的投影保解测试；不能偷换成硬 assumption。

### 5.3 B 需要的新增函数契约

```cpp
struct TargetRequest {
    uint64_t target_id;
    StrongExprRef predicate;      // g：精确原AST观察谓词
    CoverageVersion version;
};

class CoverageDecisionBroker {
public:
    void install(const GuidancePlan& plan);  // 只接收元数据，不求解
    void prepare_targets_at_safe_point();   // 内核安全边界处internalize
    DecisionSuggestion suggest_B();         // 返回未赋值普通literal，不直接assign
    void observe_final_decision(...);
    void end_check(...);
};
```

`prepare_targets_at_safe_point()` 必须放在常规 assertion/assumption 初始化已经正确建立、可以安全 internalize 且随后会正常传播的位置。查看本地 `context::check`/初始化/search 流程后选定插入点，写入 source_map；不能在外层只读回调里创建 AST 或重入 `solver.check()`。

目标内部化可能产生待传播项，必须返回正常传播循环处理完，再允许新的 decision。不能在有待传播/冲突时直接插入另一个决策。

`mark_as_relevant()` 只表示这个表达式需要被理论层处理，不表示把它断言为 true。内部化、relevance 和实际决定取 true 三件事分别记录。

### 5.4 普通决策与回溯

B 必须使用与原生决策相同的 scope、decision 标记和冲突处理路径。不可把目标以根层单位子句、永久 `assert`、`assert_and_track` 或外层 check assumptions 的形式固定为 true。

目标被传播为 false、与当前 HighDiv 固定变量冲突、或回溯后放弃时，原公式仍正常求解；本次没有实现目标不是整个 F 不可满足。

每个目标每个外层 CDCL check 最多主动尝试一次，attempt 集合不因回溯或 restart 清零。新 check 才开始新的 epoch。只有原生完整搜索产生的 UNSAT 才沿 HighDiv 原有处理逻辑返回；不从“所有偏好失败”直接返回 UNSAT。

目标已覆盖或暂时退出活跃窗口时，停止其显式优先级。不要手工删除仍被学习子句引用的定义，也不要声称停止指导就消除了过去指导留下的搜索历史。内部注册条目随其合法 scope 生命周期保留/回滚，裸 bool_var 不跨 pop/reset 复用。还要统计不再被显式优先、却被原生队列自行选中的目标代理；不能把它们遗漏后声称后续搜索完全不受新增表达式影响。

### 5.5 防止辅助变量污染

B 的目标、proxy、商余数等必须有独立身份/前缀和登记表。A 不能把这些新原子当作原始目标反过来指导；计分和样本去重只基于原始变量。

B 的注册表达式必须强引用，不能只保存可复用的 AST 编号；context reset、pop、内部 bool var 撤销后重新核对句柄。绝不能在发现句柄过期时直接向旧编号赋值。

### 5.6 不实现的东西

不为失效目标追加全局 UNSAT 认证；不分析 core；不因目标在一个 check 中为 false 就永久删除；不修改 `theory_lra::final_check_eh()` 的模型构造与整数可行赋值；不调用 `set_value_for_nbasic_column`。

---

## 6. 统一 broker，避免 A/B 与 HighDiv 的修改互相覆盖

### 6.1 新接口链

新增项目专用的 C/C++ 接口，建议命名：

```text
Z3_solver_set_coverage_guidance(...)
Z3_solver_clear_coverage_guidance(...)
Z3_solver_get_coverage_guidance_stats(...)
```

这些不是上游已有 API。实现时必须补齐 header、导出、build 注册、参数校验、异常边界和强引用管理。以结构化参数传递 atom hints、目标表达式、epoch、coverage_version、限制；不要把 JSON 当成决策热路径的输入协议。

路径为：

```text
LiaSampler / GuidanceBridge
  → api_solver层新增元数据接口
  → solver基类新增可选支持
  → combined_solver按原始分支路由转发
  → smt_solver / smt::kernel
  → smt::context::CoverageDecisionBroker
```

元数据安装不能触发 `check()`、`push/pop()`、原公式重建、外层 `assert()` 或额外随机数消费。原封不动保留 combined solver 的路由判断，只在它已经选择好的支持分支开始前装载计划；fallback 后端不支持时关闭当次指导并记录。

不能使用 context 全局开关误影响同一 Z3 context 中的 `ls_solver`。指导状态必须绑定具体 solver/内核及 query epoch，CCSS 调用前保证没有面向 LS 的指导安装。

### 6.2 `context::decide()` 中只有一个仲裁点

建议决策优先级：

```text
保留所有强制传播、特殊split和user-propagator优先权
    ↓
执行HighDiv原有普通变量选择与原生相位计算
    ↓
A-only / AB：原生原子有正分且额度允许 → 应用A相位建议
    否则
B-only / AB：存在未尝试、未赋值的活跃目标 → 优先B目标literal
    否则
完全使用原生普通选择
    ↓
统一的push_scope / decision assign / 后续传播
```

A-only 不改变变量顺序；B 可以插入/替换本次普通选择，但不得让被从原队列取出的原生变量丢失。源码已经在 `decide_user_interference` 改变变量时处理 `m_case_split_queue->unassign_var_eh(original_choice)`；参照其**真实队列契约**正确恢复未使用的原选择，而不是重复插入或遗漏。

原生 `var==null_bool_var` 的分支也要考虑 B 是否还有可合法尝试的目标；不能无条件把“没有原生候选”当作“没有目标”。同时无目标/关闭模式必须保持原来的提前结束路径。

一个实际 decision 只能记为 native、A 或 B 中的一类。不能先覆盖 A 再让 B 覆盖一次，却把两次都记录成实际生效。

### 6.3 AB 目标分工

同一窗口内，能够可靠绑定到**当前已存在原子**的目标优先留给 A。其余目标才可注册 B；不是根据未来模型决定分工。记录 `a_static_match`、`a_live_binding`、`a_actually_encountered` 三者，不能把静态存在当成实际遇到。

若已存在原子已被正常传播赋值，不能用 A 强行翻转；这属于当次状态，不是全局不可达。原子为false也不等价于对应bit目标不可达。AB 对该目标的具体 fallback 规则固定为：本 check 跳过，不再另建同目标 B 重复冲击相同已知分支。这个保守分工是本轮启发式，不是不可达推论，必须计入适用面统计。

AB 保留两个通道的额度，而不是让 A 永远抢完全部机会；详见固定参数。该组合是明确的优先/回退策略，不声称 A+B 的效果应当等于两者单独收益之和。

### 6.4 关闭行为

`off` 模式不构建引导目录、不创建目标、不调用新增 RNG，不修改参数和路由，不额外保持搜索状态。与 baseline 的共同测量代码相同。

在小型确定测试中核对：原生决策序列、原模型、assumption选择和随机数关键状态。真实墙钟轨迹可能因时序而不同，因此不能只用“限时运行模型不同”判断补丁错误，也不能忽略无指导时出现的确定控制流差异。

---

## 7. 第一轮参数：仅作固定工程选择，不宣称最优

把这些参数写入 `configs/round1.json`，在任何正式性能运行前冻结，8实例统一，不按实例调参。

| 参数 | 第一版值/规则 |
|---|---|
| seed | 0 |
| 指导启用 | 第一份正式模型之后；只在CDCL路径 |
| 单次目标窗口 | 最多8个单侧缺口 |
| 目标扫描 | 轮转，保留游标；不永久只取低位 |
| 单check A-only建议额度 | 最多4个实际选中机会 |
| 单check B-only尝试额度 | 最多4个目标 |
| 单check AB额度 | A最多2个、B最多2个，总计最多4个 |
| 指导决策窗口 | 每check前64个普通决策机会；特殊/传播不强行干预 |
| 同一TargetId | 每check最多主动尝试一次，restart不重置 |
| 每check新建B定义 | 最多2个，其余可复用已注册目标 |
| B累计注册上限 | 2048个不同目标；到限继续使用已注册者并记录cap，不清空solver |
| 单目标Reach/编码构建上限 | 4096个新建中间DAG节点；到限返回incomplete，不得当不可达 |
| 新增准备/目录/安装/诊断累计额度 | 会话900秒的5%，包括首次准备；到限停止新增指导，继续原有HighDiv |
| 单次可暂停的准备工作软限额 | 10ms；单次不可中断操作超额照实记录，不截断计时 |
| 本轮单check求解上限 | 保留HighDiv的原值，受剩余会话时间裁剪 |
| 目标评分 | 直接匹配的不同未完成bit数；相位平分保留原生选择 |
| 额外学习/重启/候选排序 | 无 |

说明：这些额度约束显式新增工作和干预次数，**不等价于**约束由指导引发的整个后续搜索成本。后者只能通过完整 check、CDCL/CCSS 周期及端到端结果衡量。

若正式运行前因正确性/构建问题必须更改工程限额，记录理由并重新冻结协议；不能看过8实例的覆盖输赢后改值再称同一轮。

不要复制上一轮算术候选池的“所有准备、验证和评分都必须在2ms完成”门槛。这里没有算术候选池，也不以未完成准备证明不存在可引导目标。

---

## 8. 外层主循环与正式输出

### 8.1 保留完整 HighDiv 流程

在 `hybrid_sampling()` 中，示意如下；这里的新增名字由你实现：

```cpp
while (!session_expired() && !formal_limit_reached()) {
    // 保留原cdcl_epoch循环与根据m_ls构造固定assumptions的顺序/RNG。
    for (size_t k = 0; k < cdcl_epoch; ++k) {
        if (session_expired() || formal_limit_reached()) break;
        auto assumptions = build_existing_highdiv_assumptions(m_ls); // 原逻辑
        auto plan = guidance.prepare_for_cdcl(current_coverage_version);
        // 只装元数据，不能借此改变solver种类或assertions。
        ScopedGuidance installed(cdcl_solver, plan);
        set_original_cdcl_timeout_clipped_after_preparation();
        auto result = cdcl_solver.check(assumptions);
        capture_check_and_guidance_result(result);
        if (result == sat) record_model(..., Source::CDCL);
        // 原HighDiv的SAT/UNSAT/Unknown流程保留。
    }
    if (session_expired() || formal_limit_reached()) break;
    // ls_solver没有指导；原seed与ls_timeout设置、模型恢复不变。
    run_existing_ccss();
    if (ls_sat) {
        m_ls = subgoal.convert_model(ls_solver.get_model());
        record_model(m_ls, Source::CCSS);
    }
}
```

不将这个伪代码机械替换原逻辑：尤其不要改变 HighDiv 根据输出数量、LS模型以及已有参数决定 assumptions 的条件。必须提交原流程与新流程的逐项差异清单。

### 8.2 HighDiv 的内部模型交换与原变量输出隔离

`record_model()` 接收 solver 的模型后，输出端只提取原始 AST 中实际出现的原始自由变量（Int/Bool 常量声明）。未在公式中出现的闲置声明不加入样本身份。新目标的辅助变量不参与样本身份，也不能进入 LS→CDCL 的随机固定列表。

原模型恢复和 HighDiv 内部 `m_ls` 保持原有生命周期。对输出做 model completion 时使用独立模型副本/原变量快照，不通过测量代码悄悄修改后续要交换的内部模型。

所有原变量排序固定（名字＋sort）；用精确值形成无歧义的身份键。Hash 仅用于索引/日志，发生 hash 相同必须比较完整键，不能只靠64位hash去重。

该原变量规范输出和截止适配在 HighDiv 基线与新方法上共同使用，报告名称写“统一编译与测量适配的HighDiv”。共同适配不得加入覆盖引导；HighDiv 不为新方法的目录或在线bit反馈付费。

### 8.3 `SampleSink::try_commit()`

事务顺序建议：

1. 检查会话截止与100样本限制。
2. 提取完整原变量赋值；验证原始F。去重原变量身份。
3. 新方法纯值求值并计算当次新增观察/covered；baseline不必在线计算覆盖。
4. 写 `.samples.raw` 的完整一行并flush，获得实际完成时间；写相应收据并flush。
5. 检查提交完成时刻是否仍在900秒内。只有及时完整事务计为正式输出。
6. 正式计数、seen状态、目标状态一起提交。截止后记录为late，不更新正式计数和反馈。

所有普通合法不同模型都可交付，零增益不筛掉。100样本模式计数的是正式的不同原变量模型，不是 solver SAT次数、候选数或新观察压缩后的样本数。

不要批次重排，不要为了减少磁盘时间只对新方法少记数据。原生基线与新方法的基本输出/收据格式一致；额外引导日志的实际成本由新方法承担。

### 8.4 `-n 0` 陷阱

上游 `hybrid_sampling()` 对 `maxNumSamples==0` 直接返回，**不能把现有 `-n 0` 当无限采样**。

共同适配增加明确的 `--unlimited-samples`/`std::optional<size_t> sample_limit`，不拿一个任意大常数冒充“没有上限”：

```text
time900:   sample_limit = nullopt, wall_limit = 900
n100_t900: sample_limit = 100,     wall_limit = 900
```

及时达到100即停止后续求解。为构建新目标临时增加的新变量不能让同一个原模型被误计成第101种不同样本。

### 8.5 截止与监督

共同 `t0` 在进程内公式加载之前建立，包含解析、预处理、首次求解、指导、验证、写出，不免费恢复历史前缀。

每次 check 前在准备完成后重新计算剩余时间。保留上游50秒/60秒额度，但不能授予超过本次剩余时间；LS整秒timeout必须检查0的实际含义，不能把不足1秒误传为“无限”。

监督器在900秒附近请求停止，信号handler只写原子/安全标志，不从信号handler调用Z3或写复杂日志。必要时用正常线程/API发出取消，所有算法采用相同测量/停止规则。给退出/归档有限宽限，硬超时和实际额外进程耗时单列。**900秒之后完成的模型不计分**，即使 solver 在此前已经找到了一部分赋值。

原有 UNSAT、错误或取消可以提前结束；不得为了填满时间伪造输出，也不得因为覆盖不增长或当前指导额度耗尽提前结束整次会话。

---

## 9. 正确性与机制测试：必须先于唯一一次正式基线

### 9.1 观察器差分

使用冻结 `calc_metric.py` 中 `ManualSatisfiesMetric` 和 `WireCoverageStatistics` 做独立参照。合成模型逐项核对 seen0/seen1、访问集合、原分母、Δobserved、Δcovered、前缀累积。

覆盖：负数、0、超过64位整数、bit63、共享DAG、AND/OR短路、整数ITE、布尔等式、深AST、常量、同名不同sort的拒绝/显式兼容处理。

### 9.2 A 语义与边界

- `x=10` 的 true 可建议对应常量位；false不能冒充相反位证明。
- NOT、等式交换的极性正确。
- 不能修改已传播变量，不干预特殊split。
- 没有原子匹配时真正走原生流程，不降级为未报告的随机flip。
- 双侧未见/双侧已见无建议；首次观察之后才出现相反需求。
- 原节点不被访问时不虚报命中或收益。

### 9.3 B 语义与回溯

必须包含至少以下端到端合成例，使用真实补丁库：

1. `0≤x≤15`，请求 bit3=1，确实发生普通目标决策并可输出合法模型。
2. 负数范围中对每个j的谓词结果与Python低64位精确一致。
3. `x=0`，请求 bit0=1：偏好不可行但原F可满足，solver仍能返回x=0，而不是把整个问题判为UNSAT。
4. `x∈{0,1,2}`，同时请求bit0=1和bit1=1：两目标不能同时满足，但单独可满足；要求能回溯放弃，不永久封禁任一目标。
5. 原式允许x=0或10，但本次HighDiv固定x=0：本次偏好冲突，下一次撤掉固定条件后仍允许尝试10。
6. ITE/OR中的未访问节点：只有Reach和bit同时成立才算目标实现。
7. 小有限输入穷举原变量投影，关闭/开启A/B后的合法解集合相同；辅助定义不丢原解。
8. 回溯、restart、pop、reset、不同solver同一context、取消/Unknown后的强引用与epoch安全。
9. 只改变辅助变量、原变量相同：输出仍视为重复。
10. 限额到达不会重复恢复额度，也不会关闭HighDiv剩余采样。

### 9.4 路由与关闭回归

- 新接口set/clear前后，combined solver路由标志不能因安装行为变化。
- 空assumptions与原生非空assumptions两种真实调用均测试。
- solver2未知后fallback时，没有悬空回调，也不会把LS solver装上指导。
- `off` 的受控操作轨迹与共同测量适配基线一致；不额外消费HighDiv随机数。
- 实际按动态库哈希确认补丁库被调用；“程序跑完但机制没执行”不算机制正确性通过。

### 9.5 构建测试

Release 与 ASan/UBSan 均通过新增测试和原有适用回归。不为新模块添加宽泛leak suppression；若发现上游已存在问题，保留可独立复现证据及精确例外，不掩盖新问题。

可对合成例做短冒烟；8个真实实例只做格式、AST、官方指标兼容性与接入检查，不按短跑覆盖调参数或取消某个不利配置。代码和参数冻结后才启动正式64次运行。

遇到错误模型、错误覆盖、丢解、悬空指针或基线测量协议错误，先停止、保存现场、修复并重新测试，不能用“有界实验”绕过正确性。正式基线未运行前完成这些工作，避免之后需要重跑唯一基线。

---

## 10. 日志：支持调试，但不把观测开销藏起来

### 10.1 每个会话最小文件

```text
config.json
command.txt
stdout.log / stderr.log
samples.raw
sample_receipts.jsonl
samples.formal
models.jsonl
queries.jsonl
guidance_events.jsonl
target_catalog.jsonl
summary.json
resource.csv
artifact_hashes.json
```

### 10.2 模型记录

记录正式序号、原始序号、来源CDCL/CCSS、原变量模型hash、查询号、开始/输出完成/提交完成时间、是否及时、是否重复、合法性、coverage_version、Δcovered、Δobserved、累计covered。

baseline没有在线covered时这些字段记null，由同一官方离线重放补充，不能填写猜测值。

### 10.3 查询记录

记录后端、query epoch、原有assumptions数量/身份摘要、原始SAT/UNSAT/Unknown及reason、timeout请求/实际授予、实际check时间、模块准备/安装/记录时间、模型提取/验证/写出时间、原生统计快照、CDCL/CCSS阶段、是否fallback。

统计快照不要未经核验直接当作每查询差值；层级包含计时不要重复相加。

### 10.4 引导记录

每次实际建议/尝试至少记录：

```text
target_id，原节点/bit/desired，coverage_version
A静态匹配与当前live binding；或B谓词/代理身份
原生变量与相位、最后实际变量与相位
来源native/A/B，decision level，ordinary ordinal
安装/内部化/relevance/实际尝试各阶段状态
同相位建议/实际改变/已传播/特殊分支/预算退出
最终模型是否产生、Reach是否成立、目标是否实现
是否新增观察/covered，正式模型来源与序号
```

保存目标定义的可重放SMT表达式或结构引用，在目录中存一次，不在每个事件重复全文。未遇到、未保持、目标编码未完成、路由不支持分别记录，不能全部写成“失败”。

只记录有限的跳过事件明细（例如每check前32条），其余保留准确计数和truncated标记。实际已实施的A/B事件最多4次，应完整记录。详细冲突/全决策轨迹默认关闭，避免重演大规模诊断开销。

### 10.5 归因边界

“目标实现”不是“该目标独立造成全部模型收益”；多个目标共享同一个最终模型，不能把其完整gain反复记账。B关闭后过去已内部化的表达式与学习历史也不消失。

没有实际介入的运行不能说证实了机制无效；其端到端性能仍应保留，原因写“接入/映射/额度/后端覆盖不足”。

---

## 11. 正式运行调度：8实例，16路，四个固定批次

### 11.1 输入与计划冻结

扫描用户指定 `benchmarks/` 的8个 `.smt2` 文件，按稳定相对路径排序，记录路径、字节SHA-256、logic与原变量/AST统计。恰好8个才冻结；不要擅自从HighDiv自带库补成9个，也不要丢掉难实例。

保存 `plan.json`：每个run的配置、预算模式、seed、优先CPU及允许CPU集合、命令、binary/library/input/metric哈希、输出目录、计划次序和空槽补位规则。实际分配CPU/启动时刻另写运行收据。提交代码和协议后再跑。

### 11.2 第一轮16槽队列

本轮按用户要求优先占用16个逻辑CPU；不要改回每物理核一个进程。使用固定优先顺序的任务队列：

| 队列优先块 | 8个time900任务 | 8个n100_t900任务 | 任务数 |
|---|---|---|---:|
| 1 | HighDiv | HighDiv | 16 |
| 2 | A-only | A-only | 16 |
| 3 | B-only | B-only | 16 |
| 4 | A+B | A+B | 16 |

这些块规定入队顺序，**不是等待所有16个任务完成才补位的屏障**。前16个HighDiv任务同步释放；之后某槽结束，就按事前冻结的队列顺序补入下一条任务，直到64项全部结束。不得根据覆盖好坏调整队列、杀掉难任务或跳过不利配置。

读取 `lscpu -e=CPU,CORE,SOCKET,ONLINE` 确认真实SMT sibling，不假定CPU0和CPU8必为同核。建立16个固定逻辑CPU worker，每个worker最多运行一个采样进程，进程及其超时辅助线程绑定该worker的逻辑CPU。初始16项可令同一实例的time/count任务使用同一物理核的两个逻辑CPU；后续按空闲worker补位，记录实际CPU而不伪造计划CPU。

同时有多个空槽时按CPU编号稳定分配；采样任务单线程，不能为每个worker再开启16路内部求解。监督器自身尽量低开销，不从16个逻辑CPU中强行预留一个导致长期仅15路。

100样本任务提前结束会改变并发构成，所以不同配置、不同实例不能宣称经历完全相同的瞬时负载。逐秒记录实际并发、每进程CPU、CPU时间与峰值RSS。后续轮次沿用同一机器、16槽规则、编译和预算协议，但不重新运行HighDiv；报告明确冻结参考基线的负载限制，不做事后“校正时间”。

采样队列运行时不编译、不审计、不压缩、不推送大文件。独立审计和归档在全部采样结束后执行，可使用16路。

### 11.3 HighDiv只执行一次

对 `baseline_seed0_v1` 创建不可覆盖的计划与尝试登记文件。每个实例/模式启动前原子写入attempt标记；完成后记录终态和哈希，整体完成后写 `BASELINE_FROZEN.json`。

后续轮次的运行脚本只校验并读取基线。基线损坏、缺失或因共同测量错误而不可用时明确报错，不自动启动补跑、不复用旧项目结果、不用guided-off的结果冒名替代。

第一轮正式任务总时限预算合计64×900秒，不包括构建和离线审计；这是任务预算记账，不是承诺实际完成墙钟。

---

## 12. 用HighDiv原覆盖脚本统一计分

### 12.1 冻结脚本，禁止替换指标

唯一正式覆盖百分比来源为固定提交的：

```text
HighDiv/my_scripts/calc_metric.py
```

所有配置同一个文件哈希、同一冻结Python/Z3环境、同一原始SMT2输入，不能评分加了指导目标的solver dump。

正式样本格式保持脚本可读取：

```text
0: x:3;y:-2;
1: x:5;y:0;
```

预先核对变量名、sort与分隔符兼容性。脚本的样本parser按整数解析；遇到不支持的名字/sort不能改脚本后还说同一官方口径。保存完整typed输出用于审计，并明确处理兼容性问题。8例若均为Int变量就直接沿用；Bool模型的官方wire与satisfies两条路径并不具有相同的输入处理方式，要分别验证，不混称支持。

### 12.2 正式文件的生成

`finalize_samples.py` 只依据完整收据和截止规则，将原始顺序中及时、合法、不同的已正式提交行复制到 `samples.formal`。禁止按gain挑行、排序或删零收益模型。迟到/截断/重复/非法行保留在raw并分别解释。

100模式的formal文件最多100行；超时只保留实际行数。空输出保持空文件和no_model状态。

### 12.3 必须执行的命令

```bash
"$BASELINE_VENV/bin/python" "$FROZEN_METRIC" \
  -f "$ORIGINAL_SMT2" -s "$FORMAL_SAMPLES" -m wire_coverage \
  > "$RUN_DIR/wire_coverage.stdout" 2> "$RUN_DIR/wire_coverage.stderr"
```

记录命令、退出码、脚本/公式/样本hash和原始stdout。该脚本wire分支使用 `ManualSatisfiesMetric` 求值；输出百分比只保留两位小数。

### 12.4 精确计数只能附加，不能改官方结果

另写只读 `evaluate_exact.py`，通过import固定原脚本创建原来的 `WireCoverageStatistics` 与 `ManualSatisfiesMetric`，逐样本调用原 `count_sample()`，读取其 `_storage` 并使用原 `node_count/node_total` 得到精确 numerator、denominator与seen掩码。

这个适配器不能改动原方法或注册行为，也不能自己删常量/不可达位/未访问节点改变分母。原脚本两位小数仍独立保留；精确计数用来识别被四舍五入掩盖的几十bit差别。

独立核对所有模型的合法性。原wire脚本即使对不合法模型返回false，其统计收集已经发生，所以“脚本打印了覆盖率”不等于样本合法。发现非法模型应将相应性能结果标为invalid并停止相关实验，不能删掉坏模型后继续宣布通过。

`-m satisfies --use-c-api` 的官方路径会调用SMT，且按Int声明处理样本；只有输入兼容时再运行。完整正确性审计优先使用原式具体赋值检查和原Manual求值交叉验证，不能把一个不兼容的satisfies输出当证据。

### 12.5 前缀与时间曲线

基于真实收据，从正式轨迹提取1、5、10、30、60、120、300、600、900秒前缀，以及1、2、5、10、20、50、100个模型前缀；使用同一官方类重放。

未到达k时记NA，不用最后一个模型替代第k个。`time900` 中的C100与单独`n100_t900`结果分栏，不当作同一次运行。

---

## 13. 结果表与中文总结

### 13.1 `time900` 主表

每实例列出：4配置的官方覆盖率、精确covered/total、正式模型数、首模型时间、AUC、CDCL/CCSS模型来源、退出状态；A/B/AB分别减冻结HighDiv的bit差和百分点差。

### 13.2 `n100_t900` 主表

每实例列出：实际模型数、是否达到100、达到100的实际时间（未达到为NA）、结束时的官方覆盖率、精确covered/total、状态。

完整8例的实际终点都报告，但只有双方都达到100时才能称为“严格相同100样本覆盖比较”。同时报告两边完成100的实例数，不能只报有利共同子集。

### 13.3 消融

分别比较 A−HighDiv、B−HighDiv、AB−HighDiv、AB−A、AB−B。跨实例均值使用原分母归一化后的百分点，对8实例等权；不能把大公式的bit总差当成总体平均优势。

一个seed不作显著性或稳定性结论。第一轮8实例均是开发/观察集；不声称泛化到所有LIA。

### 13.4 机制是否实际发生

逐实例报告：

- 单侧目标数量与被选窗口范围，Bool/Int、低/中/高位分布；
- A的静态映射、实际绑定、遇到次数、同原生相位与实际改变次数；
- B的编码完成、内部化、普通决策实际尝试、回溯放弃、最终命中；
- 不支持后端、固定assumptions下冲突、准备不完整、注册上限与成本停用；
- 每种机制完整显式成本、整体check成本和吞吐变化；
- 正式模型真实收益，首次观察与covered分开。

### 13.5 最终报告必须直接回答

1. 相对完整HighDiv，固定900秒是否提高？在哪些实例退步？
2. 独立100样本模式是否提高样本质量？有没有因为变慢而达不到100？
3. A、B是否实际生效，哪个更有价值？AB是否值得新增成本？
4. 当前失败主要属于无实际接入、目标映射不足、编码/准备成本、目标引起求解变慢，还是完整策略没有净收益？
5. 路由、CCSS、原随机流程和合法解空间有没有被错误改变？

如果结果不佳，完成负结果归档并提出下一轮建议，但不要本轮自动扩大目标数、追加seed、修改预算或重跑HighDiv。不能把内部对照的小改善当作已经优于HighDiv。

---

## 14. 推送与归档

### 14.1 Git流程

确认远端为：

```text
https://github.com/ChenKaichen-SCUT/guided_sampler
```

已有内容则先读取并保留，空仓库则初始化。使用独立分支，例如 `round1-ab-guidance`。禁止force-push覆盖用户已有分支。

至少形成这些可追溯提交：

1. 目录、上游/输入清单、冻结算法与实验协议；
2. A/B实现与通过的正确性测试；
3. 正式实验计划绑定的源码/二进制哈希；
4. 基线与新方法完整结果、审计、中文报告。

本地Git凭据可用时实际push并核对远端SHA；凭据不可用时保留本地提交、报告失败命令与原因，不询问/输出令牌，不声称已推送。

### 14.2 应上传的内容

上传新增实现、补丁、构建与运行脚本、配置、测试、协议、全部成功/失败结果、原始模型、查询/指导日志、官方计分stdout、精确计数、归档与重放说明。

原始日志无损压缩，按固定大小（例如每片50MiB）分片并记录每片和全部成员哈希，避免一个巨大文件阻断Git上传。保留从Git中实际可取得的归档片段，不只上传一个指向本地绝对路径的清单。压缩/推送放在计时采样结束后。

不上传虚拟环境、构建目录、临时下载、访问凭据。原8个输入默认保存相对路径和内容哈希；用户要求上传实现与实验结果，不据此自动把所有本地数据集/其他项目文件公开。已公开的输入可用来源说明实现重放。

### 14.3 不可改写的证据

正式结果目录禁止覆盖。参数或代码在正式实验后变化，应另立轮次，不覆盖上一轮日志。已有基线manifest与哈希固定，后续只读使用。

---

## 15. 完成标准

本轮“任务完成”不以覆盖必须上涨为条件，而以这些事实为准：

- 独立目录中实现了A/B与三种配置，未加入被禁止的其他机制；
- 真实HighDiv hybrid流程保留；关闭补丁兼容性与新机制正确性测试通过；
- 8实例×2预算×4配置的64次正式会话有完整结果或明确失败记录；
- HighDiv16次只执行这一批，后续复用；
- 官方脚本对全部可计分正式输出统一计算，原始百分比与精确bit计数相互核对；
- 100未完成、无模型、迟到、Unknown、非生效、成本退出均没有被删除；
- 报告如实区分性能结果、机制诊断和单seed局限；
- 实现与实验结果实际推送并验证远端SHA，或明确报告推送失败。

若发现严重正确性缺陷，在污染正式基线之前停止并修复；若已经产生正式失败现场，保留它，不能静默重跑替换。只有工程正确性阻断可以停止后续任务，不能因为早期性能不好而不执行事前冻结的正式矩阵。

最终回复用中文给出：提交SHA、分支、完整报告路径、64项完成情况、两个主结果表、A/B实际生效概况、正确性与独立审计结果、已知限制。不要宣称执行了未运行的实验或完成了未成功的上传。

---

## 附录 A：源代码依据与范围说明

本指引的函数与已存在行为取自下列固定版本；新增模块、broker、参数和实验协议是本轮设计建议，尚未在用户机器上实现或验证。

- H1（宿主主循环与输出）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/HighDiv/src/sampler/liasampler.cpp
- H2（epoch、变量固定比例）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/HighDiv/src/sampler/liasampler.h
- H3（CLI默认及0样本相关入口）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/HighDiv/src/main/main.cpp
- H4（统一指标及parser）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/HighDiv/my_scripts/calc_metric.py
- Z1（原生guess/decide、队列与实际assign）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/smt_context.cpp
- Z2（internalize、relevance等接口）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/smt_context.h
- Z3（默认solver路由）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/solver/combined_solver.cpp
- Z4（SMT solver到kernel转发）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/smt_solver.cpp
- Z5（不修改的算术最终检查入口）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/theory_lra.cpp
- R（上游构建说明）  
  https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/README.md
- S（SMT-LIB整数mod语义）  
  https://smt-lib.org/theories-Ints.shtml

附录中的公开文档用于解释语义，不允许用最新系统Z3替换HighDiv的冻结修改版。
