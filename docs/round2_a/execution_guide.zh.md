# Guided Sampler 第二轮：A-only 接入修复、完整诊断、成本控制与实验执行指引

## 0. 本轮任务、基点与不可变边界

请实际完成代码修改、构建、正确性测试、受控机制诊断、正式实验、独立审计、中文总结和 GitHub 推送，不要只返回计划。

本轮从以下冻结版本新建分支，例如 `round2-a-routing-repair`：

```text
项目：ChenKaichen-SCUT/guided_sampler
第一轮冻结提交：fc19bd22609295ed405e1ac96bf35d695c42832a
HighDiv 上游：f2c6e1756b13281d96cbf90a8bd940129e56cce4
目标远端：https://github.com/ChenKaichen-SCUT/guided_sampler
```

原 `HighDiv/`、8 个输入、第一轮结果和已执行的 16 次 HighDiv 基线全部保持不变。不要拉取上游最新代码代替上述版本，不要改写原始报告。新构建、日志和结果使用独立目录。

### 0.1 本轮唯一正式算法

**只运行修复后的 A-only。** A 的严格定义是：在 HighDiv 原生求解过程已经选中一个尚未赋值的、普通布尔/理论原子后，根据历史单侧 bit 缺口调整这一次决策的相位偏好。

A 不选择新变量，不增加公式，不内部化新目标，不强制目标实现，不直接改整数值。普通传播、冲突分析、回溯、模型恢复和 CCSS 保持原实现。

本轮不实现或运行 B-only/A+B，不实现宏观整数域分析、不可达证明、目标 core 学习、MaxSMT、LIA 数值移动、额外求解修复器、完整模型阻塞、候选排序或新的混合调度。

### 0.2 本轮必须分别回答的问题

1. 上轮 A 为什么没有实际介入：目标窗口、静态匹配、表达式重写、内部绑定、已经赋值、原生队列未选择、决策窗口、额度、后端传递，分别损失多少机会？
2. `SMT_random`、`SMT_real` 的真实 tactic 叶子是什么，A 数据是否到达实际进行决策的内核？
3. 修复后的 A 是否真实改变了普通决策相位？同相位建议不能当作实际改动。
4. 改动是否最终命中原 AST 的缺失观察？命中与模型全部增益分别统计。
5. 新增的数据准备/绑定成本，与真正执行相位偏好后整个 check 的成本，如何区分？
6. 与冻结完整 HighDiv 和第一轮 A-only 相比，固定时间、固定 100 模型结果分别如何？

### 0.3 正式矩阵

```text
8 个既有实例 × 2 个独立预算模式 × 1 个修复后 A-only × seed=0 = 16 次正式会话
```

- `time900`：900 秒，不设样本数量上限。
- `n100_t900`：100 个不同、合法、及时正式模型，最多 900 秒；不足时保留实际数量。
- 两种模式独立进程；不能用前者的前 100 个冒充后者。
- Linux，8 核/16 逻辑线程；仍使用冻结的逻辑 CPU 槽安排，16 路并行，不改成 8 路。
- 不重跑 HighDiv，不重跑旧 A/B/AB 正式配置，不追加 seed。
- 正确性通过后完成这 16 项，不按短跑覆盖好坏筛选实例或改参数。
- 允许以下指引规定的有限正确性/机制微测试；它们不是新的 HighDiv 基线，不替代正式矩阵。

---

## 1. “软指引”具体是什么，当前在哪里

### 1.1 上轮已有实现

`src/z3_broker.inc::context::coverage_decide()` 的 A 分支执行的核心操作是：

```cpp
is_pos = pos.size() > neg.size();
```

`patches/20_z3_guidance.patch` 将它放在 `smt::context::decide()` 的正常决策处理过程中。随后仍由原来的 literal 符号处理、`assign(..., decision=true)`、传播和回溯运行。

这就是 **A 的软相位指引**：只改变“这次先尝试真还是假”，不是把目标加入必须成立的约束。没有单独名为 `soft_solver()` 的优化器，不保证找到最多覆盖的模型。

上轮 A-only 的 `a_used=0`，意味着这段分支在正式实例中没有实际给出建议；不是有一套隐藏的软引导在别处发挥了效果。

注意旧函数最后返回 `var != native`，表示“有没有换决策变量”，不是“有没有改相位”。A不换变量，因此即使通过引用改了 `is_pos`，也会返回false。不能仅看这个返回值就误判A没有执行；新接口必须消除这种混合含义。

B 也是可放弃的普通决策，但它先添加了目标表达式的内部表示；其内部定义和历史搜索影响与 A 不同。本轮不运行 B。

### 1.2 本轮给 A 明确命名

新增或重命名为以下接口之一，名称可按工程组织调整，但文档必须一一对应：

```cpp
AAdvice evaluate_A_phase_hint(NativeDecisionView const& native);
bool apply_A_phase_hint(bool_var native_var, bool native_phase,
                        bool& effective_phase);
```

`native_var` 不允许通过引用被改写。返回值只表示是否产生建议/发生改相位，不能沿用“是否更换变量”的混合含义。

至少区分：

```text
eligible：满足安全/普通决策条件
suggested：得出了不平分的相位建议
same_as_native：建议与原生相同
overridden：建议与原生不同，实际改了相位
retained：最终该原子仍取被建议的值
target_hit：最终原 AST 确实访问并命中关联缺失 bit
```

不得把 suggested、same_as_native、retained、target_hit、性能收益混为一谈。

---

## 2. 已核对的代码事实与本轮修复位置

以下是已核对的冻结源码事实；后续新增类和接口是实施建议，不是现成 API。

