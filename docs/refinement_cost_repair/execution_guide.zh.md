# 观察保留改进器的成本修复与离线验证指引

仓库：`https://github.com/ChenKaichen-SCUT/guided_sampler`。

固定基点：`ae6da89e16be99142b7402fe6f0bccfb87e19893`。建议独立分支：`refinement-cost-repair`。本轮衔接已完成的 observation-preserving-refinement，不覆盖其 No-Go 结论和冻结证据。

**执行任务：完成成本定位、语义不变的代码修复、正确性与隔离验证、限定离线对照、oracle 编码成本对照、独立审计、中文报告、归档和 GitHub 推送。** 不止返回方案。本轮不运行真实在线采样会话、不运行 24 次短会话或 900 秒矩阵；即使离线取得正收益，也只提交下一阶段是否值得进入在线检验的判断。

## 1. 本轮要补上哪一段证据

上一轮真实序列共有 43 个原生模型，完整候选评价为 0：convert 因预处理超过 100 ms 关闭；random 的方向池为空，10 个等式分量被规模限制跳过；real 建成 177 个方向，但首个方向处理尚未完成就耗尽事件预算。12 个 oracle 案例均在总截止前没有交付答案，且没有留下检查启动前必须写出的检查点。

据此只能确认：当前实现与冻结预算组合没有给出真实改进，尚未测到真实候选的保护拒绝率和覆盖增益。不能将失败解释为“保护条件过强”“问题不存在更好模型”或“SMT 已证明很难求解”。

必须区分以下证据层次：

| 命题 | 当前证据 |
|---|---|
| 旧覆盖相位指导可能损失其他位置的覆盖 | 第四、第五轮样本集合比较支持 |
| 某个覆盖模型对应的交换 map 可拖慢 CCSS | convert 的固定构造交叉重放支持，范围限于该捕获 |
| 替代输出可与原生反馈隔离 | 已在真实发生替代的受控测试中验证 |
| 真实输入存在保留全部新增观察的有益候选 | 尚未建立，上一轮未完成候选评价 |
| 这些候选能在低成本预算内找到 | 尚未建立，上一轮成本关卡失败 |
| 低成本替代能提高等时间、等样本覆盖 | 尚未开展在线验证 |

**识别旧机制的一种失败原因，不等于新机制的收益链已经成立。** 状态隔离可以阻止替代模型直接污染反馈，但不会自动生成有益替代；完整保护约束输出质量，却不会自动保证候选存在或便宜。上一份指引中的 100 ms、20 ms 和分量上限是首版工程选择，并非已验证的最佳值。

本轮的具体任务是使“取得方向 → 完成可行域 → 产生参数 → 完整评价候选”能够在真实输入上被测到，并定位剩余失败。成本下降和覆盖提高分别验收，不能合并成一个“成功”。

## 2. 冻结范围与不可改变的条件

### 2.1 读取与保护

读取基点的：

1. `docs/refinement/results.zh.md`、`implementation_contract.zh.md`、`known_boundaries.zh.md`。
2. `manifests/refinement/implementation.json`、`offline.json`及 `configs/refinement.json`。
3. `results/refinement/analysis/final_v1/{failure_reasons,record_boundaries}.json`。
4. 第五轮 43 模型的输入 JSON、原始模型、收据、AST 和官方指标哈希。
5. `archives/refinement/RESTORE.md`及逐成员哈希。

实际源码包括 `include/refinement/`、`src/refinement/cli.cpp`、`session_commit.inc`、`native_output_split.hpp`和 `scripts/refinement/`。构建树由补丁生成，实施时核对真正使用的头文件依赖、生成树、动态库和二进制，不只修改模板文件。

保持基点已采用的 Ref 原生策略、第六轮 65536 停滞守卫和原动态库不变。本轮不重新验证或修改守卫，不改变参考来源、map、m_ls、RNG、后端路由和原生计数。

### 2.2 保持算法选择不变

保持完整保护、官方 Reach/短路访问、原 AST 身份、Int 低 64 位、Bool 一位、完整原式合法性、输出去重与事务。数值缓存与正式观察始终分开。

以下参数均继承基点，不扫描、不提高：

| 项目 | 固定值 |
|---|---:|
| 生产式离线预处理 CPU/墙钟上限 | 各 100 ms |
| 生产式离线事件 CPU/墙钟上限 | 各 20 ms |
| 三实例各条序列可选累计 CPU/墙钟绝对上限 | 各 6 s，沿用 120 s 的 5% |
| 等式分量规模 | 64 变量、128 行、4096 非零项 |
| 方向池 / 每事件方向 / 每方向目标 | 256 / 16 / 8 |
| 每方向—目标参数 / 每事件完整候选评价 | 4 / 64 |
| 一维域区间 / 操作上限 | 4096 / 200000 |
| 中间整数位长 | 4096 bit |

