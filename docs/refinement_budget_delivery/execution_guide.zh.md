# convert 原预算交付与 real 方向阻塞诊断：代码修改及离线验证指引

仓库：`https://github.com/ChenKaichen-SCUT/guided_sampler`。

固定基点：`2dde70ab203009afdb07e4337eb3cdd637906704`；建议独立分支：`refinement-budget-delivery`。本轮继承 refinement-cost-repair，保留其全部代码、No-Go 报告、失败与冻结证据。

**执行任务：实现 convert 通用路径的成本修复与有界交付，单独诊断 real 的方向阻塞，完成正确性、状态隔离、限定离线实验、独立审计、中文报告、归档和分支推送。不要只返回方案。** 不运行新原生采样，不重跑 HighDiv，不开展在线短会话或 900 秒矩阵，不运行真实 SMT oracle。本文件是待执行协议，不代表改进已经实现或必然成功。

## 1. 目标、证据与结论边界

### 1.1 本轮的两个任务

1. **任务 A：convert 的通用搜索流程在原预算内交付一个完整、合法、通过全部观察保护、严格增加 covered 的候选。** 生产式离线轨道仍为冷预处理 CPU/墙钟各 100 ms、每事件 CPU/墙钟各 20 ms，整条序列可选 CPU/墙钟各 6 s。不能扩大预算或硬编码已知见证。
2. **任务 B：解释 real 的已选方向为什么大多只有参数 0 合法，并有限检验“组合方向能否移动”。** 这是独立诊断，不向任务 A 的方向池、输出历史、原生状态提供任何信息。

任务 A 的目标是一个可检验的研究目标；正确实现后若仍未达到，必须完整报告失败，不能为得到正结果放松条件。

### 1.2 已知事实，禁止重新解释成未证明的结论

1. 上轮宽预算探针中，convert 第 3 个原生位置，两种缓存实现均找到方向 186、参数 3 的见证，保留 1049 个 protected 观察，新增 covered 比原生多 43。这是一个位置的真实存在性证据。
2. 正式 100/20 ms 轨道没有完整候选。convert 的预处理全部超时；某诊断位置的排序单独耗费 34.93 ms CPU。
3. Shared 的 convert 依赖构造比 ValueCache 便宜，但 affected 构造更贵：一次诊断为 4.735/75.173 ms 对 36.277/14.085 ms；完整预处理为 148.848 对 124.314 ms。real 的三次正式预处理也显示 Shared 更贵。
4. real 主 L2 中 ValueCache、Shared 完成的 101、105 个完整域全部精确为 `{0}`。这说明这些方向在这些 anchor 上不能移动，不说明原公式唯一可满足，也不是保护筛选造成的。
5. random 方向池为空；10 个超限分量仍被跳过。本轮保持限制，仅作为控制。
6. 上轮 24 个 oracle 均未进入 check；不能据此估计重新求解的完成成本。

### 1.3 本轮必须分开的结论

| 结论 | 所需证据 |
|---|---|
| 等价成本修复有效 | 相同已完成工作结果一致，重复运算下降，成本或预算内工作量改善 |
| 算法内已找到增益候选 | 完整合法性、官方观察、保护、去重和严格 covered 增益全部完成 |
| 原预算内已交付 | 冷预处理合格，事件的搜索、候选处理及交付相关尾部合格，实际提交了候选 |
| 单实例结果可重复 | convert 三次冷 L2 重放存在共同原生位置，三次均有合格严格增益交付 |
| 最终序列覆盖提高 | 整条 L2 的最终 covered 严格高于原生；与某个前缀的临时增益分开 |
| 方向组合解除阻塞 | 两个原方向的完整域均为 `{0}`，组合方向具有经验证的非零合法点 |
| 一般采样性能改善 | 本轮不作此结论：没有在线等时间实验，也缺历史逐模型 CPU 信用 |

保留 `historical_cpu_credit_proven=false`。即便达到固定 100/20 ms 上限，也不能声称已经满足原生 CPU 的 10% 双信用规则，或远低于重新求解的成本。

## 2. 读取、冻结与不可改变的条件

### 2.1 执行前读取

1. `docs/refinement_cost_repair/results.zh.md` 与本轮基点的实现说明。
2. `configs/refinement_cost_repair.json`、`manifests/refinement_cost_repair/`。
3. `archives/refinement_cost_repair/RESTORE.md`，按说明恢复原始探针、事件记录、`diagnostic_opportunities.json`、`protected_losses.json`、域分类和成本证据。记录各成员 SHA，不覆盖旧目录。
4. `results/refinement_cost_repair/analysis/sequences.csv` 和 `domain_records_v1/summary.json`。
5. 43 个冻结源模型、原 AST、输入来源、原生顺序、原始收据和官方指标身份：convert 27 个，random 8 个，real 8 个。
6. 真正使用的宿主模板、生成头文件、构建入口和动态库依赖。当前重点源码见第 3 节。

如果归档恢复或 SHA 核对失败，停止依赖该证据的步骤并报告缺项；不能另找“相似模型”替代。

### 2.2 固定语义

1. 原生 Ref 策略、map、m_ls、RNG、参考选择、搜索计数、反馈、后端、动态库以及 65536 停滞守卫不变。
2. 改进器只读原生模型；实际交付候选进入独立 output ledger，原生模型继续驱动搜索。
3. 保护集合仍是原生模型相对当前实际输出历史新增的全部 `(原 AST node, bit, side)` 观察。Reach、短路访问、原节点身份、Bool 一位及 Int 低 64 位规则不变。
4. 原式及既有真实硬条件的数学整数合法性、完整官方观察、保护、去重和覆盖计分均保留。
5. 方向、分量和消元顺序，方向归一化、编号、池截断、目标顺序、参数顺序、候选轮转均不改变。方向评分仍为 affected 节点的未 fully-covered bit 数；前 8 个按分数降序及 ID 升序，其余按原 event 轮转再取最多 8 个。
6. 不添加生产方向，不提高分量限制，不缩减保护，不改为仅检查保护数量，不复用数值缓存冒充正式观察。

### 2.3 固定额度