| 文件/函数 | 上轮行为 | 本轮动作 |
|---|---|---|
| `include/observation.hpp::OriginalAst::select_window()` | 从全部单侧位轮转选最多 8 个，之后才找 A 映射 | 保留为旧版诊断函数；正式 A 改为按实际原生原子反查当前缺口，不再受全局 8 位窗口阻断 |
| `AtomHintCatalog` | 原布尔节点、显式整数项=常量；还会创建交换等号两侧的 AST | 保留直接语义，不做域推导；改用宿主数据中的规范化键，避免为了匹配创建新 Z3 AST |
| `GuidanceBridge::prepare()` | A/B 共用目录、编码字段、最多 8 位 API、逐目标 JSON | 拆出 A 专用数据通路；纯元数据注册、无 B 编码、分阶段计时、分层日志 |
| `combined_solver::set_coverage()` | 仅转发给 `m_solver2` | A-only 元数据可传给 solver1 和 solver2，但不得改变原路由条件 |
| `tactic2solver::check_sat_core2()` | 构造 goal，调用 tactic 流水线 | 在 goal 上附加非逻辑元数据，跟随真实流水线到达实际叶子 |
| `smt_tactic::operator()` / `scoped_init_ctx` | 创建临时 `smt::kernel`，常走 `setup_and_check()` | 安全绑定 A 数据；临时上下文退出清理；不能只修改持久 smt_solver |
| `context::setup_and_check()` | 另一条真实搜索入口；旧补丁没有 A 准备点 | 补齐 A 的搜索入口生命周期，且绕过 `m_ls_sampling` 的 CCSS 路径 |
| `context::check()` | 上轮在这里准备目标 | 改成只读 A 绑定；内层重搜索不得重置外层 check 的预算和干预次数 |
| `context::decide()` / `guess()` | 原生选择变量、生成相位，然后 broker 仲裁 | 保留原生选择与随机消费，只在安全的普通决策处覆写相位 |
| `src/coverage_guidance.h` | 共享 A/B 状态；单个 backend 字段 | 分离请求、每内核状态、跨后端查询统计，记录路由链而非只存最后一个编号 |
| `include/session.hpp::commit()` | 正式样本验证、去重、观察提交 | 保留正式交付口径；只将成功提交观察送入 A，及时性和有效性不变 |

重要事实：上游 `smt_tactic::operator()` 在无 assumptions 和无 user context 时调用 `m_ctx->setup_and_check()`。因此，只把数据从 solver1 转发到 tactic 还不够；仅在 `context::check()` 准备 A，依然会漏掉该路径。

另一个边界：上游 QF_LIA tactic 包含不同叶子和预处理步骤。日志中的“tactic”不是实际叶子名称，不能预先断言所有调用最终都是 `smt::context`。必须先追踪，不强制改路由使假设成立。

---

## 3. 先做只读失败分解，不先猜根因

新增 `scripts/diagnose_round1_A.py`，只读第一轮的 `mechanism_main.csv`、`mechanism_details.json`、归档中必要的 query/target 日志、源码与输入 manifest。不要重新运行第一轮采样。

输出 `results/round2_a/diagnosis_before/`：

- `old_a_funnel.csv`：按实例、预算模式分层；旧日志可确定的阶段计数。
- `old_route_summary.csv`：tactic/incremental/fallback、实际指导次数及 CDCL/CCSS 输出。
- `missing_evidence.json`：上轮无法从日志得知的原因，必须记 unknown/not_recorded，不补造。
- `root_cause_hypotheses.zh.md`：把已证事实与推测分开。

特别拆开：

```text
静态可匹配但 a_live=0
已经 a_live>0 但 a_used=0
后端不支持且仍构造/记录了大量指导对象
```

Bromberger/prime_cone 的已绑定但未使用，与 CAV/dillig/pb2010 的没有绑定，不能写成一个原因。不能用 `a_live` 反推出原子尚未赋值；不能用最终 SAT 反推出曾经尝试目标。

本轮不需要下载全部大归档才能阅读小 CSV；仅恢复诊断必需文件，并验证已有哈希。不得覆盖第一轮的恢复目录或修改证据。

---

## 4. 完全隔离 B：不只是命令行不选 B

### 4.1 新进程、新求解状态

所有第二轮测试和正式会话使用新的进程/solver。从来没有安装过 B 的状态开始，不能从第一轮带 B registry 的状态继续。

保留旧 B 源码用于历史重放，但本轮可执行入口只允许：

```text
正式：a_only_v2
测试：a_off_test / a_observe_test / a_apply_test
```

测试模式不得出现在正式计划中。正式 runner 拒绝 `b_only`、`a_plus_b`。

### 4.2 A 专用桥接对象

把 `GuidanceBridge` 拆成 `AGuidanceBridge`，或用强类型 variant 使 A 分支不构造下列对象：

```text
TargetEncoder
ReachBuilder（仅用于 B 编码的那个实现）
encoded 谓词缓存
B registry / B proxy set
B eligible 队列
```

A 的原 AST 观察器继续遵循短路访问；“不构造 Reach 公式”不等于改变观察语义。

### 4.3 零副作用不变量

A 注册和匹配不得调用：

```text
solver.add / assert_expr / assert_and_track
solver.push / pop（为了启用指导而调用）
internalize / ensure_internalized / mark_as_relevant
mk_bool_var / force_phase / set_true_first_flag
额外 check / optimize / MaxSMT
```

这里禁止的是**A 为指导额外调用**；Z3 原生求解自身的这些操作正常保留。

尤其不要为了让 A 原子“绑定成功”，把原始原子重新 internalize。这会重新产生 B 式副作用，也可能把已消元变量带回理论状态。

记录并断言：

```text
b_encoded = 0
b_internalized = 0
b_selected = 0
guidance_created_bool_vars = 0
guidance_added_assertions = 0
guidance_marked_relevant = 0
```

只读注册前后比较断言、原生内部变量数等快照。之后正常搜索本来就会创建变量，不能把整个 check 中的原生变量增长都归因于 A。

---

## 5. 修复 A 的关键结构：从“先选 8 个 bit 等待碰巧遇到”改为“实际原子反查缺口”

### 5.1 原因与边界

旧版把同一组 8 位窗口同时用于 A 和 B。A 不控制变量选择，先从全部单侧位选 8 个，再等待原生队列选中对应原子，很容易错开。

本轮保留 A 的既定定义：不改变原生变量选择；但改成：

```text
HighDiv 正常选出原子和相位
    → 对这个实际原子查找直接支持的原 AST 观察
    → 只对当前仍单侧的观察计分
    → 若一个相位更有支持，在配额内建议它
    → 否则保留原生相位
```

这是本轮明确的选择逻辑修复，不应伪装成完全不改变策略的日志补丁。报告要与路由修复、规范化匹配分别记录。

不自动把匹配范围扩展成整数域、联立方程推导或任意未覆盖位求解。

### 5.2 数据结构

建议新增：