不添加新方向、随机移动、多步爬山、目标约束、MaxSMT、保护放松或新的调度策略。相同历史、相同完整计算工作量下，方向、目标和参数的选择顺序必须保持。

只允许改变计算复用、等价的数据表示和诊断记录。减少重复运算会让同一墙钟内完成更多原有步骤，这是需要检验的效果。不能先换候选规则，再把差异归因于缓存。

### 2.3 两种预算轨道必须分开

**生产式上限重放**：使用上表 100/20 ms 与 6 s 上限，评价当前实现是否在原有预算内取得进展。

**成本诊断探针**：只为完成并比较固定工作负载，预处理最多 2 s、每个固定位置最多 500 ms；所有其他离散限制保持不变。探针结果不能写进生产式覆盖表，不注入后续候选排序或输出历史。

诊断采用较宽预算是为了看清被 20 ms 截断的工作，不是调参获胜。旧、新实现都使用同一个预登记上限，禁止看到结果后继续延长。

历史逐模型原生 CPU 信用仍缺失。本轮不运行新原生采样补齐，也不以墙钟、全场平均或后续失败耗时代替。主表必须标注 `historical_cpu_credit_proven=false`；满足固定上限不等于已证明满足原来的“原生 CPU 的 10%”双信用策略。

## 3. 先让取消位置和成本可见

### 3.1 修复未完成方向不落盘的问题

目前 `prepare_direction()` 在完成后才将局部 `log` 加入 `result.directions`；时间异常向外传播时，正在处理的方向与阶段容易丢失。先建立方向记录槽，再开始工作，用不抛异常的清理逻辑记录未完成状态。

建议新增以下接口，名称是本轮设计，不是已有 API：

```cpp
enum class RepairStage {
    ParseInput, CopyAst, CompileTerms, DependencyIndex, CollectEqualities,
    Components, Elimination, VerifyDirections, BuildAffected, Metadata,
    Protect, ScoreBase, RankDirections, NumericValues, LineTerms,
    FormulaDomain, TargetSelection, ModularHits, CandidateBuild,
    ValidateFormula, OfficialObserve, PreserveAndScore, SerializeResult
};

struct StageRecord {
    uint64_t calls, nodes, edges, cache_hits, cache_misses;
    uint64_t full_size_allocations, full_size_scans, budget_checks;
    double inclusive_cpu, inclusive_wall, exclusive_cpu, exclusive_wall;
    bool completed;
    unsigned current_node, current_direction;
    // 当前事件、位置和取消原因使用稳定身份。
};

class StageScope; // 析构 noexcept，不分配大对象，不调用会抛出的预算检查。
DirectionRecord& begin_direction_record(unsigned direction_id);
void finish_direction_record(DirectionRecord&, Status, CancelReason);
```

阶段计时只在阶段边界读时钟，不给每个 AST 节点都加两次系统时钟读取。节点循环记录整数计数器及最后节点编号即可。保持原预算检查机制和频率，本轮不通过稀疏化检查来获得速度差。

取消时至少保存：阶段、方向身份、已经处理的节点数、缓存命中/未命中、已经完成的域/候选数、剩余工作是否未知。`not_started`、`incomplete`、`unsupported`、`exact_empty`必须分开。

### 3.2 非重复相加的成本表

报告以下成本且避免嵌套重复相加：

1. 输入解析和独立 AST 构造。
2. 预处理算法本身，各子阶段的 exclusive 时间。
3. 元数据构造、序列化和输出。
4. 每个事件的保护构造、排序、数值、域、模命中、验证、观察、评分。
5. 事件日志序列化、收尾和全部进程成本。

特别检查 convert 的超时是否发生在真正的数学预处理，还是 `Refiner::metadata()` 和 JSON 导出。基点 `cli.cpp` 将这些都放进预处理窗口；不能把它们漏记后宣称预处理变快。

计数器要能估计 `k 次子项求值 × N 大小数组/扫描` 的工作量；同时记录依赖集合总条目、系数总条目、方向影响集合总条目、消元操作和时钟检查次数。不能仅凭看到 `std::set` 或缓存命中率高，就宣布它是主要耗时。

## 4. 修复一：共享精确数值，不创建观察轨迹

### 4.1 已确认的代码路径