| 项目 | 正式轨道 |
|---|---:|
| 冷预处理 CPU / 墙钟 | 各 100 ms |
| 单模型可选 CPU / 墙钟 | 各 20 ms |
| 单序列可选 CPU / 墙钟 | 各 6 s |
| 方向池 / 每事件方向 / 每方向目标 | 256 / 16 / 8 |
| 每目标参数 / 每事件完整评价 | 4 / 64 |
| 分量变量 / 行 / 非零项 | 64 / 128 / 4096 |
| 整数中间量 | 4096 bit |
| 一维域区间 / 操作 | 4096 / 200000 |
| 原消元操作上限 | 200000 |

继续沿用 WorkBudget 的检查机制；不以减少时钟检查频率取得收益。删除已经被等价表示消除的循环允许减少检查总数，但仍存在的循环、算术及序列化边界保持检查。不得把索引、排序初始化、失败工作或尾部挪到“必需原生工作”名下。

### 2.4 唯一显式改变的停止行为

本轮为所有正式对照统一增加 `FirstCovered` 交付策略：

1. 保持原方向、目标、参数与候选评价顺序。
2. 首次完成一个非重复、合法、保护通过、`candidate.gain.covered > native.gain.covered` 的候选时，立即停止继续搜索，进入交付收尾。
3. 仅增加单侧观察的候选不会触发提前停止；正常结束或软截止时仍按原字典序规则保留已完成的最优候选。
4. 未完成的候选不能提交。严格增益按完整官方观察计算，不按目标命中估计。

这是明确的**停止策略调整**，不能归类为语义等价的缓存优化。四个正式配置都用同一策略，性能差异才能归因于下列成本修复。固定工作量等价测试关闭提前停止和时间截断，比较原搜索序列与最终选择。旧轮报告的时间不直接充当本轮配对基线。

## 3. 修改位置与配置

以下“已有”来自固定基点；“新增”是建议接口，实施者可以调整签名，但不能省略契约。

| 已有位置 | 本轮修改 |
|---|---|
| `directions.hpp::build_integer_directions()` | 稀疏验证方向；保持生成/交织/截断顺序；选定池后批量构造 affected |
| `affine_ir.hpp::compile_affine_ir()` | 新批量模式不再物化传递变量集合；保留原仿射系数与算术顺序 |
| `dependency_index.hpp` | 增加以方向位集传播语法影响的实现，不继续逐方向爬父边 |
| `directions.hpp::select_directions()` | 同分数、同顺序的共享及增量评分 |
| `refiner.hpp::Refiner::try_refine()` | 接入排名状态，记录首候选时间，统一 FirstCovered 与预算内收尾 |
| `affine_ir.hpp::LineValues::value()`、`line_domain.hpp::LineDomain::varies()` | 统一影响关系查询，避免新枚举值误入旧 dependencies 路径 |
| `cost_trace.hpp` | 新阶段、正确的方向身份、首次完成/准备交付时间；析构不抛异常 |
| `cost_repair_worker.cpp` 的新独立外壳 | 有界交付事务与 L1/L2 分离，保留旧入口 |
| 新 `direction_score.hpp` | 影响签名分组、精确评分状态与取消恢复 |
| 新 `line_blocking.hpp`、诊断 worker | 只用于 real 域来源、阻塞解释及有限组合 |
| 新独立 Python 审计器 | 重算影响、分数、等式点积、观察保护及诊断证书 |

同一个新 Release 二进制提供四种配置，不能用四个构建环境混杂比较：

| 名称 | 数值缓存 | 方向验证 | 影响关系 | 方向评分 |
|---|---|---|---|---|
| V0 | 基点 ValueCache | 原全行数组 | 原传递变量集合 | 原全 affected 扫描 |
| V1 | 同 V0 | 稀疏验证 | 同 V0 | 同 V0 |
| V2 | 同 V0 | 稀疏验证 | 批量方向位集 | 原分数扫描 |
| V3 | 同 V0 | 稀疏验证 | 批量方向位集 | 分组及增量精确评分 |

四种配置共享新交付外壳、FirstCovered、相同日志内容和软截止。Shared 的原逐方向父边遍历保留为历史实现，不作为更优基线，不另增正式第五配置。

避免把 RepairMode 同时用于所有策略的脆弱分支。建议显式拆成 `NumericStrategy / EqualityVerifyStrategy / InfluenceStrategy / ScoreStrategy`，会话开始时冻结。新模式的 `varies()`、非仿射不变项、hard AST、metadata 均必须走正确接口。

## 4. 修复 A1：稀疏验证保持全部强制等式

### 4.1 当前成本

现实现对每个方向创建 `vector<Big>(eq.rows.size(), 0)`，按 `equation_uses[v]` 更新后，再扫描全部等式行。未受方向影响的行必为零，但每条方向仍支付完整数组构造和扫描。

### 4.2 实现

建议增加：

```cpp
struct EqualityIncidence {
    // 保留原变量顺序和每个变量的原等式行顺序。
    std::vector<std::vector<std::pair<RowId, Big>>> uses;
};
class SparseRowAccumulator; // 一次分配，epoch + touched rows
void verify_direction_sparse(IntegerVector const&, EqualityIncidence const&,
                             SparseRowAccumulator&, WorkBudget&);
```

1. 建立 incidence 时覆盖所有强制等式的所有非零系数，检查行号、变量身份与重复条目。其构造计入预处理。
2. 按原 `dir.values` 顺序遍历变量，按原 incidence 顺序执行相同 `checked_mul/checked_add`；不能改点积的加法次序，以免改变中间位长行为。
3. 用 epoch 标记本次触及的行，第一次触及时把累加器置零，最后只检查这些行是否为零。
4. 未触及的行与方向支持集没有交集，点积按结构恒为零。此理由应写进实现说明，不能声称“忽略其他等式”。
5. 允许一次全行槽分配；不允许每方向清零所有 Big。epoch 回绕完整清理计费。取消不能使下个方向读到上次半成品。
6. 最终 touched 行可按原行号检查。方向生成、标准化、去重和入池规则完全不变。
7. 分量清空、位长退出及消元操作额度保持旧语义。记录预处理方向身份 `(component, local_id)`，入池后补稳定 pool ID，不再只有 -1。

### 4.3 验证

独立 Python 用任意精度整数，对每条完成方向重算**全部原强制等式行**的点积，必须全为零。比较 V0/V1 的方向向量、顺序、分量状态与 omitted 数；故意损坏 incidence 或方向的测试必须被发现。记录总行数、方向数、实际触及行数、槽初始化数、乘加数和验证时间。