```cpp
struct OriginalNodeId { uint32_t value; };
struct DemandId { uint32_t node; uint8_t bit; bool desired; };

struct CanonicalAtomKey;      // 与 AST 地址无关的精确结构/算术规范键
struct CanonicalLiteralKey {
    CanonicalAtomKey atom;
    bool negated;
};

struct DirectObservationRule {
    OriginalNodeId observed_node;
    // BooleanValue / IntegerTermEqualsConstant
    RuleKind kind;
    bool atom_truth;
    uint64_t known_one_mask;
    uint64_t known_zero_mask;
    MappingEvidence evidence;
};

class AAtomIndex {
public:
    void build_from_original_ast(OriginalAst const&, WorkBudget&);
    void update_after_commit(Evaluation const&, OriginalAst const&, WorkBudget&);
    HintView lookup(CanonicalAtomKey const&) const;
    std::shared_ptr<const AQuerySnapshot> snapshot(uint64_t coverage_version);
};
```

索引至少包含：

- `canonical_atom -> direct rules / aggregated current scores`；
- `original_node -> affected rule entries` 的反向索引；
- 已验证的正/负相位关系；
- 每个规则对应的原节点与 bit 掩码，方便最终命中核对。

不要把完整A索引塞进旧的 `nt<=8` 目标数组接口。新增A专用请求/快照接口，与B的8目标协议分离；静态索引只注册一次或按代际复用，每次check传递需求版本和必要增量。实际进入决策时仍只在64/4的限额内提供建议，索引中有更多可匹配目标不等于同时强制更多目标。

位缺口：

```cpp
want_one  = seen0 & ~seen1 & width_mask;
want_zero = seen1 & ~seen0 & width_mask;
```

一个等式 `t = c` 为真时，对原整数项 t 的支持数为：

```text
popcount(want_one & bits(c)) + popcount(want_zero & ~bits(c) & width_mask)
```

等式为假不能自动给相反位加分。只见单侧才计分，未见与双侧已见均不计分。原常量节点不作为引导目标；覆盖统计的原分母不变。

### 5.3 更新边界

只有正式提交模型后更新需求。CCSS 与 CDCL 的正式模型都更新同一份状态。

当前一个外层 CDCL check 期间，需求版本冻结；多个 tactic 子阶段读取同一版本。不要在回调内递归取 model 或重算整个原 AST。

使用 `Evaluation::changed` 更新受影响索引，不每个查询重新扫描全部节点和全部位。完整构建和增量更新成本必须计入会话与机制成本。

### 5.4 A 的候选集合与计数

正式 A 不再调用旧 `select_window()` 决定是否可指导。保留旧窗口算法作为离线诊断，可统计“这次原生原子具备可用缺口，但旧8位窗口是否会漏掉”；该额外诊断只在微测试执行，不进入正式热路径。

一次建议可能支持多个 bit。按 `DemandId` 去重，不能因为等号交换、NOT 表达式或共享节点重复加分。记录支持目标的掩码，不为每一位分配大量 JSON 对象。

保持第一轮 A-only 的以下上限，以避免把路由修复与增大干预强度混在一起：

```text
普通决策窗口：外层 CDCL check 的前64次
最多有效相位建议：4次（包括与原生同相位的建议，保持旧口径）
每个目标：同一外层 check 最多被主动建议一次
```

不要在内层重启、回溯、fallback 或新 tactic 子内核中重置配额。

两种相位支持数相同，保留 HighDiv 原生相位。不得引入新的随机抽签或消费 HighDiv 的 RNG。

---

## 6. 解决表达式绑定：精确规范化，不重新向求解器添加表达式

### 6.1 必须支持的低风险匹配

新增 `canonicalize_atom(expr_view, WorkBudget&)`。它在宿主数据或只读内部 AST 上计算键，不为了比较创建反向等式或辅助 Z3 变量。

支持：

1. 原表达式直接匹配。
2. 等式左右交换，例如 `x=10` 与 `10=x`。
3. NOT 链、literal 符号与相位正确组合。
4. 精确整数线性整理，例如 `x=10` 与 `x-10=0`。
5. 整数严格/非严格比较的等价形式，例如 `x>2` 与 `x>=3`；必须保留取反极性。

可以做项的精确线性展开、常量合并、确定性的符号/系数规范化。这是表达式等价识别，不是从公式推出新取值域。

不得：

- 把 `x!=10` 当成 x 的某一位固定为相反值；
- 把 `x>=10` 当成 `x=10`；
- 用浮点系数/取整做等价键；
- 把不同变量只按局部编号或裸地址视为相同；
- 从样本中只出现0/10就推导域为 `{0,10}`；
- 将不完整线性化结果用于指导。

当操作数、深度或资源上限到达时，返回 `normalization_incomplete`，本次不建议；不能采用只算了一半的相位分数。

### 6.2 从实际决策对象反查

在 `context::decide()` 真正选到 `var` 时，对 `bool_var2expr(var)` 做只读规范化，查询 `AAtomIndex`。首次解析结果可按上下文代际缓存，后续更新只读当前需求分数。

不再要求在 check 开头 `lit_internalized(original_expr)` 成功之后才有指导资格。某些原子在稍后才出现；只依赖开始时的静态列表会漏掉它们。

`bool_var` 不能跨上下文或 pop/reset 盲目复用。缓存键必须含上下文实例/代际，缓存中的表达式要有可靠生命周期引用；不能只相信裸编号不复用。

### 6.3 被预处理消元的变量

规范化不等于完整恢复 solve-eqs 的替换关系。若原目标涉及已消去变量，而本轮没有可靠的 provenance/reconstruction 关系，记录 `eliminated_or_unmapped`，不重新引入变量。

可利用现有、已经导出的确定替换记录，但必须是明确可验证的等价映射，不能通过单个模型猜测。为避免范围膨胀，本轮不要求新建通用预处理逆映射器；修复到哪里、仍缺哪些范围，报告必须量化。

只有实际记录了预处理删除/替换证据才能写 `eliminated`；仅没找到匹配时应写 `unmapped_reason_unknown`。

### 6.4 Reach 与 A 的保证程度

A 不创建 Reach 目标公式。等式相位为真可保证对应项的数学值，但不保证该原AST节点实际被访问。

因此建议记录为“值支持”，而不是“保证覆盖”。最终结果须分别核对：

```text
实际原子相位是否保留
原节点是否被访问
指定bit是否取期望值
该观察是否在当次正式提交前仍然缺失
```