`LineDomain::truth()` 对不受当前方向影响的子项调用 `evaluate(..., false, node)`；`affine_on_line()` 对不随方向变化的非仿射项也调用它。

但 `observations.hpp::evaluate()` 每次都创建全 AST 大小的 values/zero/one 数组，并在返回前扫描整个 AST 生成掩码。`official=false` 没有消除这些成本。它可以作为正确性参考，不应继续作为频繁的“只求一个子项数值”的热路径。

### 4.2 新增模型数值缓存

```cpp
struct AnchorKey {
    FormulaIdentity formula;
    uint64_t native_event_id;
    AssignmentIdentity complete_assignment;
};

class NumericEvalCache {
public:
    NumericEvalCache(Ast const&, AnchorKey const&, Assignment const&, WorkBudget&);
    Big const& value(NodeId, WorkBudget&);
    bool ready(NodeId) const;
    // 私有数据只有数值、有效标记和计算栈；不含 seen0/seen1/Reach。
};

Big const& evaluate_value_only(NodeId, NumericEvalCache&, WorkBudget&);
```

同一原生模型的所有方向共享一个缓存。以完整原变量赋值和公式身份确认归属，不能只靠输出 coverage version；下一原生模型必须换代或清理。多个真实硬条件若有不同 AST，要拥有不同公式身份。

每个缓存槽只分配一次、按需计算。不得每次 `value(node)` 都重新清空 N 个槽；允许每个模型一次 O(N) 初始化，但要计时。若使用 generation 标记，处理版本回绕并记录清理成本。

求值沿用原有精确数值语义和操作顺序，AND/OR/ITE 仍按需求孩子；不要为了“全量缓存”强行求未选分支，触发本不会访问的除零或 unsupported 运算。缓存里数值正确不代表该节点属于官方观察轨迹。

可复用已验证原生轨迹中的数值，但必须确认原节点身份及完整赋值相同，复制成本计入本事件。首版也可从空缓存开始；这一选择在实施前冻结，不按某个实例单独切换。

异常和取消时，只保留已经完成且属于当前 anchor 的槽；正在计算的槽不能变成默认零或永久的 ready。避免递归栈深度风险，沿用显式栈，并解决临时对象悬空引用。

### 4.3 替换调用点

```cpp
// 原来：每次为子项构建整棵 AST 的 ObservationTrace。
auto ev = evaluate(ir.ast, anchor, budget, false, node);

// 修改后：只取精确值。下行不会产生任何覆盖观察。
Big const& v = numeric_cache.value(node, budget);
```

`LineDomain` 构造函数接收缓存引用；`affine_on_line()` 的不变非仿射分支使用同一缓存。不要每个 `LineDomain` 再创建一份模型缓存，否则失去跨方向复用。

支持的仿射项，其沿线常数部分等于该项在 anchor 下的精确值，可以共享；相同方向中重复请求同一个 `LineTerm` 也应缓存，供原子域和目标命中共用。首版常数仍按旧仿射系数点积顺序计算一次并缓存，斜率也按原有系数顺序计算，不另换数值移动算法。

数学等价不自动意味着 4096 bit 中间数限制下的退出行为等价。例如，按原始表达式求值与按已经合并的仿射系数求值可能出现不同大小的中间量。因此不要未经核验就用原表达式数值缓存替换所有仿射点积；值缓存先替换旧 `evaluate(..., false, node)` 的同语义调用，仿射点积使用单独的按 anchor 缓存。

`LineTerm` 缓存身份至少包含公式、anchor、完整方向；只存在于当前事件的方向上下文，不能把 m 上的常数带到下一个模型。若以后跨事件保存斜率，只能保存与 m 无关的部分，本轮不需要这种额外优化。

`observe_official(candidate)`、合法性检查、完整保护检查及输出账本保持原接口和独立状态。数值缓存不能提前更新 `output_seen0/seen1`。

### 4.4 应测到的效果

对于同一模型下重复请求的数值节点，缓存未命中后的节点求值次数应受已请求依赖 DAG 的规模约束；不能每次请求重新初始化和扫描 N 个观察槽。记录实际工作量下降及模型缓存内存。

不能将“避免了这条重复路径”直接写成“整个改进器从二次变成线性”。方向域、区间运算、目标选择及大整数运算仍有各自成本，必须分别测量。

## 5. 修复二：用原 DAG 反向索引表达精确影响关系

### 5.1 当前预处理会物化大量传递依赖

`compile_affine_ir()` 为每个节点构造全部依赖变量的集合；`build_integer_directions()` 又将这些集合反向组织成 `node_uses`，最终形成每条方向的 `affected`。