## 5. 修复 A2：一次传播整个方向池的语法影响

### 5.1 不再使用逐方向祖先遍历

方向池最多 256 条，可以用每节点最多 4 个 uint64_t 表示“哪些方向会影响此节点”。这是普通位集，不是节点乘方向的 BigInt 表。

建议接口：

```cpp
struct InfluenceIndex {
    unsigned direction_count;
    std::vector<DirectionBits> node_directions;
    // 按原节点 ID 升序的 affected 向量仍供原候选代码使用。
};
InfluenceIndex build_direction_influence(Ast const&, DirectionPool&, WorkBudget&);
bool varies(NodeId, DirectionId, InfluenceIndex const&);
```

### 5.2 批量算法

1. 先按旧流程完成方向生成、分量交织、归一化、去重、256 截断和编号。不能先保留“看起来有用”的部分方向。
2. 建立每个原变量的方向位集：方向该变量系数非零则置位。构造也计入预处理。
3. 沿 `Ast::postorder` 从孩子到父节点计算：
   - 变量节点取对应变量位集；
   - 其他节点取全部孩子位集的 OR；
   - 常量为空。
4. 保留 Bool、算术、共享 DAG、未选 ITE 分支和所有原节点。对 `x-x` 仍保留 x 的语法影响，不作代数消去。
5. 按原 node ID 从小到大枚举每节点置位的方向，将 node 加入对应 `affected`。由遍历顺序保证与旧版排序结果相同。
6. 元数据仍输出同样的 affected 集合。每个节点只为全部方向传播一次；记录节点、边、位集字数、OR 次数及最终 incidence 数。
7. V2/V3 的仿射编译不再构造完整传递变量集合或不需要的反向索引。为了影响传播而恢复一次全依赖构造，会抵消本修复。
8. 预处理峰值内存、位集和 affected 向量均计量；池为空时直接生成空索引。按节点数和方向数检查分配溢出，不静默截断影响集合。

近似工作规模为“节点及边数量 × 位集字数 + 最终 affected 条目数”。这不是保证整个预处理线性，也不保证正式预算内完成，必须实测。

### 5.3 接入的容易出错处

1. 新模式不能因为 `mode != Shared` 就访问空的 `ir.dependencies`。统一影响查询接口。
2. `LineDomain` 与 `LineValues` 对同一方向使用同一不可变视图；引用的方向池和索引必须比它们活得更久。
3. 真实 hard AST 有自己的公式身份和节点空间。不得拿主公式的节点位集查另一 AST；按现有变量映射为各 AST 建立正确索引并计费。不能删除 hard 条件以通过测试。
4. 方向组合仅在 real 诊断中出现，使用独立影响计算，不能复用错误的原池 ID。
5. 原根和不可达但保留的 AST 节点按照旧编译遍历规则处理，不更改观察宇宙。

## 6. 修复 A3：方向评分共享，并精确跟随输出历史

### 6.1 保持原评分

节点 n 的权重为：

`weight[n] = popcount(mask[n] & ~(seen0[n] & seen1[n]))`。

方向 d 的分数为其全部 affected 节点权重之和。只看 fully-covered bits，不改为保护大小、目标数、梯度或受阻程度。排名仍严格使用原比较器，随后执行原 8 + 8 选择。

单侧观察首次出现会影响目标选择，但不会直接降低这个方向分数；不要把 observed 与 covered 混用。

### 6.2 合并相同的方向影响签名

V3 在冷预处理内，将方向位集完全相同的节点归入同一组：

```cpp
struct InfluenceGroup {
    DirectionBits directions;
    uint64_t maximum_weight;
};
struct ScoreIndex {
    std::vector<GroupId> node_group;
    std::vector<InfluenceGroup> groups;
};
struct ScoreState {
    FormulaIdentity formula;
    HistoryIdentity history;
    uint64_t version;
    std::vector<uint64_t> covered_snapshot;
    std::vector<uint64_t> group_weight;
    std::vector<uint64_t> direction_score;
    bool valid;
};
```

1. 精确比较全部方向位，哈希碰撞必须做相等核对。空签名节点不贡献任何方向分数，但仍存在于官方观察。
2. 每组最大权重等于成员节点 mask 的 popcount 之和。初始化组权重、方向分数以及快照的成本全部计入冷预处理。
3. 同一组可以只把组权重向每个相关方向累加一次，避免为大量具有相同影响签名的祖先节点重复更新。
4. 记录原 affected 总条目数、不同签名组数、分组后的“组—方向”条目数。若压缩不显著，也如实报告，不能换数据。

### 6.3 每事件的事务式同步

建议增加：

```cpp
void sync_scores(ObservationHistory const&, ScoreIndex const&,
                 ScoreState&, WorkBudget&);
std::vector<DirectionId> select_directions_cached(
    ScoreState const&, uint64_t event, WorkBudget&);
```

首版采用**每个有资格运行的事件入口扫描一次原节点**，与缓存的 covered 快照比较，不要求改动原生观察或在 ledger.commit 内偷偷做评分：

1. 在事件 20 ms 窗口内读当前输出历史，计算每节点 `covered = seen0 & seen1 & mask`。
2. 按节点计数变化，汇总每组权重差。对有效单调历史，权重只能下降；异常变化不能继续做无符号减法。
3. 对有变化的组，只按组签名更新各方向一次。没有变化的组不更新。
4. 原子发布新的快照、组权重、方向分数及 history version，再排序最多 256 项。
5. 第一个可改进事件必须支付首模型已产生覆盖的同步成本；不能在未计费的首模型提交阶段预热。
6. L2 使用实际交付历史；L1 和宽预算探针使用原生前缀历史。history 身份包括模式和会话，不能用相同数字 version 跨历史复用。
7. 取消时，采用 scratch 后 swap 或明确的 invalidate + 下次完整重建。不能对同一 delta 重复扣分，也不能继续用半更新排名。
8. 未能完成同步就取消本事件；不能使用 stale 分数选方向。下一事件继续同步所花成本仍计入下一事件，所有已失败工作保留。
9. `try_refine()` 当前是 const；可以将 ScoreState 放在外部 session 中并显式传入，或清楚调整只属于改进器的状态。不要用全局 mutable 缓存或写入原生 RNG/map。