---

## 7. 修复后端数据传递：保留路由，进入真正的 tactic 叶子

### 7.1 先记录真实调用链

为每个外层 CDCL check 分配 `query_id`，每个 tactic 子阶段/内核分配 `backend_call_id`、`context_id`。

必须能看到：

```text
combined_solver 选 solver1/solver2 的原因
    → tactic2solver（若有）
    → 具体 tactic 名称/子阶段
    → 临时 smt::kernel / smt_solver / SAT叶子 / 其他叶子
    → setup_and_check 或 check
    → 是否出现普通决策
```

不要用“metadata installed=true”代替“内核收到了请求”；不要用“进入tactic”代替“已经进入SMT”。

### 7.2 建议实现：沿 goal 传递非逻辑 sidecar

新增不可变 `AGuidanceRequest` 与外层 check 专属 `AGuidanceRunState`。前者保存需求快照/直接映射，后者保存统计和有限配额。不要把它们放到全局 `ast_manager` 上。

推荐修改点：

1. `combined_solver::set_coverage/set_A_guidance`：向两端传递 A 元数据，不设置 `ignore_solver1`、不调用 push、不添加 assertion。
2. `tactic2solver::check_sat_core2`：在本次创建的 `goal` 上附加 A sidecar；不把内容转成 goal 中的新公式。
3. `goal.h/goal.cpp`：在本轮实际用到的 copy/copy_to/translate/subgoal 派生路径中保留 sidecar，明确 reset/reset_all 的生命周期。
4. `smt_tactic::operator()`：创建临时 `smt::kernel` 后、实际 check 前，从输入 goal 读取 A sidecar，绑定当前内核；退出/异常时 RAII 清理。
5. `smt_solver::check_sat_core2`：保留持久内核的 A 绑定。
6. `context::setup_and_check` 与 `context::check`：使用统一的 A search-session 初始化，不能漏掉前者，也不能因为后者内部重搜索重复重置。

新增接口示意，不是上游已有函数：

```cpp
class goal {
    std::shared_ptr<const AGuidanceRequest> m_a_request;
    std::shared_ptr<AGuidanceRunState> m_a_run;
public:
    void set_A_sidecar(...);
    ARequestView get_A_sidecar() const;
};

class context {
public:
    void attach_A_guidance(ARequestView, BackendIdentity);
    void detach_A_guidance();
private:
    void prepare_A_search_epoch();  // 只读映射与状态初始化
    AAdvice evaluate_A_phase_hint(bool_var native_var, bool native_phase);
};
```

头文件依赖须保持合理分层：不能让 `goal.h` 包含整个 solver 实现形成循环依赖。可使用前置声明和独立元数据头。

### 7.3 跨 AST manager、分支与并行

裸 AST 指针和本地声明编号不能直接跨 manager。优先传递不可变规范化 IR、原目标 ID 和可核验的声明身份；必要时用实际 `ast_translation` 同步翻译持有引用的表达式。不能只复制 shared_ptr 内的旧 manager AST 引用到另一 manager。

多个子 goal 可共享只读请求，运行统计按 backend_call_id 分开，外层 check 的64/4额度共享。若真实路径有内部并行，需线程安全配额和独立 per-context 状态；不能让两个线程各自免费得到4次指导。若无法安全支持某分支，标记明确的 unsupported，而不是串改原生路由。

禁止进程全局裸指针或未限定所有者的 thread_local 请求：同一个 context 中的 CCSS、辅助solver或后续无关调用可能误接收它。

### 7.4 CCSS 隔离

只有 HighDiv 的 CDCL solver 发出 A sidecar。CCSS 的 solver、goal 和 `m_ls_sampling=true` 内核不安装、不调用 A。

在 `setup_and_check()` 中发现 `m_ls_sampling` 时必须保持原流程。即使出现错误传递也要拒绝A并记录，而不是让CCSS走普通CDCL指导。

CDCL产生的新模型可以通过HighDiv原有方式影响后续CCSS，这属于原有混合流程；不要声称新指导对CCSS的实际样本供给完全无影响。

### 7.5 纯 SAT 或预处理已经决定结果的分支

如果某次真实 tactic 最终在非SMT叶子结束，或不需要普通决策就得到结果：

- 分别记录 `non_smt_leaf`、`preprocess_decided`、`no_ordinary_decision`；
- 不为追求触发率删除预处理、不强制走SMT、不添加虚假assumption；
- 本轮不额外引入另一套SAT内部指导器。

目标是让 A 覆盖自然到达的SMT决策，不是保证每次查询都有改相位。对两个关键实例必须给出实际路由证据和支持比例，不能再次只写“后端不支持”。

---

## 8. A 相位仲裁：函数级实施规则

### 8.1 保留原生决策顺序与 RNG

`context::decide()` 仍先执行原来的：

```text
特殊分支/临时子句处理
has_split_candidate
m_case_split_queue->next_case_split
guess(var, phase)
用户传播器/其他已有干涉
```

A只处理普通队列产生、尚未赋值、没有特殊协议的原子。对于用户传播器、量词、已指定的特殊 phase、非普通理论分支等，不得擅自覆盖。

`guess()` 必须按原条件调用，即使最后A改了相位，也不能为了节省随机调用而跳过它。关闭A时，原生随机数消费、变量选择和路由应保持一致。

### 8.2 仲裁伪代码

```cpp
AAdvice context::evaluate_A_phase_hint(bool_var v, bool native_phase) {
    if (!a_state || !a_state->enabled()) return NoAdvice(Disabled);
    if (!is_ordinary_eligible(v)) return NoAdvice(SpecialDecision);

    auto ordinal = a_state->next_external_check_ordinal();
    if (ordinal > 64) return NoAdvice(DecisionWindowExhausted);
    if (get_assignment(v) != l_undef) return NoAdvice(AlreadyAssigned);

    auto mapping = live_atom_index.lookup_or_normalize(v);
    if (!mapping.complete) return NoAdvice(mapping.reason);

    auto scores = mapping.score_unattempted_demands(a_state->snapshot);
    if (!scores.complete) return NoAdvice(ScoringIncomplete);
    if (!scores.has_active_demand) return NoAdvice(NoActiveDemand);
    if (scores.true_score == scores.false_score) return NoAdvice(ScoreTie);
    if (a_state->suggestions_used >= 4) return NoAdvice(ActionQuota);

    bool desired = scores.true_score > scores.false_score;
    // 开始改变前检查显式成本与整次查询暴露额度
    if (desired != native_phase && !a_state->can_start_override_now())
        return NoAdvice(ExposureBudget);

    return Advice(desired, scores.supporting_original_demands);
}
```