在大公式中，节点—变量传递依赖的总条目数可能远大于原 AST 的节点与边数。此处允许改变存储与构造方式，但必须得到与旧实现完全相同的**语法依赖**，不能借机删除抵消变量或简化原 AST 观察点。

### 5.2 建立直接父边与变量出现点

```cpp
struct DependencyIndex {
    std::vector<std::vector<NodeId>> parents;
    std::vector<std::vector<NodeId>> variable_occurrences;
};

DependencyIndex build_reverse_index(Ast const&, WorkBudget&);
AffectedNodes collect_affected(DependencyIndex const&,
                              IntegerDirection const&, ScratchMarks&, WorkBudget&);
bool depends_on_direction(NodeId, AffectedNodes const&);
```

对方向中所有非零原变量，从其 AST 出现点沿父边遍历，取得祖先闭包；结果去重并按原节点编号排序。它应与“该节点的原始变量依赖集合和方向支持集有交集”完全等价。

即使某项是 `x-x`，它在旧语法依赖中仍依赖 x。新实现也应将它标记为 affected；不要用代数抵消改变方向评分、目标排序或 unsupported 判定。

替换位置：

1. `compile_affine_ir()`：Shared 模式不再物化每节点完整变量集合，仿射项系数提取和等式行保持不变。
2. `build_integer_directions()`：方向形成后用父边索引构造 affected，仍按旧顺序、旧规模限制和旧池上限工作。
3. `LineDomain::truth()`、`affine_on_line()`：使用当前方向的精确 affected 标记判断不变性。
4. `select_directions()`：读取同样的 affected 节点集合，保持旧评分、排序和轮转。

父边索引必须包括所有实际孩子边、Bool 和算术节点、共享 DAG 及非仿射项。完整原变量声明身份保持一致。等式提取不能改成依赖简化后的公式。

每条方向的遍历与存储成本都计入预算。使用可复用标记数组，避免每个方向反复新建全局 set；一次必要的结果排序仍计时。缓存超过可用内存时明确记录并停止相关修复功能或回退旧等价计算，不静默少选方向。不得创建节点数乘方向数的稠密 BigInt 表。

### 5.3 random 在本轮仍可能没有方向

严格保留 64/128/4096 分量限制，因此 random 的 10 个超限分量仍应被跳过。**这是预期的控制结果，不是允许临时加大阈值的理由。** 若缓存修复后 random 突然出现原本不该出现的方向，先检查数据或算法是否已改变。

对被跳过分量只做结构报告：变量、行、非零项、行长度分布、单变量等式、二变量单位关系、显式定义等式及相互依赖情况。没有完成精确秩计算就填写 `rank_unknown`，不把“跳过”写成“无自由度”。不生成新方向，不解新 SAT/SMT，不把结构诊断产物送入候选池。

如果 convert 的主要成本其实是消元或系数展开，以上两项修复可能仍不够。本轮据实报告，不临时增加新的稀疏消元算法或改变表达支持范围。

## 6. 三个固定实现配置及语义等价要求

同一个 Release 构建提供以下配置；选择发生在会话创建时：

| 配置 | 数值与 LineTerm 缓存 | 依赖表示 |
|---|---|---|
| Legacy | 旧路径 | 旧完整变量集合 |
| ValueCache | 新缓存 | 旧完整变量集合 |
| Shared | 新缓存 | 新父边索引与精确 affected |

Legacy 复用基点算法，只有共同阶段记录和实验外壳变化。不能直接拿历史运行时间与新实现作加速比较。诊断日志种类、序列化内容和计费边界保持匹配；如果减少了日志冗余，必须同时作用于三个配置并单列，不能记为缓存收益。

本轮不优化 `WorkBudget::check()` 的读取频率，不减少最终观察/验证次数，不延后应计费的工作，也不预先将新配置的索引放到计时窗口外。每个冷序列从空数值缓存、空反向索引和未构造方向池开始。

### 6.1 固定工作量下核对什么

在双方都完整结束的同一输入上，逐项核对：必需等式、分量与跳过原因、方向向量与身份、affected 集合、方向选择顺序、目标列表、规范化区间并集、命中参数顺序、候选完整赋值、合法性、实际观察、保护缺失集合、得分及选择结果。

墙钟截断后的候选数量可以不同；不能要求新配置只做与旧配置相同的前几步。等价性用较宽预算探针或合成固定工作量测试验证，不以“输出恰好相同”代替内部语义核对。