在正常历史下，这将旧的逐方向全 affected 扫描变为一次节点扫描、变化组传播及小排序。仍需测量第一事件和后续事件，不能只报温态命中时间。方向评分状态只依赖覆盖历史；数值缓存依赖当前原生赋值，两者身份不能混淆。

### 6.4 等价检查

固定工作量下，每次同步后用原 `select_directions()` 重算分数和选择列表。至少覆盖：

1. 空历史、首模型历史、连续多个实际交付、多个原生回退。
2. 只增加单侧观察但 covered 不变。
3. 输出去重导致历史不变。
4. 完整历史替换、session 重建、公式身份不同。
5. 在扫描节点、更新组、发布前各阶段取消，再恢复。
6. 分数平局、池不足 8/16、event 轮转与大 event。
7. 一组包含大量节点以及每节点签名各异的两种极端。

排序相同不足以验证分数，必须逐方向比较整数分数。

## 7. 原预算内交付：计时、保留已完成候选和事务

### 7.1 当前入口的风险要先修正

基点 worker 的事件顺序是 `try_refine → refinement_json/emit → 计时 → 提交历史 → 写 event_cost`。它记录了尾部超支，但不能仅凭 `r.chosen` 非空就声称候选在 20 ms 内完成交付。

新外壳必须明确区分：

1. `first_complete_candidate`：合法性、官方观察和评分均已完成。
2. `first_preserved_covered_gain`：全部保护和去重通过、covered 严格增加，候选及所需观察已经安全保存。
3. `delivery_ready`：交付所需数据、规定日志和搜索临时对象清理完成。
4. `actually_delivered`：最终预算检查通过，实际输出历史提交该候选。
5. `event_total`：本事件全部可选工作及日志尾部，包含失败和回退。

前两个时间不是交付时间，单个 candidate_wall 也不包含排在它之前的失败工作。

### 7.2 统一收尾余量

四种正式配置共用以下固定策略，不扫描参数：

1. 预处理总上限仍为 100 ms，算法工作软截止为从预处理入口起 CPU/墙钟各 96 ms，余下时间供元数据和收尾使用。
2. 事件总上限仍为 20 ms，搜索软截止为从事件入口起 CPU/墙钟各 18 ms，余下时间供交付收尾使用。
3. FirstCovered 在找到第一个合格严格 covered 候选时立即收尾，不等到 18 ms。
4. 软截止不是额外时间：同步评分、保护构造、排序、数值缓存初始化等全部从同一事件入口计时。不能在进入某阶段时重新开始一个完整 18 ms 预算。
5. 余量不保证尾部一定完成；超支就记失败，不能继续放宽。记录 96/18 ms 是本轮统一收尾策略，100/20 ms 才是最终验收上限。
6. 对进程退出、异常和超时保存已发生工作及候选，但不使用截止后才完成的结果。

实现绝对 deadline 或共享起始时刻的 budget view，避免嵌套 WorkBudget 意外重置时钟。

### 7.3 最小事务契约

建议新增：

```cpp
struct CandidateMilestones {
    std::optional<Elapsed> first_complete;
    std::optional<Elapsed> first_preserved_covered;
    std::optional<Elapsed> delivery_ready;
};
struct DeliveryDecision {
    bool proposed_replacement;
    bool actually_delivered;
    bool within_preprocess_cap;
    bool within_event_cap;
    std::string rejection;
};
class BudgetedDeliveryTransaction; // 只涉及输出，不能写原生状态
```

要求：

1. 搜索使用固定输出快照；产生候选期间 output history 不变。
2. 保存合格候选所需的 assignment、完整实际观察、gain、方向和参数全部在时限内完成，不能只保存一个悬空引用或参数，之后再完成验证。
3. 优先通过 move 转移已经完成的对象；不要在找到合格候选后重新执行一次不计时验证。原有独立验证与官方观察仍必须实际执行。
4. 先暂存拟交付数据和证据，完成规定序列化、写出和清理，再决定是否接受。暂存记录明确标记 `proposed`，不能提前作为最终输出。
5. 收尾超限时实际交付原生模型；下一事件的 L2 历史必须来自这个实际决定。不得先用候选更新历史，再在报告里把它改叫超时。
6. 若外层观察到决策后的不可中断尾部使预算超支，离线事务必须在处理下一模型前撤销该次替代，并按原生交付重建对应输出账本/评分状态；明确记录 `delivery_tail_overrun`。不得继续沿超时替代产生的历史计算。
7. 不要求在普通操作系统上证明硬实时。只能依据实际 CPU/墙钟测量判断是否达标，调度噪声导致超限也保留。
8. 对“最后一条成本记录不能测量自己的写出”使用已有父进程/外层计量补充完整进程成本，单列无法归属的测量尾部；不能将其记为 0。若剩余不确定成本使某个临界事件是否合格无法确认，状态为 `budget_eligibility_unknown`，不计入成功数。
9. 任何为交付或排序新增的复制、索引、回滚、同步都属于可选成本。原有必需原生观察/基本 ledger 提交可以保持既有分类，但不得借此隐藏新增成本。
10. 会话的全部可选支出，包括超支尾部，继续扣减 6 s 累计额度。达到累计额度后不再尝试改进。

保留旧原始日志信息：方向、目标、参数、完整赋值、实际观察、缺失集合和得分。不要把完整候选审计数据移到截止之后再宣称原预算内交付。本轮不通过删日志、缩小观察集合或改变日志配置获得优势。

### 7.4 增加的时间与工作字段

每事件至少记录：

```text
native_event_id, source_assignment_sha, output_history_identity/version
configuration, stop_policy, first_output_identity
preprocess_eligible, preprocess_total_cpu/wall
event_cpu_cap, event_wall_cap, search_soft_cpu/wall
first_complete_cpu/wall
first_preserved_covered_cpu/wall
first_candidate_direction/parameter
first_gain_direction/parameter
delivery_ready_cpu/wall, event_total_cpu/wall
proposed_replacement, actually_delivered, budget_eligible
delivery_rejection, cancellation_stage, candidate_in_progress
rank_sync_nodes, changed_covered_bits, dirty_groups, score_updates
original_affected_entries, compressed_group_direction_entries
completed_domains, proposed_parameters, completed_evaluations
protected_missing, native_gain, delivered_gain
event_tail_cpu/wall, overrun_cpu/wall
historical_cpu_credit_proven=false
```