实际代码可更高效，但不能省略语义区分。先完成全部评分再改变相位，不按候选扫描到一半的分数操作。

对于已经内核化的 NOT literal，必须正确组合规范化负号与实际 literal sign；测试正负相位两种情况。

### 8.3 提交与返回值

A 的提交只允许：

```cpp
const bool native_phase = is_pos;
const bool_var native_var = var;
AAdvice a = evaluate_A_phase_hint(var, native_phase);
if (a.has_suggestion()) {
    record_suggestion_before_assign(a, native_var, native_phase);
    is_pos = a.phase;
}
SASSERT(var == native_var);
// 原生 literal 构造、assign 和后续逻辑保持原样
```

A 不调用 `unassign_var_eh(original_choice)`，因为没有换变量。把旧B在 `var==null_bool_var` 时补发新选择的分支排除在本轮A路径之外。

若原生已没有候选，A不能创造决策来凑触发次数。

### 8.4 回溯后不强行再次施加

一旦一次建议使用了某个 DemandId，同一个外层 check 内记为 attempted。回溯、restart、tactic fallback不重置它。

原生 phase saving 可能自然保留先前选择，这是正常求解器历史；A不能每次回溯都额外重写缓存或再次强迫同一个相位。

---

## 9. 补齐诊断链：注册、准备、遇到、建议、改动、命中分开

### 9.1 必须输出的三张主机制表

**请求表 `a_query_requests.csv`**，每个外层CDCL check一行：

```text
query_id, coverage_version, single_sided_bits
A_mappable_targets, index_entries, entries_updated
observer_seconds, index_build_seconds, index_update_seconds
request_register_seconds, request_size_bytes
has_request, disabled_reason
```

**后端表 `a_backend_calls.jsonl`**，每个实际后端调用一行：

```text
query_id, backend_call_id, parent_call_id, solver_id, context_id
outer_route, tactic_name, entry_function, ls_sampling
metadata_received, ordinary_decisions, context_generation
binding_seconds, normalized_atoms, exact_matches, normalized_matches
unmapped, unsupported_normal_form, incomplete_mapping
result, original_reason_unknown, check_seconds
```

**决策漏斗 `a_decision_funnel.csv`**，每个query或backend汇总：

```text
native_ordinary_seen
within_decision_window
has_direct_mapping
has_current_demand
score_tie
quota_rejected
cost_rejected
same_phase_suggestions
phase_overrides
outside_window_potential  // 仅有界诊断模式；正式未检查则NA
```

### 9.2 为什么“已经赋值”和“没被选中”必须另查

实际 `decide()` 正常只会处理未赋值原子，所以不能只在回调里检查赋值状态，就声称解释了所有绑定目标的流失。

在受控诊断模式中，于实际普通搜索开始前、原有 assumptions 完成后，对有界的可匹配集合做一次只读绑定快照；区分：

```text
not_internalized
bound_unassigned
bound_assigned_true
bound_assigned_false
mapping_incomplete
```

之后关联该集合是否在决策窗口被遇到。对于未遇到的条目，报告 `not_selected_in_observed_window`，不能直接叫“不可达”。

若没有记录赋值原因，不得断言由哪个assumption传播；可记 `assigned_reason_unknown`。不得为得到原因新增求解检查。

完整绑定快照只在微诊断开启，限制条目和序列化成本，正式实验用已有轻量索引计数。

### 9.3 每次实际建议的结构化日志

对最多4次建议保存完整事件，不在热路径执行 `to_string()` 或拼接长JSON：

```json
{
  "query_id": 12,
  "backend_call_id": 3,
  "context_id": 5,
  "decision_id": 9,
  "level": 7,
  "source": "A",
  "native_phase": false,
  "suggested_phase": true,
  "phase_changed": true,
  "mapping_kind": "exact_linear_equivalence",
  "support": [{"node": 42, "desired_one_mask": "2", "desired_zero_mask": "0"}],
  "coverage_version": 6
}
```

上述数值只是schema示例，不是实验数据。AST内容放到去重catalog，事件只引用稳定ID。对跳过事件仅累计原因，保存固定数量见证，不写每一步全量公式。

### 9.4 回溯/放弃记录

为每次实际建议记录 `decision_level` 与本次assignment token。在正常 pop/backtrack 钩子中，标记该赋值是否被撤销。

应区分：

```text
trailed_assignment_popped：那次赋值被回退撤销
reassigned_opposite：之后观察到相反赋值
reassigned_same：之后原生再次取同相位
final_atom_truth：最终可提取的原子真值
```

`popped` 不等于“目标被证明不可达”，也不必等于最终目标失败。没有记录到后续重赋值时写unknown，不凭最终模型倒推完整搜索历史。

清理时避免重用的bool_var/token引用错误。每个check最多4条需要追踪的事件，不开启全量冲突/学习子句转储。

### 9.5 最终命中归因

新增 `AOutcomeTracker`：只把本次CDCL请求中的A事件关联到同一次check生成的正式CDCL模型。不能把随后CCSS偶然命中的目标归为这次A直接命中。

每个目标记录：

```text
formal_model / no_formal_model
reached / not_reached
desired_value_observed
was_missing_before_commit
new_covered_for_this_target
```

同一 `(model_id, DemandId)` 去重；整个模型的全部gain单独保存，不能给每条A事件都复制一份。对没有匹配事件的新观察保留为模型收益，不强行因果归因。

---

## 10. 分开诊断“注册成本”和“主动指导成本”，本轮不启动 B

### 10.1 三种测试模式

以下仅用于有限微测试，不加入正式16项矩阵：

| 测试模式 | 观察/索引/传递/匹配 | 改相位 | 用途 |
|---|---|---|---|
| `a_off_test` | 关闭A新增工作 | 否 | 关闭行为与小问题基础路径 |
| `a_observe_test` | 与A相同，计算会给出的建议 | 否 | 测注册/映射/诊断成本，保持普通决策 |
| `a_apply_test` | 相同 | 是 | 测真正执行偏好后的求解行为 |