位长、unsupported 和域操作上限仍可能中断计算。缓存不应将错误状态当成数值；未完成结果不是空域。任何完成结果不一致，停止真实离线评分，先保存并修复正确性错误。

### 6.2 需要新增的针对性测试

1. 同一 anchor 的多个方向反复请求共享子项，精确值一致，第二次请求不重建整棵观察数组。
2. 下一 anchor 的值变化，旧缓存不会命中；输出历史单独变化不应污染原数值。
3. 深 DAG、共享 DAG、短路、数值 ITE 的未选分支、负数、高位及取消恢复。
4. 数值缓存已有某节点值，但官方候选没有访问该节点时，保护仍拒绝该观察缺失。
5. 对小 DAG 穷举方向支持集，父边闭包等于旧变量依赖交集；含 `x-x`、共享孩子、多个原变量出现点。
6. 原生状态隔离仍使用确实发生替代的既有夹具验证，保留 map、m_ls、RNG、参考、原生计数和反馈检查。
7. 取消发生在预处理、首方向、模命中、候选验证各阶段，日志都有当前阶段和方向，不会把 incomplete 计为 completed。
8. 成本账本含冷初始化、失败候选、元数据和收尾；日志尾部超支单列，未完成输出不进入覆盖。

Release、ASan/UBSan 与独立任意精度/官方观察核验全部通过。既有大规模合成数学测试直接复用，不新增与真实结果相关的调参输入。

## 7. 固定成本诊断探针

固定原生位置为三个实例各第 2、3、4、5 个，共 12 个；每个位置都使用同一原生前缀作为 S，不能带入另一个探针的输出。与原 12 个 oracle 案例对应，便于对照。

每个配置、每实例一个独立 worker：预处理至多 CPU/墙钟各 2 s，随后四个位置各至多 CPU/墙钟各 500 ms；worker 墙钟保护 5 s，退出延迟另计。离散算法上限和完整保护不变。预处理失败则四个位置标为未进入，不用备用模型替换。

总计 **3 配置 × 3 实例 = 9 个诊断 worker，最多 36 个位置处理**。Legacy 的 3 个 worker 在成本修复前、共同仪表完成后执行，用于定位；ValueCache 与 Shared 的 6 个在修复冻结后执行。各项只执行一次。跨这两个阶段的墙钟只作为诊断记录，不作严格配对加速主结论。

每个 worker 使用同一原 AST 和同一原生序列；允许公式不变的结构在四位置间复用，但模型数值缓存必须换代。第一位置冷、后续共享的范围明确记录。较宽预算下产生的模型只是诊断产物，不能用于主离线序列、未来排序或在线交付。

报告至少回答：

1. convert 停在具体哪一阶段，主要是系数/依赖/消元/元数据中的哪一项？
2. real 的 20 ms 原窗口内实际完成了多少工作；给定诊断上限后是否能够完整处理方向？
3. 不变子项重复评价的次数、全数组初始化/扫描量，在修复后是否消失？
4. 同一固定请求在旧、新实现中完成时，值/域/候选是否完全一致？
5. 有候选但因保护失败、有候选但无额外收益、仍无候选，各占多少？

如果 Legacy/Shared 在诊断上限仍不能完成，只能报告未完成和工作进度，不填写精确加速倍数；若旧配置超时而新配置完成，只可给出基于截断时间的下界并明确删失。

## 8. 生产式上限的离线验证矩阵

### 8.1 同源数据与完整重放

仍使用 convert 27、random 8、real 8，共 43 个不同源模型，不增加真实采样、不替换序列。首模型固定原样输出。每个进程重新读取输入并冷启动；正常原生观察、预处理、可选改进、日志及进程总成本分别记录。

主评价为 L2：每个配置维护自己的输出历史，每步重新计算完整 protected；发生替代后不可继续用旧 Ref 历史。所有原生前缀核对观察包含；输出重复单列，不用双重输出凑样本。

L1 使用原生历史，比较同一候选池上的严格保护与不检查保护的评分，后者仅诊断；component_only 继续用于检查完整区间并集与包含 0 的局部区间差异。

### 8.2 新执行数与顺序

1. **主 L2 配对**：3 配置 × 3 实例 × 3 次预登记重复，共 27 条序列运行。
2. **补充 L1 与 component_only**：Legacy/Shared 两配置 × 3 实例 × 2 种模式，各一次，共 12 条序列运行。

总计 **39 条生产式上限离线序列运行**。这些重复只衡量固定输入下的时间波动，不是新 seed 或新模型证据。源数据仍是 43 模型；共处理 559 个含首模型的重放事件，不能宣传为 559 个独立模型。