首次时间是从本事件可选工作入口累计计时，不是阶段内部耗时；未到达则为 null，不是 0。CPU 与墙钟分别检查，两者都达标才通过。

## 8. real：解释完整一维域为何是 {0}

### 8.1 固定诊断对象

1. 仍用 real 原生位置 2/3/4/5，保持原生前缀，不使用 convert 的候选。
2. 从上轮归档取各位置已选的 16 条原方向及顺序，共 64 个 anchor—direction 请求。按完整方向系数、公式与 anchor SHA 核对身份，不仅核对 ID。
3. 已知每个缓存配置的 64 个域有 62 个 `{0}`、2 个含非零点；本轮不假定所有 64 个都阻塞。
4. 使用基点 ValueCache 的数学实现加独立诊断钩子；任务 A 的新索引和评分不决定本诊断选择。没有改变方向池或排序。
5. real 诊断工件不参与正式 L2，不更新任何原生/输出历史。其结果不能被任务 A 用来绕过某条方向。

### 8.2 诊断不等于查看活动约束

需要区分：

1. 强制等式应已满足 `A*d=0`，是否真的全数成立。
2. 某个分支内等式可能在当前 anchor 处成立并沿方向钉住 t=0，但它未必是全局强制等式。
3. 紧不等式可能分别阻止正、负移动。
4. 不紧的不等式也可能通过整数 floor/ceil 使允许的整数参数只剩 0。
5. 当前分支无路可走，不代表其他 OR 分支不能在较远 t 处成立。
6. 保护筛选发生在合法候选之后；原式完整域已经为 `{0}` 时不能把阻塞归因于保护。

因此不能只检查当前活动分支，也不能用 t=±1 均不合法来证明整条线上没有其他非零整数。

### 8.3 增加只读域来源记录

建议新增：

```cpp
struct AtomLineEvidence {
    NodeId node;
    Op comparison;
    Big constant, slope;     // 规范化比较的 constant + slope*t
    IntervalUnion integer_domain;
    // Eq/Distinct 的整除信息；Le/Lt 的 floor/ceil 及严格性转换。
};
struct BoolDomainEvidence {
    NodeId node;
    Op operation;
    std::vector<NodeId> children;
    IntervalUnion integer_domain;
    bool complete;
};
class DomainEvidenceSink;
BlockingReport explain_singleton_zero(...);
```

在 `LineDomain::truth()` 完成节点域后，通过可选钩子记录，不改变原式域运算：

1. 保留原 atom ID、原运算、参与比较的孩子、沿线常数/斜率和规范化结果。
2. 多元比较若出现，记录各子比较及交集；不虚构新的原观察节点。
3. 对不变子公式记录“语法影响为空 + anchor 的精确真值”，独立审计仍核验其不变性。
4. 对 AND/OR/NOT/ITE 等按实际支持范围记录域的交、并、补及来源。unsupported 仍是 unsupported，不为诊断扩大生产支持范围。
5. 对 Bool 节点共享 DAG 保留引用，不能复制成指数大小的解释树。
6. 记录原公式根域、额外真实硬条件的域及最终交集。若本批没有额外条件，明确写 none。
7. 完成根域必须包含 0。违反则是正确性错误，不是算法没有候选。
8. 根域 `{0}` 的证明是**完整整数域推导**。阻塞 atom 列表只是解释摘要，不能冒充最小 UNSAT core。

### 8.4 为人阅读的阻塞摘要

每个完成的 singleton-zero 方向输出：

1. anchor、方向支持变量、完整系数及强制等式验证结果。
2. 导致正方向上界和负方向下界收缩的 atom ID、常数、斜率、精确 floor/ceil。
3. 对相关 atom，标明从根只经过必需 AND 到达，还是位于 OR/NOT/ITE 等条件结构内。不能把一个分支 atom 当作全局必需约束。
4. 是否出现非零斜率的局部分支等式；该分支之外的域为何也不能提供非零点。
5. 是否存在“anchor 处有正 slack，但整数舍入后的边界是 0”的 atom。称为“整数取整参与阻塞”，除非给出充分证明，不称其唯一原因。
6. 完整布尔组合是否排除了所有非零整数；若来源记录不完整，解释状态仍为 incomplete。
7. 可另给 t=+1、-1 的失败点作为直观例子，但不能以这两个测试点替代完整域证明。
8. 对非零域，记录最近非零点、是否合法，以及后续保护/增益结果；不能混入 singleton-zero 统计。

不要求计算最小约束核，也不调用求解器提取核心。对无法压缩成少量 atom 的情况，给完整共享推导引用和“多个分支共同阻塞”，不强行归因于一对约束。

### 8.5 独立验证

新增 Python 检查器，不调用生产 C++ LineDomain：

1. 从原 AST、完整 anchor 和方向独立生成相关仿射常数/斜率；不能直接信任记录的系数。
2. 使用任意精度整数实现规范化区间集合，重算原子域以及 Bool 运算。
3. 检查所有完成的根域及来源证书。不能以有限 t 抽样代替区间等价证明。
4. 独立核验全部强制等式，根域含 0，以及“singleton_zero / has_nonzero / unsupported / incomplete”的分类。
5. 非仿射但语法不变的子项使用独立精确求值；数值正确性与官方 Reach 继续分开。
6. 记录审计器支持范围。证书含尚未支持构造时填 `unverified`，不能把生产实现自己复算称为独立验证。

将原始完整域和完整证书分别计数，避免“根域完成但解释未完成”被写成全部完成。

## 9. real：有限组合方向检验，不能进入生产

### 9.1 本步骤回答的问题

如果两个已选方向各自只有参数 0 合法，组合后能否得到一个非零合法点？这有助于判断当前单方向集合是否缺少协调移动。

例如约束 `x>=0, y>=0, x<=y, y<=2*x`，anchor 为 `(0,0)`：沿 `(1,0)` 和 `(0,1)` 都只能取 0；沿 `(1,1)` 则能移动。这只是必须通过的合成测试，不是对真实 real 的预先结论。

### 9.2 预登记组合列表