这里“注册”只指A元数据传递，不是B目标内部化。三个模式的 `B_created/B_internalized` 必须都是0。

`a_observe_test` 不得调用 `mark_as_relevant`，不得调整phase缓存；否则不是无主动指导对照。

### 10.2 微测试输入和预算

首先使用合成问题完成确定性测试。随后从已保存正式日志中事前选择：

```text
Bromberger、SMT_random、SMT_real、convert
每实例固定3个CDCL查询快照
每快照3种测试模式
最多36次调用，每次最多2秒
```

快照包含原公式、当次原有assumptions、原变量映射、之前正式模型形成的观察状态、上游参数和源码哈希。按确定规则选：首个有观察历史的check、第10个有历史check、最后一个完整check；不存在则缺失，不挑高收益样本补位。

这些新建solver只用于机制诊断，不运行完整900秒hybrid，不生成新的HighDiv正式基线。所有成本保留。

明确：重建公式和assumptions不是恢复原求解器学习状态。诊断比较的是相同重建输入，不能说与历史内部状态完全相同。

执行顺序冻结并轮换；计时诊断与正式实验分开。需要更多debug日志时只在这批受控调用使用。

### 10.3 可以得出的结论

- off与observe：新增观察、索引、传递与只读匹配的实测成本。
- observe与apply：在相同重建输入上的局部行为差异。
- observe的建议计数但零实际改相位：软偏好建议可形成，不等于求解被引导。
- apply必须有真实override见证，不能只通过模式开关验证。

不能以这批微测试的性能替代8实例900秒结果。

---

## 11. 成本控制必须考虑持续影响，但不能伪造精确因果成本

### 11.1 三层成本分开

新增 `ACostLedger`，至少包含：

**直接显式成本**：观察、索引构建/更新、注册、绑定、规范化、评分、诊断序列化。

**指导查询暴露时间**：只要某次外层CDCL check发生真实相位override，就保守地记录该整次check的墙钟时间，包含内部fallback的时间。这不是“A额外增加的时间”，而是被改变过的整次求解成本。

**停止指导后的后续成本**：停止后CDCL/CCSS耗时、Unknown、模型数、覆盖曲线，以及仍存活的历史学习状态。单独统计，不冒充已恢复未干预HighDiv。

这些时间可能重叠，主报告不把它们直接相加成总墙钟。会话端到端成本仍以统一计时为准。

### 11.2 为什么不能承诺精确限制全部历史影响

A改变过决策后，原生相位记忆、学习子句和后续模型轨迹可能已经改变。只清空A请求不能消除这些历史；在不复制/恢复整个求解器的前提下，也无法知道“没有A会花多久”。

因此本轮不承诺“全部因果开销严格小于5%”。承诺的是：

1. A本身不增加长期目标定义；
2. 对显式计算与发生真实override的查询暴露分别设置有界策略；
3. 停用以后不再施加新偏好；
4. 保留历史效应、实际尾部成本和端到端结果。

### 11.3 事前冻结的保护设置

沿用900秒会话5%的工程量级，本轮默认：

```text
explicit_budget = 45秒
intervened_check_exposure_budget = 45秒
native_query_timeout_max = 原50秒，不改变普通非指导查询设置
ordinary_decision_window = 64
A_suggestion_limit = 4
```

45秒是保守的工程保护，不是已验证最佳值；不按这8例结果反复修改。

- 显式准备/索引工作循环设置取消检查，额度耗尽停止新增A工作。
- 首次真实override之前，检查整次外层check已经经过多久；若剩余暴露额度不足，不开始这次override。
- 一旦发生override，该外层check的整个经过时间用于保守计费，包括其内的原生工作和后续fallback。
- 达到暴露额度时，使用Z3原有安全资源检查/退出路径，使当前外层CDCL check以专门的 `guidance_exposure_limit` Unknown终止；然后按原HighDiv顺序继续CCSS及后续查询，A在本会话停用。

这是新增的指导成本保护，可能提前结束本来可继续求解的那次查询。必须明确报告这一代价，不能声称HighDiv所有查询终止行为完全不变。

### 11.4 安全实现要求

不要在正在赋值/传播的任意语句抛自定义异常，尤其不能破坏base-level不可回退传播。应接入实际版本已有的安全取消/resource-limit检查与异常清理路径。

预算属于最外层 CDCL check，不因临时内核销毁、fallback、新tactic子阶段重置。各阶段共享统一deadline；避免当前子阶段取消后下一fallback重新花50秒。

`guidance_exposure_limit` 与普通timeout、会话900秒截止、资源耗尽、算术不完整分别记录。清理check-local取消状态，不能污染同一context中的下次CCSS。

在 `combined_solver` 与 tactic 的 fallback 边界必须检查同一个sticky的指导退出标志；仅让某个SMT子内核返回Unknown，可能触发后面的fallback继续耗时，不能算已经限制了外层check。使用可被安全传播的专门退出原因，记录每个被跳过的后继阶段。

不得在退出后偷偷补跑一个无指导check或恢复一个新solver来获取见证；这会新增算法流程。任何已合法返回、及时完成的模型按既有规则交付。

安全取消只能在检查点响应，因此单次不可分操作仍可能超额。报告 `requested_limit / actual_end / overrun`；不写成硬实时保证。

若无法通过复用/取消/清理测试，不能启用不安全保护后继续正式实验。保留失败证据并修复，而不是用空catch掩盖。

### 11.5 停用之后

停用后不再更新A索引、不再注册空请求来维持逐决策监控，不再计算指导评分。必要统计改为查询级快照。

原公式合法性验证、完整原变量输出、去重、收据与正式计分必须继续。若为控制显式开销停用了在线覆盖观察器，记录最后在线版本，后续增量标为未在线计算；最终覆盖一律由离线官方脚本重放，不输出陈旧在线值冒充终点。

对持久内核不得直接删除合法学习子句或清空原生phase缓存。日志记录 `guidance_disabled_but_native_history_retained=true`。

### 11.6 必需的持续影响测试

在有限合成问题上：一次A改相位 → 停用A → 若干次普通check。

核验停用后：

```text
A新增建议/override均为0
A新增目标/断言/literal始终为0
注册与评分路径不再执行
普通SAT/UNSAT语义和后续CCSS可继续
历史学习仍可存在，不能要求模型与从未启用A时完全一致
```