固定一个物理核，顺序执行；三个主 L2 重复采用 `Legacy→ValueCache→Shared`、`ValueCache→Shared→Legacy`、`Shared→Legacy→ValueCache` 的轮换顺序。实例顺序固定。计时期间不编译、压缩、上传、运行 oracle 或其他实验。

在所有修复与正确性测试完成后才开始这 39 项；一旦开始，不因结果不理想改缓存策略、扩大预算或补做第四次重复。报告所有重复，给出中位数、范围和各次完成状态，不只保留最好的一次。

### 8.3 主表要能区分“更快”和“更有用”

逐实例、配置和重复报告：

```text
冷预处理 CPU/墙钟/状态，算法成本与元数据成本
保护/排序完成事件数
开始方向数 / 完整域数 / 不支持数 / 在途取消数
提出参数数 / 不同候选数 / 完整评价数 / 合法数
保留通过数 / 保留拒绝数 / 输出重复数
严格额外 covered 替代数 / 仅新增单侧观察替代数
每事件和全序列 covered，G1/G2/G3 得失
可选阶段 CPU/墙钟、必需阶段成本、完整进程 CPU/墙钟/RSS
预算超支、历史 CPU 信用缺项、逐前缀包含审计
```

每次替代保存原生和输出模型、完整保护掩码、实际观察及精确差集。有限候选零增益不能叫 UNSAT；保护拒绝很多也不能直接叫“保护过强”，应核对被拒候选丢失了什么。

若时间截断导致重复间输出不同，报告各次结果和发生替代的次数，例如 3 次中 1 次；不能只报出现正值的那一次。固定序列覆盖相等而计算成本下降，仍然只是成本修复，不是采样覆盖提高。

## 9. oracle 的独立编码成本修复

### 9.1 先记录到底停在哪

现有 `oracle_worker.py` 在 `check()` 前包括导入、读文件、解析 SMT、构造 Reach、历史观察、保护/额外目标编码、`solver.add()`以及 `to_smt2()` 导出。缺少 check 前检查点只能支持“尚未记录到检查入口”，不能单独归因为求解难或某一个编码阶段。

新增轻量阶段日志，最早在重型模块导入之前建立。每阶段进入/退出写入：stage、CPU/墙钟、已编码节点/观察数量、完整/未完成；父进程超时仍保留最后有效阶段。

```text
worker_start → imports → input_read → parse_formula → export_ast
→ reach_build → prefix_observations → protected_build → extra_build
→ solver_add → smt2_export → check_attempt → check_return
→ witness_validation → result_write
```

`check_attempt` 表示调用方准备进入 API；只有 `check_return` 才有返回结果。父进程强制退出时，不凭最后阶段推造精确内部 solver 步数。保留原始计数和推断的区别。

### 9.2 Reach 构造保持共享前缀

`reach_conditions()` 当前为 AND/OR 的第 k 个孩子重新构造 `cs[:k]` 条件列表。对一个有 q 个孩子的节点，这类前缀构造会累计包含二次数量级的 Python 参数引用。

替换成等价的共享前缀：

```python
guard = reach[parent]
for child in children:              # 原顺序
    incoming[child].append(guard)
    if op == AND:
        guard = And(guard, value[child])
    elif op == OR:
        guard = And(guard, Not(value[child]))
```

NOT、算术算子及比较保持既有访问规则；数值 ITE 的条件总被访问，两个分支分别受条件真/假保护。共享 DAG 节点的 incoming 继续取完整析取，不丢路径；拓扑顺序保持父到子。

这里减少的是重复构造成本，不缩小 Reach 条件。禁止通过只保留第一条入边、删掉原 AST 观察点或取消短路来压缩问题。

### 9.3 位谓词与目标按节点共享

缓存 `(node, bit)` 的正侧谓词，负侧引用其 NOT；protected 按节点合并，Reach 只合取一次。额外覆盖目标可由逐 bit 的 `Or(And(Reach, bit_hit))` 等价改为逐节点 `Or(And(Reach, Or(bit_hits)))`。

完整 protected 和完整额外目标集合不变。不得抽取目标子集、固定未要求的变量或让 oracle 只求一个更弱的值条件。避免逐项调用全局 simplify；记录共享后 AST 节点/边统计与构造成本，而非只比较文本长度。

所有公式相关共享只在本案冷进程中建立。不能先离线编译好 oracle，再把冷启动对照的全部成本与其热态成本比较。

### 9.4 oracle 固定对照与预算