从上轮该位置已完成且域为 `{0}` 的原方向中选对，执行前把列表写入 manifest：

1. 按 `(min_direction_id, max_direction_id)` 排序，同等式分量取前 8 对、不同等式分量取前 8 对。
2. 某类不足 8 对则不补到另一类。跨分量对必须保留，因为不等式可以连接不同等式分量。
3. 每对只尝试 `d_i+d_j` 与 `d_i-d_j`，按此顺序。每 anchor 最多 32 条请求，四个 anchor 最多 128 条。
4. 每条组合去零、按全体系数 gcd 及首非零符号归一化，使用既有精确整数限制。零向量和重复方向记录后跳过，不补选。
5. 与已有原池方向重合时记录 `already_in_pool`；其结果不能充当“新增组合首次解除阻塞”的证据。
6. 不尝试其他权重、第三条方向、随机组合、分支求解、变量释放或提高分量上限。
7. 组合列表由旧证据确定；本轮某原方向若未及时复核完成，跳过依赖它的因果结论，不根据新截止情况换一组容易完成的方向。

对组合归一化后，再独立验证所有强制等式。线性组合加归一化能保持齐次等式，但仍必须检查实现没有系数和身份错误。

### 9.3 每条组合做什么

1. 使用完整原式与硬条件计算一维整数域，保持区间、运算和整数限制。
2. 若域含非零点，确定性选择绝对值最小的非零整数；平局取数值更小者。只取一个点，不调用覆盖目标命中搜索。
3. 构造完整赋值，独立验证原式及硬条件，计算官方观察、完整保护缺失和 marginal gain。
4. 依次记录 `nonzero_domain_found → legal_witness_verified → preserved → covered_gain`。域有非零点但后续验证超时，只能停在前一层。
5. 候选不注入输出、历史、方向池、排序或原生搜索。所有诊断耗时单列，不属于 20 ms 正式轨道。
6. 两条原方向的域已独立证明为 `{0}`，而组合点合法，才称为“组合解除该处单方向阻塞”。
7. 组合可动但保护失败，说明可行性阻塞有所解除，保护问题仍在；不能写成“改进成功”。
8. 全部组合失败只否定这个固定有限集合。不能推出无组合方向、无其他模型或保护不可满足。

### 9.4 诊断资源边界

每个 real anchor 一个冷 worker，共 4 个：

| 项目 | 上限 |
|---|---:|
| 诊断预处理 CPU / 墙钟 | 各 2 s |
| 16 个原方向及证书阶段合计 CPU / 墙钟 | 各 8 s |
| 每个原方向（含解释与记录） | 各 500 ms |
| 最多 32 条组合请求阶段合计 CPU / 墙钟 | 各 8 s |
| 每条组合（含验证、观察与记录） | 各 250 ms |
| 单 worker 父进程墙钟截止 | 25 s |
| 单 worker 证书内存增量 | 64 MiB |

解析、前缀构造、诊断预处理、方向、组合及尾部均列出，父进程上限包含所有阶段。子阶段剩余额度不得大于其阶段与 worker 剩余额度。提前耗尽就停止并保留未开始项，不提高预算或重试。

大证书按 DAG 共享，每方向处理后可写出并释放。内存达到固定上限记 `evidence_limit`，不可删掉 OR 分支后声称证书完整。

## 10. 正确性、预算及状态隔离验证

先通过 Release 和 ASan/UBSan，再进入正式离线矩阵。复用上轮已存在的算术、模命中、区间、方向和官方观察测试，不以新增大量镜像实现测试代替关键机制检查。

本轮必须新增或扩展以下测试：

1. 稀疏验证与全行点积逐方向一致；不同分量、空行、零系数、重复入射、取消和 epoch 回绕。
2. 批量位集影响与旧完整变量依赖一致；共享 DAG、深链、x-x、未选分支、Bool、多个变量出现点和空池。
3. V0/V1/V2/V3 在无时间截断、相同工作上限、关闭 FirstCovered 时，等式/分量/方向/affected/分数/顺序/目标/区间/参数/完整赋值/观察/保护缺失/最终选择逐项相同。
4. FirstCovered 对四配置均停止在原候选序列的同一个首个合格严格 covered 候选；高分但丢观察、仅单侧增益、重复输出均不能触发。
5. 评分增量及取消恢复见第 6.4 节；L1/L2 历史不串用。
6. 预算在构造方向、评分同步、公式域、完整验证、官方观察、保存候选、序列化、清理时取消。只能交付已经完成且最终合格的对象。
7. 用可控时钟/注入钩子验证：搜索 17 ms 后尾部 4 ms 必须回退；候选在 19 ms 才完成不能通过 18 ms 软截止后继续计算；超时回退后的下一事件历史与实际原生输出一致。合成时钟测试不能作为真实性能证据。
8. real 合成阻塞例：两个单方向阻塞而组合可动；两个相反紧界；分支内等式；OR 在 t=2 重新可行，不能只因 t=±1 失败判为 `{0}`。
9. 整数取整例：`-1<=x<=1`、y 自由，anchor `(0,0)`、方向 `(2,1)`。连续参数可以小幅移动，整数参数只有 0。不能只检查 slack=0 的原子。
10. 三变量用双向不等式强制 `x=y=z>=0`，单位方向及两两组合均阻塞，但三向协调可动；用于检查有限二方向负结果不被解释为全局不可行。
11. real 证书的 atom 系数、布尔来源、区间端点或分支引用被故意修改时，独立检查器必须拒绝。
12. 原生隔离测试必须实际发生替代，比较完整 map、m_ls、RNG、参考、反馈、路由与原生计数。关闭模式维持基点行为；不能用全回退轨迹证明隔离。
13. 已知 convert +43 完整赋值作为只读回归 fixture，独立验证合法性、保护和 gain。生产选择器不得读取 fixture、指定方向 186、参数 3 或第 3 个位置。

算法函数中禁止按实例名、公式 SHA、已知方向 ID、原生位置或已知结果选择快路径。实验驱动器当然可以按 manifest 定位输入；该信息不得进入候选策略。

## 11. 固定实验数量、顺序与分析

### 11.1 先冻结，再运行