---

## 12. 日志开销、状态可追溯与失败输出

正式日志采用“固定计数器 + 每次至多4条建议事件 + 去重catalog”。不要每个原生决策同步flush，不要重复输出整个原子或全目标列表。

建议文件：

```text
query.jsonl / 既有 queries.jsonl
backend_calls.jsonl
a_requests.jsonl
a_actions.jsonl
a_skips_summary.jsonl
a_atom_catalog.jsonl
a_outcomes.jsonl
cost_ledger.jsonl
lifecycle.jsonl
```

保留统一的 `run_id/query_id/backend_call_id/context_id/coverage_version` 关联。

`lifecycle.jsonl` 记录：install、实际内核attach、search entry、正常detach、异常detach、reset/pop、停用原因、取消清理。

表达式内容只在首次绑定成功或有限失败见证中保存。Hash只用于快速查找，碰撞必须做完整键比对；不同公式或不同声明身份不得合并。

日志截断、失败、无正式模型、零收益、Unknown、超过截止的模型保留。不得因为日志缺一行就重新生成本轮正式结果。

---

## 13. 测试清单：正确性和“真正触发”都要覆盖

### 13.1 原有回归

保持第一轮的观察器差分、模型投影、截止收据、原公式合法性和归档测试。上游已复现的32字节泄漏例外仅保留原精确范围，不扩大抑制、不关闭一般泄漏检查。

### 13.2 新增规范化/相位测试

必须覆盖：

- `x=10`、`10=x`、`x-10=0` 的映射；
- NOT、双NOT、内部literal负号组合；
- 整数严格与非严格比较、负常数、大整数；
- 等式为假不能支持相反bit；
- 不相同关系不得误匹配；不完整规范化不能介入；
- 当前已覆盖或两侧未见的bit不计分；首次观察不直接算covered；
- 一次模型更新移除已补齐目标，重复AST和别名不得重复加分。

小问题中可用独立求解检查规范化关系的等价性，这是测试，不是在线不可达分析。

### 13.3 真实 A 改相位的正反见证

构造有普通选择的有限公式，在observe模式记录原生相位；使用同样重建状态和固定需求，让apply模式确实改变至少一次相位。

要求：

```text
原生选中的变量相同
native_phase按原函数先计算
实际phase_changed=true
最终赋值满足原公式
存在最终命中缺失bit的正例
存在偏好与原有约束不相容但仍返回合法模型的放弃正例
```

不能仅要求 `a_used>0`；同相位建议不足以证明override接口有效。

### 13.4 后端路径测试

- 持久SMT内核 `check()` 可接收A。
- 默认solver的tactic路径、新建临时SMT内核、`setup_and_check()` 可接收A。
- 注册元数据不会改变solver1/solver2初始路由选择。
- tactic同manager复制、goal复制、必要跨manager翻译、fallback都不丢请求/混淆身份。
- 配额不随子内核、restart、重搜索重置。
- 预处理直接决定结果、纯SAT叶子清楚标为不需要/不支持，不强行改路由。
- 两个solver同context互不污染；CCSS绝不接收A。

### 13.5 静默注册测试

在无墙钟触发、固定输入与随机种子的受控小问题中，off与observe应保持原生决策/模型轨迹一致。

若不一致，先检查：A是否创建了反向等式等额外AST、改变声明内部编号、修改随机流、改变tactic路由或phase缓存。差异必须解释或修复，不能直接叫噪声。

正式900秒轨迹受时间和并发影响，不能要求它们逐模型完全相同。

### 13.6 成本与生命周期测试

覆盖64次窗口/4次建议、查询暴露超额、fallback、取消后复用、pop/reset、析构、异常退出和停用尾部。

尤其验证：同相位建议不记为实际override暴露；observe不触发指导退出保护；多个内核共享外层check的保护；预算退出之后不阻断CCSS。

Release和ASan/UBSan均通过后才能正式运行。不得用SAN构建做性能比较。

---

## 14. 阶段验收与禁止的“修复”

实施阶段按独立提交组织：

```text
S0：只读旧证据分解、补齐路由诊断
S1：A专用隔离、非侵入元数据与tactic传播
S2：规范化匹配、原生原子反查缺口、单相位broker
S3：分层日志、命中/回溯记录、显式与暴露成本保护
S4：Release/SAN/微诊断、冻结协议与实现
S5：16项正式A-only、审计、报告、归档、推送
```

每阶段报告新增与仍未知的范围，不在中途按覆盖结果改变窗口、配额、bit权重或选seed。

以下不能作为“让A终于起作用”的办法：

- 将已传播原子强行变成decision；
- 把没有匹配的原子重新加入公式；
- 把变量选取改成覆盖优先队列（这是另一机制）；
- 将默认solver换成simple/incremental；
- 删除solve-eqs或重写整个预处理；
- 启用B目标作为A触发器；
- 只报告同相位建议，把它称为实际相位改变。

如果某实例确实没有可用于A的普通原子机会，真实记录这一适用性边界，不强造介入。不能因此省略该实例正式结果。

---

## 15. 正式实验执行与冻结

### 15.1 计划

新增 `configs/round2_a.json`、`scripts/freeze_round2_a_plan.py`、`scripts/run_round2_a.py`，或在现有脚本中添加不会覆盖旧计划的新轮次参数。

计划应绑定：

```text
8个输入SHA-256及顺序
新实现提交/源码哈希
原HighDiv上游与共同测量补丁哈希
可执行文件与实际加载libz3哈希
官方计分脚本及计分环境
seed=0、900秒、两种独立停止模式
16个逻辑CPU槽、每槽绑定、启动方式
64/4配额、45秒显式额度、45秒指导查询暴露额度
正式日志级别与不可覆盖输出目录
```

不重新生成HighDiv基线计划，不复用第一轮 `QUEUE_STARTED.json`。保留每项只执行一次的锁和attempt记录。

### 15.2 调度

将8个time900和8个n100任务放入16槽同步启动，按冻结manifest分配到逻辑CPU。使用实际拓扑，不假定CPU编号与物理核映射。

100模型任务先完成后不补跑其他正式配置。剩余time900任务继续；记录并发占用时间线。

禁止与正式计时同时进行构建、压缩、独立覆盖审计或大文件推送。