固定同一 12 个案例，即三个实例各位置 2/3/4/5。配置为 `OracleLegacy` 和 `OracleShared`，共享新的阶段日志与执行外壳，算法差别仅为上述等价编码复用。

共 **24 个冷启动 oracle 案例，每案最多一次真实 check**。保持原整案 3 s、check 最多 2 s；实际 check 配额不得超过整案剩余时间。父进程记录终止与退出延迟，不计截止后的结果为预算内完成。不追加案例或重试。

本轮保持 `to_smt2()` 在 check 前、完整导出并计费，避免把文件导出移到截止之后造成不可比。若实测主要卡在导出，报告这一点；不要在本轮后半段另加“先求解后导出”的第三种对照。

每案例的加载、编码、导出、求解和验证成本分开；SAT 必须核验完整原式、Reach、保护和额外 covered。返回 SAT 后验证未在案例期限内完成时，分别记录求解答案与验证完成状态，不假称已交付可用见证。

新编码先通过原 150 个穷举点及针对宽 AND/OR、共享 DAG、NOT、数值 ITE 的补充等价测试。对小公式有限赋值穷举比较旧、新问题真假与解释器实际观察；真实实例不另做完整 XOR 求解，以免扩大真实 oracle 调用数。

oracle 仍全数截止时，报告最后阶段分布即可。这仍是一项有价值的定位结果，不因此延长预算或将截止写成 UNSAT。oracle 见证无论成功与否均不进入离线主序列。

## 10. 本轮验收分级和停止规则

### 10.1 四类结果分别报告

| 等级 | 必须具备的证据 | 不能据此声称 |
|---|---|---|
| 正确性通过 | 值、依赖、域、候选及保护等价，状态隔离和独立审计通过 | 真实性能提高 |
| 成本修复有效 | 匹配阶段重复运算减少，完成相同工作成本下降，或同预算完成更多原有工作 | 一定有更好模型 |
| 候选阶段可达 | 至少一个真实位置在 100/20 ms 上限内完整评价合法候选 | 候选保留通过或 covered 提高 |
| 离线机会成立 | 至少两个实例在主 L2 三次重复中均有严格 covered 增益、无观察丢失，全部成本如实计入 | 等时间在线获胜、历史 CPU 信用已验证 |

“至少两个实例”用于是否值得推进整体算法，不阻止如实报告单实例的成本修复或机会发现。random 空池在本轮保持是控制结果；只有 real 改善时，可以确认局部机会，不能自动跨过整体门槛。

不设随结果移动的加速门槛。报告相同已完成工作量的配对成本和截断情况；旧配置未完成时不用它的 20 ms 当作完成耗时算精确倍数。全局累计成本下降但 completed_evaluations 仍为 0，必须明确写出。

### 10.2 按观测结果定位下一问题

1. **仍停在预处理**：定位具体阶段，本轮保持 No-Go，不能说保护条件有问题。
2. **域完成但没有参数**：区分目标恒定、周期精确不可达、域无非零位置、unsupported 和有限搜索未完成。
3. **有合法候选但保护失败**：才开始讨论保护与候选构造是否冲突；保存丢失观察，不在本轮放松保护。
4. **保护通过但无覆盖增益**：说明这些固定方向/目标下候选质量不足，不能再只归因于计算慢。
5. **有增益但超预算**：说明存在改进机会，当前低成本目标尚未达到。
6. **固定上限内有增益**：形成可进入下一阶段的证据；实际生成供给、完整预算信用与等时间结果仍待在线检验。

本轮到离线报告结束，不自动执行在线短会话。若测试出现非法候选、错误缓存、观察包含失败、原生状态污染，立即停止真实评分，保存现场，修复后重新冻结受影响版本；不能保留错误版本的有利结果。

### 10.3 不允许形成无限修复循环

本轮仅有 ValueCache 与 Shared 两个预登记修复配置；oracle 仅有一种共享编码。修复后若暴露新的消元、候选质量或保护瓶颈，写进后续研究问题，不自动增加第三种生产修复、扫预算、改变分量限制或重新选择模型。

正确性修复允许重验，但正式离线矩阵开始后的修复必须废止并保留受影响尝试、记录原因和新冻结点。正确但性能不理想不属于重试理由。

## 11. 交付与审计

建议新建：