1. 创建独立分支，记录基点、输入、归档及工具链 SHA。
2. 实现共同外壳和 V0–V3，以及独立 real 诊断；仅使用合成测试及只读旧证据调试。
3. 冻结计划：全部配置、FirstCovered、96/18 ms 软截止、矩阵顺序、real 原方向和组合列表、预算和停止条件。
4. 正确性、SAN 与隔离通过后冻结新源码、生成文件、动态库及二进制。
5. 运行固定探针、22 条正式序列和 4 个 real 诊断 worker。
6. 独立审计，报告所有结果及缺项，归档、提交、推送。

新真实探针开始后，不能根据性能结果再增修复配置或改软截止；只允许修复证实的正确性错误。修复须保留废止尝试并重新冻结，不能按最好一次挑结果。性能失败不构成重跑理由。

### 11.2 convert 固定宽预算探针

V0、V1、V2、V3 各一个冷 worker，共 4 个；每个仅处理原生前缀位置 1–5，其中位置 2/3/4/5 尝试改进。

1. 预处理各最多 2 s、事件各最多 500 ms；父进程每 worker 墙钟 6 s。
2. 使用 AuditAll：关闭 FirstCovered，保持原有限搜索工作量与候选序列。该模式只供成本定位和共同完成部分的等价核对。
3. 全部使用原生前缀，不注入候选。全部参数、方向和目标限制仍保持。
4. 原 +43 见证用于核对，不作为“必须命中”的选择规则。
5. 列出每阶段完成工作、首完整候选和首保护增益时间。旧配置截断时报告删失，不能以 500 ms 充当完整工作耗时计算加速倍数。
6. 这些结果不进入正式预算收益表，也不能提前为正式冷序列建立索引或填充缓存。

### 11.3 正式离线矩阵：22 条序列

| 轨道 | 配置与次数 | 序列数 | 重放源事件数 |
|---|---|---:|---:|
| convert 主 L2 | V0/V1/V2/V3 × 3 次 | 12 | 324 |
| convert 原生前缀 L1 | V0/V3 × 3 次 | 6 | 162 |
| real、random 控制 L2 | 两实例 × V0/V3 × 1 次 | 4 | 32 |
| 合计 |  | 22 | 518 |

每条使用完整冻结源序列。518 是重放次数，独立源模型仍只有 43 个。探针及 real 诊断另列，不混入 518。

1. L2：只将实际预算合格的交付写入输出历史；原生序列不变。
2. L1：候选只是假设结果，后续历史始终使用原生前缀。可以统计“预算内可交付候选”，不能把它当真实连续交付曲线。
3. 首模型仍原样交付，不能凭空多一次改进机会。首模型的观察及可选日志成本都记录。
4. 每条冷启动：空模型值缓存、重新建方向池/影响/评分索引，不能沿用上个配置、探针或重复的内存状态。
5. 主三轮配置顺序固定为：
   - r1：V0 → V1 → V2 → V3；
   - r2：V2 → V3 → V0 → V1；
   - r3：V3 → V0 → V1 → V2。
6. L1 两配置顺序按 r1/r2/r3 为 V0/V3、V3/V0、V0/V3。
7. 计时单进程顺序执行，固定同一物理核对应线程；记录 sibling、CPU、内存、编译器及系统。计时期间不并行编译、归档、上传或 real 诊断。
8. 不宣称宿主完全独占。保存调度异常及原始墙钟，不因其不利自动重跑。
9. random 的方向池应保持为空；若新实现产生方向，先查语义或冻结输入是否改变。real 控制若意外产生正结果照实报告，但不能用诊断方向回填解释。

### 11.4 必须输出的分析表

1. 四配置冷预处理全部子阶段、总成本、是否在 100 ms 内；稀疏验证及批量影响的工作量。
2. 每个原生位置：排名同步成本、首完整候选、首保护增益、交付完成时间、实际输出、回退原因。
3. 三次重复逐次列出，不能只给最好值；完成耗时报告中位数和范围，超时另列。
4. L1 与 L2 的区别：是否因前面实际交付改变历史而改变后续机会。不能要求 L2 第 3 个位置仍精确 +43。
5. 同位置的候选保护、实际 gain、重复检查和预算余量。
6. 全部前缀及终点 covered；“本次替代增加 covered”与“终点仍保留额外 covered”分开。原生后续可能补齐同一些 bit。
7. 全序列可选/必需成本、日志尾部、全部进程 CPU/墙钟和 RSS；缺失信用继续标 false。
8. real 64 原方向的完成/阻塞/非零/不完整数，原因摘要、证书核验情况；至多 128 组合请求的完整漏斗。
9. 新代码是否在 frozen +43 上保留正确性；若正式预算未找到，不将 fixture 本身算成发现。

### 11.5 新运行总表

| 阶段 | 上限 | 新原生采样 | 真实 solver check |
|---|---:|---:|---:|
| 合成正确性/SAN/隔离 | 固定测试清单 | 0 | 0 |
| convert 宽预算探针 | 4 workers、16 个可改进位置 | 0 | 0 |
| 正式离线 | 22 序列、518 次源事件重放 | 0 | 0 |
| real 阻塞及组合诊断 | 4 workers、64 原方向、最多 128 组合请求 | 0 | 0 |
| 独立证书与输出审计 | 全部完成工件 | 0 | 0 |

不重跑上一轮 24 个 oracle；没有新 oracle 编码修复，也不修 random 的方向供给。

## 12. 验收、停止与交付

### 12.1 任务 A 的分层判定

1. **A0 正确性通过**：等价成本修复及显式停止规则符合契约，原生隔离与独立观察审计通过。
2. **A1 候选可达**：至少一次正式事件完成完整合法候选。若保护或 covered 不过，仍未完成本轮主要目标。
3. **A2 一次预算内严格增益交付**：至少一次 convert L2 替代同时满足冷预处理、事件及累计预算；保护缺失为零，covered 严格增加，候选进入实际输出。偶发一次单列，不称稳定改进。
4. **A3 可重复的局部交付**：V3 三次 L2 存在至少一个共同原生位置，三次均达 A2，且所有输出前缀保留对应全部原生观察。三个候选可以不同，但逐次证据必须完整。
5. **A4 序列终点增益**：三次 L2 最终 covered 均严格高于原生；即使 A3 通过而 A4 不通过，也不能隐去终点追平。
6. 整体算法仍不自动 Go；本轮没有第二实例稳定收益、历史 CPU 信用和在线等时间数据。