HighDiv基线第一轮与新轮次负载背景可能不同；仍按用户要求复用，不重跑。报告注明历史基线和单seed限制，不宣称严格同步配对或统计显著。

### 15.3 计时与接纳

沿用共同测量版本：公式解析、观察器/索引初始化、日志、模型恢复、验证和输出均在900秒内计费。无样本上限使用明确的optional/unlimited表示，不传上游`-n 0`冒充无限。

合法、不同、及时的零covered模型仍保留。官方计分只使用确认完成的正式模型，迟到/损坏/重复另归档。

---

## 16. 官方计分与独立审计

继续使用冻结HighDiv的 `HighDiv/my_scripts/calc_metric.py`，不更换分母、不采用新节点或辅助节点计分。

```bash
"$BASELINE_VENV/bin/python" "$FROZEN_METRIC" \
  -f "$ORIGINAL_SMT2" -s "$FORMAL_SAMPLES" -m wire_coverage
```

同时保存官方两位小数百分比与同一统计实现导出的精确covered/total。独立核验全部正式模型的原公式合法性、样本身份、顺序、截止和增量覆盖。

在线观察器若因成本永久停用，离线补全后续覆盖，不把在线缺项当0；在已在线记录范围内逐模型差分一致。

数量模式报告：actual_models、complete100、time100。只有双方完成100，才进行严格C100比较；否则保留未达到与实际覆盖。

时间模式完整报告900秒覆盖、模型数、AUC和固定前缀，不靠多输出模型数替代覆盖目标。

---

## 17. 最终结果表与结论规则

至少输出：

### 表1：性能

每实例包含：冻结HighDiv、新A、第一轮A-only的精确覆盖与差值；900秒正式模型数；独立100模型完成率/耗时/覆盖。

主判断是新A相对完整HighDiv。优于旧A但不优于HighDiv，只说明修复了内部版本，不宣布项目性能成功。

### 表2：A漏斗

逐实例/模式列出：后端接收比例、实际SMT普通决策数、直接映射率、活跃缺口率、建议、同相位、override、最终保留、Reach、目标新观察。

将无介入原因明确分类：unsupported leaf / no native decision / normalized mapping missing / assigned / not encountered / no demand / tie / quota / cost。

### 表3：成本

显式准备、绑定、热回调、日志、指导check暴露、预算退出、停用后尾部、原生CDCL/CCSS总时间。

不要把暴露时间称为额外成本，不把5%记账额度称为总性能损失上限。

### 表4：机制命中

每个被指导模型的原生相位与建议相位、支持目标、是否回退、最终命中、整个模型实际增益。大收益案例必须同时附零收益/放弃案例，不只挑正例。

### 允许的结论

- 路由已修复但没有可用原子：接入修复成立，当前A语义映射范围仍不足。
- 有override但少命中：偏好确实改变了搜索，目标保持/访问/可实现性仍存在问题。
- 有命中但固定时间退步：引导收益未覆盖总体成本，不通过性能目标。
- 无override但覆盖变化：不能归因于A相位指导。
- 相对HighDiv两个口径有正差：本轮单seed开发证据，非稳定性/显著性或普遍性证明。
- 全部结果为负：照常归档，不增seed、不重跑基线、不重新开启B补救。

---

## 18. GitHub归档与最终交付

本轮工作区位于独立guided_sampler目录/工作树，分支例如 `round2-a-routing-repair`。

上传：

- A专用实现和最小Z3补丁；
- 新增测试、运行/计分/审计脚本；
- 新轮协议、完整参数、源码/依赖哈希；
- 只读旧证据分解；
- 微诊断的全部成功与失败记录；
- 16项正式结果、原始模型/日志无损归档与哈希；
- 中文报告 `docs/round2_a_results.zh.md`；
- 机制文档 `docs/A_soft_phase_guidance.zh.md`，明确说明“软指引在哪个函数、只改什么、不能保证什么”。

复用第一轮归档通过固定SHA引用，不重复复制1.87GiB。新归档按现有分片/校验方案保存，验证可恢复；不上传venv、依赖二进制、凭据或未获授权公开的输入内容。

使用本地Git凭据非强制推送，核对远端SHA与本地一致。不重写第一轮提交，不声称仅上传报告就等于原始结果已归档。

最终回复必须提供：分支/提交、实际正式运行数、HighDiv未重跑证明、正确性/审计状态、A真实override数、两个关键实例的后端路由与支持情况、性能差值、全部未解决问题和报告链接。

---

## 19. 已核对源码索引

以下链接固定到本轮依据的版本。它们证明现有实现状态，不证明本指引建议的新修复已经完成。

[S1] A/B仲裁与目标内部化：
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/src/z3_broker.inc

[S2] 外层指导桥接、成本和目标窗口：
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/include/guidance_bridge.hpp

[S3] 观察器、旧窗口、目标编码、直接原子目录：
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/include/observation.hpp

[S4] 第一轮后端转发与决策入口补丁：
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/patches/20_z3_guidance.patch

[S5] 第一轮内核指导状态：
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/src/coverage_guidance.h

[S6] tactic2solver的goal创建与tactic调用：
https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/solver/tactic2solver.cpp

[S7] 临时SMT内核、setup_and_check调用：
https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/tactic/smt_tactic_core.cpp

[S8] goal的copy/reset/translate接口：
https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/tactic/goal.h

[S9] QF_LIA tactic多叶子与预处理流程：
https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/tactic/smtlogics/qflia_tactic.cpp

[S10] 实际context搜索入口与CCSS分支：
https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/z3/src/smt/smt_context.cpp

[S11] 第一轮主结果与机制统计：
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/docs/round1_results.zh.md
https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fc19bd22609295ed405e1ac96bf35d695c42832a/results/analysis/mechanism_main.csv

---

## 20. 执行摘要

本轮不是另加一个软优化器，也不是重新启用B。要实现的是：

**沿真实HighDiv求解路径传递覆盖信息，在已有普通决策原子出现时识别其关联的单侧bit缺口，只调整这一次相位；用完整日志证明建议真的到达、真的改变、最终是否命中，并控制发生指导后的整次查询成本。**

先修接入与可观测性，再用唯一的新A-only配置完成16项既定实验。没有有效机会时诚实报告，不通过改变算法边界制造触发；有触发而没有收益时同样如实报告。最终性能判断始终面对已经冻结的完整HighDiv参考。