```text
docs/refinement_cost_repair/{execution_guide,implementation,results}.zh.md
include/refinement/{numeric_cache,dependency_index,cost_trace}.hpp
scripts/refinement_cost_repair/{freeze,profile,run_offline,run_oracles,audit,report}.py
configs/refinement_cost_repair.json
manifests/refinement_cost_repair/{plan,implementation,attempts}.json
results/refinement_cost_repair/{correctness,probes,offline,oracle,analysis}/
archives/refinement_cost_repair/
```

新入口不得覆盖旧 `frozen_v1`、旧原模型、旧报告、旧发布 SHA。复用旧代码时通过新参数或独立命名空间保留 Legacy，不复制全部历史工程。

记录每项 attempt 的配置、完整提交、源代码/二进制/动态库/输入/指标哈希、CPU 绑定、冷缓存状态、开始/结束、实际成本、退出状态及是否完成。执行器拒绝覆盖已开始尝试，不做自动重试。

独立审计复算所有新替代候选与最终输出的原式合法性、官方观察、完整保护、去重和逐前缀包含。检查 Legacy 与 Shared 在完成的固定工作量下的语义等价，以及随机流/map/参考未改变。

所有 canceled、unsupported、候选拒绝、预算超支、完整日志和原始模型无损归档。不能只归档最终被选候选而丢弃生成成本和失败证据。

中文报告必须直接回答：

1. 上一轮未完成的方向现在能否定位到具体阶段？
2. 重复整数组分配/扫描实际占多少，而不是推测占多少？
3. 数值缓存和父边索引分别减少了哪些工作和成本？
4. convert 是否完成冷预处理；random 的跳过分量是否保持；real 是否进入完整候选评价？
5. 低成本候选是否合法、保留、不同且严格增加 covered？
6. 无保护诊断与完整保护选择的差异来自哪些具体观察？
7. 三次固定输入重复是否都得到相同层次的进展，有无靠偶然截止获得的单次正值？
8. oracle 原先及修复后分别停在哪；是否真正进入 check，是否交付已验证答案？
9. 哪些只是成本下降，哪些形成真实离线覆盖机会，哪些仍然未知？
10. 原生逐模型 CPU 信用缺失如何影响结论，是否有任何时间被漏记或挪出窗口？

最后正常提交并推送独立分支，用 `git ls-remote`核对完整远端 SHA，保持工作区干净。不上传构建树、第三方二进制、虚拟环境或凭据。远端失败时保留本地提交并报告，不声称已上传。

## 12. 执行数量与顺序总表

| 阶段 | 规模 | 新真实采样 | 新真实 oracle check |
|---|---:|---:|---:|
| 冻结来源、共同阶段记录 | 只读及代码修改 | 0 | 0 |
| Legacy 成本探针 | 3 workers，最多 12 个位置 | 0 | 0 |
| 两项成本修复及合成正确性检查 | 固定测试清单 | 0 | 0，合成测试单列 |
| ValueCache/Shared 成本探针 | 6 workers，最多 24 个位置 | 0 | 0 |
| 生产式上限主 L2 | 27 条序列 | 0 | 0 |
| 补充 L1/component_only | 12 条序列 | 0 | 0 |
| 冷 oracle 对照 | 24 案例 | 0 | 最多 24 |
| 审计、报告、归档、推送 | 全部结果 | 0 | 0 |

执行顺序：冻结计划 → 共同仪表 → Legacy 探针 → 实现两项预登记成本修复与 oracle 共享编码 → 正确性/隔离通过 → 冻结新构建 → 新配置探针 → 39 条主/补充序列 → 24 案 oracle → 审计、报告、归档、推送。

较宽预算探针与旧源码位置用于定位和等价性检查；主离线矩阵使用原预算判断能否产生候选。两类结果分表，任何阶段不得混成一条虚构在线时间曲线。

## 来源与实现定位

1. [上一轮实际报告](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/docs/refinement/results.zh.md)。
2. [全数组求值与观察实现](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/include/refinement/observations.hpp)。
3. [一维域中的不变项求值](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/include/refinement/line_domain.hpp)。
4. [仿射表示与依赖集合](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/include/refinement/affine_ir.hpp)。
5. [方向构造与选择](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/include/refinement/directions.hpp)。
6. [候选生成、阶段异常和日志](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/include/refinement/refiner.hpp)。
7. [离线计费入口](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/src/refinement/cli.cpp)。
8. [oracle Reach 与位条件编码](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/scripts/refinement/oracle_encoder.py)。
9. [oracle 冷进程与检查入口](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/ae6da89e16be99142b7402fe6f0bccfb87e19893/scripts/refinement/oracle_worker.py)。

本文件给出待执行修改及验证协议；没有声称上述修复已经实现、实测加速或提高覆盖。