“相对 V0 更快”不足以达到 A2；“找到 +43 但超预算”也不足。即使 A2/A3 通过，也不得将单一已知实例的开发结果称为泛化验证。

### 12.2 任务 B 的分层判定

1. **B0**：重新确认已完成的根域，未获得完整解释。
2. **B1**：对完成且阻塞的方向给出独立核验的完整整数域证书与正确条件作用域，定位紧界、取整、分支等式或布尔组合的实际作用。
3. **B2**：存在两个原方向都确证阻塞而组合方向具有完整合法非零见证，说明该处需要协调移动。
4. **B3**：诊断见证还通过完整观察保护并严格增加 covered。仍只属于宽预算诊断，不进入生产成绩。
5. 有证书的局部负结果同样完成诊断任务；未完成证书或有限组合失败不能推出全局无解。

### 12.3 出现什么结果就停止在哪

| 结果 | 本轮结论与停止位置 |
|---|---|
| convert 仍过不了冷预处理 | 记录新的主成本；不增加第五码配置、不提高 100 ms |
| 冷预处理合格，排序仍超时 | 记录首次同步与后续同步成本；不隐藏初始化或改排名 |
| 排序完成，域/参数阶段超时 | 定位完整候选前的剩余工作；不改方向或降低保护 |
| 候选完成，保护拒绝或无 covered 增益 | 报告实际缺失与得分；不再笼统归因于预处理 |
| 候选有收益但交付尾部超时 | 记 delivery_overrun，实际回退；不算 A2 |
| 只有宽预算正例 | 保留机会存在结论；原预算目标仍 No-Go |
| real 原方向阻塞，组合成功 | 给下一轮协调方向研究的具体证据，不将其并入 convert 代码 |
| real 原方向或证书未完成 | 报告 incomplete，不能写成 `{0}` |
| correctness/隔离/观察包含失败 | 停止真实评分，保留现场，修复并重新冻结受影响尝试 |

不追求无限修补直到取得正值。执行完既定修复和矩阵后，无论正负，交付完整报告。后续设计应由本轮实际瓶颈决定。

### 12.4 建议工件

```text
docs/refinement_budget_delivery/
    execution_guide.zh.md
    implementation.zh.md
    results.zh.md
    real_blocking.zh.md
include/refinement/
    direction_score.hpp
    line_blocking.hpp
scripts/refinement_budget_delivery/
    freeze.py
    build.py
    run_probes.py
    run_offline.py
    diagnose_real.py
    audit.py
    check_blocking.py
    report.py
configs/refinement_budget_delivery.json
manifests/refinement_budget_delivery/
results/refinement_budget_delivery/
    correctness/
    probes/
    offline/
    real_diagnosis/
    analysis/
archives/refinement_budget_delivery/
```

保留旧入口，不复制无关历史工程。按现有 build 方式同步模板和真正生成头文件，核对二进制确实依赖新文件。

冻结清单包括：源/生成文件/二进制/动态库/输入/指标 SHA，配置和预算，所有尝试 ID，原生位置，real 原方向与组合清单，冷状态、CPU 绑定及退出状态。执行器拒绝覆盖已开始尝试。

### 12.5 中文报告必须直接回答

1. 稀疏验证省掉了多少完整数组构造和行扫描？数学义务是否仍覆盖全部等式？
2. 批量传播是否得到完全相同的 affected？是否真的比 ValueCache 和原 Shared 的相应路径便宜？
3. 分组是否有效压缩重复影响关系？第一次评分同步是否仍是瓶颈？
4. 首个真实增益候选从事件入口算起花了多少 CPU/墙钟？前面失败尝试、日志及清理是否全计入？
5. 有没有冷预处理合格、完整保护通过、严格 covered 增益且实际预算内交付的候选？三个重复逐次是什么？
6. FirstCovered 的停止行为与等价成本修复分别是什么贡献？不能混称“算法完全未变”。
7. 前缀增加是否保留到最终序列？L1 的机会和 L2 实际历史有何差别？
8. real 的完整域为何只能为 0？给原约束节点、边界算术与布尔作用域，不仅给原因标签。
9. 二方向组合是否解除阻塞？合法、保护、覆盖分别到哪一层？失败结论限制在什么范围？
10. 哪些成本或记录仍未知？是否有不能确认预算资格的临界结果？
11. 本轮达到 A/B 哪些等级；哪些研究目标仍为 No-Go？
12. 是否存在任何真实新采样、oracle、在线实验或未登记重试？如存在，必须列为偏离，不能混入正式结果。

独立审计必须覆盖所有实际交付、所有完成候选的保护/得分、全部输出前缀和所有完成的诊断证书。区分“审计调用次数”“不同公式—赋值对象数”和“43 个源模型”，不再把缓存未命中次数命名成 unique model 数。

最后正常提交并推送独立分支，用 `git ls-remote` 核对完整远端 SHA。保留所有失败、超时、拒绝、超支和缺项，提供可恢复归档及成员 SHA。工作区应干净；不得上传凭据、虚拟环境、构建树或无关第三方二进制。上传失败如实报告，保留本地提交。

## 13. 固定源码参考

1. [本轮出发报告](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/docs/refinement_cost_repair/results.zh.md)。
2. [方向生成、全行验证与排序](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/directions.hpp)。
3. [仿射编译与沿线数值](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/affine_ir.hpp)。
4. [父边索引与逐方向 affected](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/dependency_index.hpp)。
5. [完整布尔公式一维域](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/line_domain.hpp)。
6. [候选轮转、验证、保护和选择](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/refiner.hpp)。
7. [预算与信用](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/budget.hpp)。
8. [现有离线计费边界](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/src/refinement/cost_repair_worker.cpp)。
9. [官方观察实现](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/include/refinement/observations.hpp)。
10. [原始证据恢复](https://github.com/ChenKaichen-SCUT/guided_sampler/blob/2dde70ab203009afdb07e4337eb3cdd637906704/archives/refinement_cost_repair/RESTORE.md)。

本轮完成的理想结果是：一个不依赖实例特判、能在原预算内实际交付增益的 convert 流程，以及一份能够解释 real 单方向阻塞、判断有限协调移动是否有用的独立证据。任一部分不成立，都保留具体失败位置，不用另一部分的正结果替代它。


