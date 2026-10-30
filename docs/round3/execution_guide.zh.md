# Guided Sampler 第三轮：从软相位到原 AST 位观察的语义诊断

## 0. 执行目标与冻结边界

从以下提交新建分支 `round3-a-semantic-diagnosis`，实际完成诊断代码、测试、有限实验、归因报告、归档和推送。不要只写计划。

```text
项目：ChenKaichen-SCUT/guided_sampler
基点：2f839861acf0a8cec78e05dac256b98b0dc30099
上游 HighDiv：f2c6e1756b13281d96cbf90a8bd940129e56cce4
远端：https://github.com/ChenKaichen-SCUT/guided_sampler
```

**本轮是机制定位，不是第三次完整性能比较。** 不运行新的 8×2 项 900 秒矩阵，不重跑冻结 HighDiv，不追加 seed，不启用 B，不实现在线宏观域分析、不可达排除、MaxSMT、数值移动、目标批修复或新的调度器。原始 HighDiv、8 个输入、两轮结果、基线二进制与归档全部保持不变。

主任务：解释原生决策、理论传播、模型构造、模型恢复、官方短路访问之间，哪一步使所选缺失位没有实现；由证据给出下一项策略设计，而不是先假定“relevance 就是原因”。

第一阶段保持第二轮 A 的决策规则、64 次窗口、最多 4 次建议、显式/暴露保护和原 HighDiv 流程不变。新增观测不应改变公式、变量选择、原生随机数或理论相关性。后文的独立可达性检查与有条件干预对照只属于诊断，不接回在线采样。

已有事实（作为复核对象，不代替复核）：第二轮 916 次建议、534 次实际改相位，都在 convert；独立审计中 716 次内部 assignment 保留、0 次返回模型保留；941 条目标 bit 支持记录中 320 条被访问、0 次期望值命中。两个主实例已接入 SMT，但在实际观察窗口内没有映射。来源见文末 S1–S4。

---

## 1. 先明确要检验的语义链

A 不是直接把整数某个位改成 0/1。A 只把某个已有原子的当前普通决策先尝试方向改为真/假。

```text
历史缺口（原节点、位号、缺失值）
  → 原式原子对该值的支持规则
  → 实际内部原子与原式原子的对应
  → 普通决策的相位建议
  → assignment 是否仍存活、原子是否 relevant
  → 等式/EUF 或理论原子传播
  → 叶子原始模型
  → 预处理/模型转换后的完整模型
  → 原变量输出快照
  → 原 AST 官方访问路径
  → 新观察与新增 covered
```

每一步分别记录；不得用后一步没有命中反推前一步的原因。

### 1.1 两种“相关性”绝不混用

- `solver_relevant`：Z3 内部是否需要把这个表达式/原子的赋值纳入理论求解。
- `metric_reached`：官方 `calc_metric.py` 按原 AST 顺序、AND/OR 短路和 ITE 分支是否实际访问该节点。

这两个量不是同一个量。`solver_relevant=true` 不意味着官方一定访问；官方访问也不能由历史某次 relevance 标记直接推出。

### 1.2 四个独立结果

对每一个目标，在最终完整原变量赋值上同时计算：

```text
value_hit：不考虑访问，表达式的位值是否为 desired
metric_reached：官方是否访问原节点
observation_hit：value_hit && metric_reached
new_covered：observation_hit 且提交前该位只观察过相反值
```

即使节点未被访问，也计算独立纯值 `value_hit`，但不得因此更新官方 seen0/seen1。原模型缺值、原子无法求值时保留 `unknown`；不得默认 false。

---

## 2. 本轮需要排除的原因

使用以下标签，允许一个事件同时有多个问题，并记录“最早有证据的断点”。无法判定的保留 UNKNOWN。

| 标签 | 含义 | 不能据此声称什么 |
|---|---|---|
| MAP_ERROR | 实际原子、极性或支持规则不正确 | 不能说指导思想无效 |
| PREPROCESS_GAP | 原子只在预处理替换/辅助定义下对应，现有索引缺少该关系 | 不等于原目标不可达 |
| EVENT_OR_MODEL_MISMATCH | 事件、叶子、模型、上下文或变量身份配错 | 不能解释为正常回溯 |
| ASSIGNMENT_ABANDONED | 该次建议 assignment 被撤销/变号 | 不等于目标全局不可达 |
| NOT_THEORY_ENFORCED | 当前存活的赋值没有成为模型必须兑现的理论条件 | 不能只凭某时刻 irrelevant 就确认 |
| MODEL_RECONSTRUCTION_GAP | 已核实叶子模型与最终模型对应发生问题 | 不能把未映射内部变量直接代入原模型比较 |
| VALUE_HIT_NOT_REACHED | 位值达到期望，但官方未访问 | 不能计入 covered |
| FIXED_CONTEXT_BLOCKS | 当前 HighDiv 固定条件使目标不可行，但原式允许 | 不能永久删目标 |
| GLOBAL_TARGET_UNREACHABLE_DIAG | 独立检查确认原式下目标不可行 | 本轮只报告，不接入在线排除 |
| FEASIBLE_BUT_NOT_FOUND | 存在经验证的目标见证，但当前软相位未得到 | 不等于多翻几次一定能解决 |
| UNKNOWN | 缺日志、超时、无法可靠恢复 | 不用多数猜测补齐 |

另外，七个未实际改相位实例的终点正差不作为 A 的直接效果。convert 的其他位增益与指定目标命中分开报告。

---

## 3. 阶段 D0：先读旧结果，不生成新采样模型

### 3.1 复核全部 916 次建议及 941 条支持记录

读取第二轮 `a_actions.jsonl`、`a_atom_catalog.jsonl`、正式模型/收据、独立 retention 和 target audit。不要修改原文件；输出到 `results/round3_semantics/offline/`。

复核：

1. 每个事件属于唯一 run/query/backend/context generation/decision。
2. 同一查询如有多个 tactic 叶子，事件来自哪个叶子，最后哪个叶子提供了返回模型。失败叶子的 assignment 不得与另一个成功叶子的模型直接比较。
3. 提交前的覆盖版本和 target desired 正确；同相位建议与实际 override 分开。
4. 按官方输入构建顺序重建 node ID，并同时核对节点结构指纹、sort。跨库/跨 manager 不使用裸 AST ID 认定相同节点。
5. 对全部支持目标分别计算纯位值、访问、命中、新 covered。
6. 记录原变量模型完整性。区分真实模型解释、模型转换恢复值、输出时补全值；旧日志没有记录来源则明确缺失。

### 3.2 不能循环地用同一个 canonical key 证明映射正确

旧 retention 审计根据 key 找原式等价原子，再恢复极性。它是重要证据，但不是对 key 生成器的独立证明。

新审计需要实际内部表达式、声明及极性。旧记录没有这些内容时，标记 `raw_internal_atom_missing`，交给新短运行补齐；不得用 key 重新拼出的表达式冒充旧真实原子。

### 3.3 事先冻结见证选择

生成 `manifests/round3_semantic_cases.json`，在任何新干预结果出来之前提交。

优先包含 convert 的时间模式：

```text
query 5 / decision 25
query 7 / decision 30
query 11 / decision 64
```

这些只是历史定位锚点，不要求新运行强行出现相同状态。再按以下类别、run/query/decision/node/bit 的字典序补充，总共至多 12 个 action–target 见证：

- 改相位、未记录撤销、内部与模型不同；
- 改相位、已撤销；
- 同相位建议、内部与模型不同；
- 官方访问与未访问。

同一个 action 支持多个位时每次选最低尚未选过位号，最多取两个；尽量覆盖不同实际原子。数量不足就保留实际数量，不为凑数挑其他有利案例。两个预算模式的数据不当成独立随机重复。

8 个实例的旧数据都做只读概览，但新活运行只针对 convert、SMT_random、SMT_real。

---

## 4. 阶段 D1：增加只读的语义链追踪

建议新增文件：

```text
include/round3/semantic_trace.hpp
src/round3/semantic_context.inc
scripts/patch_round3_diagnostics.py
scripts/select_semantic_cases.py
scripts/run_semantic_probes.py
scripts/audit_semantic_chain.py
scripts/check_target_feasibility.py
scripts/classify_unmapped_atoms.py
scripts/summarize_semantic_diagnosis.py
```

新增名称是本轮设计，不是声称上游已有同名 API。以第二轮补丁生成器为基础增加诊断，实际编译位置应记录在 `docs/round3_hook_map.zh.md`。

### 4.1 事件唯一身份

至少使用：

```text
run_id / external_query_id / backend_call_id / context_generation
 / decision_id / assignment_token / target_id / coverage_version
```

保存实际原子 AST 的受控引用，serialize 时保留 sort、declaration 身份与精确表达式。多个 manager 的内部 skolem 必须分开命名，不按打印名字合并。

一个 assignment 被撤销后，再赋相同变量也必须是新的 token。记录曾经传播不能代替最终存活 assignment 的传播证据。

### 4.2 `context::apply_A_phase_hint()`：记录“建议针对什么”

保留现有相位规则，新增有界 typed 数据：

```cpp
struct WatchedAction {
    EventKey id;
    ExprHandle actual_atom;          // 所属 manager 内持有引用
    bool native_phase;
    bool suggested_phase;
    bool effective_phase;
    bool phase_changed;
    bool canonical_negated;
    AtomKind atom_kind;              // eq / theory atom / Bool / gate / other
    TriBool relevant_before;
    std::vector<SupportRef> support; // 原节点、位、desired、规则来源
};
```

另存原式对应原子、规范化前后表达、规则是“Bool 本身”还是“显式 t=c 为真支持位值”。只缓存将被追踪的至多 4 个建议及少量未映射原子，不在每次决策打印整个公式。

### 4.3 `A_assignment()`：区分撤销与重新赋值

在原生 assign/unassign 钩子记录：当前 assignment token、literal 符号、决策层、trail 位置、来源（decision/propagation/unknown）。回溯要关闭对应 token。

`popped=true` 只能说明原 token 被撤销；后续同值重新赋值不能被误计为一直保留。没有原因字段时不推断是哪个目标引发冲突。

### 4.4 relevance 与理论传播：两条路径都必须覆盖

已核对上游 `context::propagate_atoms()`：

- `is_eq()` 为真时，走 `add_eq()` 或 `add_diseq()`；
- 其他 `is_theory_atom()` 才走 `th->assign_eh(v, val)`。

因此不能只监听 `theory_lra::assign_eh()`，否则会漏掉等式。

为 watched action 增加以下只读事件：

```text
relevance_before / after_assignment / changed / before_model
atom_queue_enqueued / atom_queue_consumed
bool_enode_propagated
equality_merged / disequality_added
theory_atom_assign_eh
theory_eq_or_diseq_delivered
assignment_withdrawn
```

在 `context::relevant_eh()`、`propagate_atoms()`、等式/不等式向理论传播的实际调用点插入有界观测；具体签名以冻结源码为准。等式经 EUF 和理论组合传递时要保留关联，不强求存在某个名为“arith constraint”事件。

先证明覆盖了该类原子的全部传播入口，才能把“没有记录”解释为“没有传播”；否则记 `transmission_not_observable`。

**relevance=false 的单张截图不是根因证明。** 必须观察同一 token 从建议到结束是否后来变为 relevant、是否真正传播、传播是否被回退。

### 4.5 模型证据：必须沿原有导出路径取得

`A_finalize()` 当前只读取 `get_assignment()`。把这个字段明确命名为 `final_internal_assignment`，不能再叫“模型原子真值”。

上游 `context::get_model()` 会调用 `mk_proto_model()`，不是任意时刻可无副作用查询的只读函数。因此：

- 禁止在 `apply_A_phase_hint()`、传播回调或 `A_finalize()` 里额外调用 `get_model()` / `check()`。
- 只在程序原本要生成或导出模型的路径上采集。
- 在 `context::get_model()` 正常生成模型后，或已有的 `smt_solver::get_model_core()` / `smt_tactic` 正常 get_model 点，保存“该内核的实际模型”。不要为诊断多生成一遍。
- 同时在 tactic/goal 模型转换前后和宿主 `Session::commit()` 前后保存受控诊断数据。实际 converter 调用点先核对；如无法找到真正转换前模型，明确记缺失，不能把转换后模型重复标为 raw。

需要四层：

```text
M_leaf：该真实叶子内核导出的模型
M_outer：solver/tactic模型转换后、交给HighDiv的模型
M_original：按原变量投影、补全后的输出快照
M_formal：经正式收据接纳的模型
```

每层记录 watched 原子/项的求值与是否依赖补全。对 M_leaf 的实际原子先用不补全求值；无法得到 true/false 则记 undef，之后只能在副本上补全并单独记录。不得通过补全原 solver model 改变后续 CCSS 交换的数据。

第二轮 `detach_A_guidance()` 清空 tracks，而 persistent solver 的模型读取可能在 detach 之后。增加一个仅用于诊断的 `PendingSemanticSnapshot`：持有受控 expr 引用和事件身份，直到正常 get_model 完成；它不是 active guidance，不能产生建议，不能跨下一查询复用。reset、pop、异常、取消、对象析构全部清理。临时 tactic 必须在 context 析构前完成原子求值或序列化，不将裸指针留给宿主。

### 4.6 不能把不同叶子的模型串起来

增加 `model_provider_backend_id` 和 converter chain ID。一个被 fallback 放弃的叶子没有最终模型时，只能记 `leaf_discarded`。

需要分别判断：

```text
该叶子 assignment ↔ 该叶子实际模型
该叶子模型 ↔ 同一条模型转换链的输出
输出模型 ↔ 原变量快照
原变量快照 ↔ 官方观察
```

未知的映射或来源不能强行比较。

---

## 5. 只读追踪的正确性测试

先通过 Release、ASan/UBSan，沿用第二轮唯一上游泄漏例外，不扩大抑制。

必须有以下受控测试：

1. 真正可行且被访问的目标：建议、原子、位值和覆盖形成完整正链。
2. 原子为真但其分支不被官方访问：value_hit=true，observation_hit=false。
3. 不相关/后来变为相关的原子：日志能区别二者，不预定最终真值。
4. 相位被撤销后同值/反值重赋：不同 assignment token。
5. 原子 NOT、交换等号、严格不等号规范化：原子极性独立核对。
6. 同一外层查询有多个 tactic 叶子/一次失败 fallback：模型只关联提供者。
7. 缺失解释与输出补全：undef 不冒充 false。
8. 临时内核析构、persistent get_model、pop/reset、异常取消、CCSS隔离。
9. 对相同确定性小例的“追踪关/追踪开”，原生选择、原生 RNG 消费、逻辑断言和模型共同轨迹一致（资源截止的差异单列）。

日志不得触发新的求解、新的理论相关性或原式替换。收集诊断所需额外时间不用于宣称性能胜负。

---

## 6. 阶段 D1 的有限运行矩阵

只使用新构建的 A 诊断程序，不执行冻结 HighDiv 二进制。seed=0，CCSS 保留。每种模式独立进程、独立输出。

| 输入 | 模式 | CDCL查询上限 | 会话墙钟上限 |
|---|---|---:|---:|
| convert | observe_trace / apply_trace | 各32 | 各60秒 |
| SMT_random | observe_trace / apply_trace | 各8 | 各60秒 |
| SMT_real | observe_trace / apply_trace | 各8 | 各60秒 |

共 6 次短会话。`observe_trace` 计算同一套 A 建议但不改相位；`apply_trace` 是第二轮 A 的原规则。查询上限和墙钟任一到达就停止；不能提高上限找正例。单次查询沿原 HighDiv 额度，并受这次短会话的剩余时间约束。

这两条持续轨迹在首次 override 后可能分叉，不能把后续相同 query 序号当成相同内部状态；它们提供机制现象，不是完整因果对照。

采集：每个窗口前64次普通决策的轻量类型/键统计；仅 watched 建议和每实例最多8个代表性未映射原子保存完整表达式与可恢复声明。选择“最早不同键”，不按后续收益选择。

诊断与编译、消毒器、压缩、审计分时运行。16逻辑线程可并行独立任务；成对微对照顺序执行且同CPU绑定，不从深度追踪的耗时宣称采样加速。

历史锚点没有重现就记 `historical_trace_not_reproduced`。保存到首次分叉之前的指纹，使用新出现的同类事件继续分析，不能称为旧事件的原样复现。

---

## 7. 阶段 D2：独立“能否实现”检查，不修改采样策略

此阶段回答：该 bit/观察在原式或当前 HighDiv 固定条件下是否真的能实现。它不是在线不可达证明模块，不保存用于排除目标的缓存，不向采样器反馈答案。

### 7.1 符号

```text
F：原始公式
A_q：该次外层 HighDiv 查询原本使用的固定 assumptions
P：所选事件之前的内部相关分支前缀（只用于另列的内部诊断）
D：所选已有原子的建议相位条件
V：原节点所需 bit 的精确值条件，不含访问
R：官方原 AST 中该节点被访问的条件
G：R && V
```

R必须与官方短路语义、共享DAG一致。可以复用已有 ReachBuilder/TargetEncoder 的**纯构造算法，在独立诊断进程使用**；不得在采样器中重启 B、注册目标literal或增加目标约束。

所有 oracle SAT 模型都用原式和官方观察器再次核验。负数与第63位使用精确整数与非负模语义。oracle 的mod编码不能走此前B的低层内部化捷径，使用独立普通solver的完整路径。

### 7.2 每个见证最多8次查询

对最多12个被冻结见证，每个检查最多2秒，Unknown不升级预算：

| 编号 | 检查 | 用途 |
|---|---|---|
| Q0 | F && A_q | 验证保存上下文可满足；已有完整合法模型可直接验证并跳过此调用 |
| Q1 | F && V | 位值本身是否可行 |
| Q2 | F && G | 原式下实际观察目标是否可行 |
| Q3 | F && A_q && G | 当前HighDiv固定条件是否允许该观察 |
| Q4 | F && A_q && D | 被建议的已有原子方向是否可行 |
| Q5 | F && A_q && D && !V | 直接支持规则是否真的保证所需位值 |
| Q6 | F && A_q && D && !R | 该动作是否可能不带来官方访问 |
| Q7 | 独立映射/内部前缀检查，二选一且在计划中注明 | 检验actual atom↔原式映射，或在完整可恢复前缀下检验G |

最多96次oracle调用，不批量扫描全部位、不泛化UNSAT core。Q5/Q6若Q4已证UNSAT，只能记“前件不可行导致真空成立”，不能认定映射和Reach支持良好。

Q7比较内部与原式表达式时，必须显式恢复声明、sort、预处理替换与辅助定义。只有同一语义变量空间中才能检验XOR；单靠key相同不能当证明。无法恢复就记mapping_unknown，不能强行创建同名变量让它们看起来一致。

### 7.3 结果解释

- Q2 SAT：存在真实合法的观察目标见证；不是保证A一定能找到。
- Q2 SAT而Q3 UNSAT：固定条件阻塞，不能说目标全局不可达。
- Q1 SAT而Q2 UNSAT：值可能，但原式不能以官方访问路径观察该值。
- Q5 SAT：支持规则出现反例，优先修复映射/规则，暂停新策略。
- Q6 SAT：原子方向不保证Reach；并非每次都会不访问。
- Q2 UNSAT：仅作为独立诊断事实，保持官方分母和covered不变；不接入线上排除。
- 任一Unknown：保留未知，不等于UNSAT。

所有oracle模型仅为诊断见证，不计入正式样本数和覆盖性能。

---

## 8. 阶段 D3：必要时做真正受控的原因干预

先完成 D0–D2。若原因已确定为映射/极性/事件bug，先修该bug并回放同一组见证，不加入relevance机制。

若证据支持“被建议的原子并未进入理论约束”，才做以下有条件的小规模对照。最多6个真实决策检查点，每个最多4个子运行，每个5秒；不扩大范围。

### 8.1 原生相位 × 局部理论参与，2×2对照

| 子运行 | 本次相位 | 现有原子的相关性处理 |
|---|---|---|
| N0 | 原生相位 | 不改变 |
| A0 | 既有A建议相位 | 不改变 |
| N1 | 原生相位 | 仅对本次现有原子做受控、可随原生scope撤销的相关性激活 |
| A1 | 既有A建议相位 | 与N1相同的局部激活 |

这是诊断性的新干预，不是第二轮A原定义。报告明确承认N1/A1改变了相关性处理。不得把其结果写成“仅修日志后A就变好”。

不内部化任何新原子，不添加目标约束，不全局设置relevancy=0，不绕过理论传播，不强行保持建议相位。如果无法确认原生相关性激活的回溯契约，跳过N1/A1并报告限制；不能直接修改内部标志代替原生接口。

在相关性激活后若正常传播已给变量赋值或产生冲突，交还正常流程，不能继续强制assign一个相反值；单列 `propagated_before_test_decision`。

仅改变选定检查点的这一次操作，子运行中关闭后续新的A建议，保留先前历史。记录原子求值、Reach、目标命中、SAT/Unknown和完整时间。

N1相对N0帮助识别激活本身的作用；A1相对N1才涉及相位建议的增量。不能只比较A1和N0。

### 8.2 “同状态”要求与fork安全

复制F、A_q和seed并不复制学习子句、相位缓存、CCSS交换或预处理状态。

首选受控的Linux单线程诊断进程：按原HighDiv逻辑从头运行到检查点，在任何诊断锁之外暂停，使用进程快照将同一个搜索状态分支成上述子运行。

**禁止对当前带watchdog线程的正式采样进程直接fork。** 第二轮Session会创建watchdog线程。需要独立单线程诊断harness，内部solver线程数为1，检查点时确认 `/proc/self/task` 只有一个线程；用外部父进程管理子进程截止。不得在Z3/诊断互斥量持锁时分叉。输出缓冲预先flush，子进程重新绑定独立日志，不能共享写入同一收据。

快照前检查公式、assumptions、coverage version、原生候选、phase、随机状态及可导出的搜索统计指纹。指纹是检查条件，不是单凭它宣称状态相同；同一进程快照才提供所需历史复制。

如无法安全实现，只做新建查询快照的独立对照，名称写成 `same_query_not_same_state`，不得给出强因果结论。默认不通过额外重跑和加长预算来补足。

---

## 9. 并行任务：两个主实例的未映射原子分类

从D1每实例收集的最多8个不同原子，回答它们属于：

1. 原式原子，仅交换、缩放、严格比较或极性导致规范化遗漏；
2. 原生solve-eqs等替换后才能对应原变量；
3. Tseitin/辅助Bool定义，不能直接当作原节点；
4. 理论生成原子或分支切割；
5. 原式可匹配但没有当前缺口；
6. 当前证据不足。

只读取实际预处理转换链，记录真实替换与model converter。允许补充来源追踪，不改变预处理或恢复被消元的变量，不做新域推断。无法恢复就标unknown。

对最多16个代表原子，可各做一次2秒的独立映射核验；包含在单列mapping-check清单。若需要的背景关系无法导出，不运行伪验证。

报告必须区分“后端接通”“表达式能映射”“存在能指导的真实决策”三件事。不要为增加触发数把任意内部布尔变量映射到缺失位。

---

## 10. 预算与执行次序

| 阶段 | 上限 | 是否采样性能实验 |
|---|---|---|
| D0旧数据复核 | 全部旧建议/目标，不新求解 | 否 |
| 诊断正确性测试 | 固定受控用例 | 否 |
| D1活追踪 | 3实例×2模式；每次最多60秒及查询上限 | 否 |
| D2可达性/支持规则 | 最多12见证×8调用×2秒 | 否 |
| 未映射核验 | 最多16代表原子×1调用×2秒 | 否 |
| D3有条件原因干预 | 最多6检查点×4子运行×5秒 | 否 |
| 900秒正式矩阵 | 0次 | 不执行 |
| 冻结HighDiv基线重跑 | 0次 | 禁止 |

表中的时间是执行上限，不是未来交付时间估计。实际超时检测延迟、退出与初始化成本均记录。独立任务可最多16路并行；同状态分支顺序执行且保持绑定，避免把负载差异当成机制效果。编译/ASan/压缩/审计不与测时子运行重叠。

修复诊断程序bug后重试必须保留失败记录、原因和次数，不允许因没有正例而追加参数搜索。正确性问题必须先修，不能为了凑齐矩阵接受不可靠测量。

---

## 11. 日志、独立审计与验收

### 11.1 输出

```text
results/round3_semantics/
  frozen_cases.json
  offline/reclassified_targets.csv
  traces/<run>/semantic_events.jsonl
  traces/<run>/atom_dictionary.jsonl
  traces/<run>/model_stages.jsonl
  traces/<run>/queries.jsonl
  oracle/<case>/<Q>.smt2
  oracle/<case>/<Q>.result.json
  oracle/<case>/<Q>.model.json
  mapping/unmapped_examples.jsonl
  micro/<checkpoint>/<cell>/...
  analysis/event_chain.csv
  analysis/first_broken_link.csv
  analysis/cause_matrix.csv
  analysis/strategy_decision.json
  audit_summary.json
  BASELINE_UNCHANGED.json
```

日志包含版本、二进制、动态库、input hash、AST指纹、参数、原生假设、叶子来源、所有Unknown/取消/未复现/缺数据。完整日志先落内存有界缓冲，在正常边界序列化；发生溢出必须记录并把依赖完整性的结论降为unknown。

### 11.2 独立核验原则

- 各层真值由实际对应模型求值，不由内部assignment拷贝。
- 映射核验不能调用同一个canonical函数后比较两个字符串就宣布等价。
- 官方访问由冻结HighDiv脚本的求值语义独立计算。
- 位值核验不使用64位有符号溢出；精确整数、低64位mask。
- diagnostic oracle的答案与正式覆盖分开。
- 对失效证据同样归档，不能只保留SAT正例。

### 11.3 本轮成功不是“找出若干新增bit”

本轮验收是给出可复现的断点与足以区分解释的证据。若能得到正链，额外保存其前后完整合法模型和官方观察差分；若目标被证不可行或映射不可恢复，也可以形成有价值的明确结论。

不能用一个玩具正例声称真实数据上方法有效。也不能用一次hard目标求解SAT声称软A已经能够实现它。

---

## 12. 根据诊断决定下一项策略，而不是同时实现所有策略

| 确认结果 | 下一项合理方向（本轮只给建议） |
|---|---|
| 映射/极性/模型事件配错 | 先修正确性并重审旧结论 |
| 内部赋值未进入理论，局部参与对照能改善保留 | 研究有界、可撤销的理论相关性引导；必须单独计成本，不能只加大相位概率 |
| 位值能兑现，官方节点不访问 | 研究访问条件优先的分支协调，再引导值；不是重排AST，也不是改变覆盖定义 |
| F允许但HighDiv固定条件阻塞 | 研究有依据、受限的固定变量释放；本轮不修改fixed_var_pct |
| 可观察目标原式下不可行 | 后续再考虑宏观摘要/可靠排除；本轮不加入 |
| 目标可行、映射与传递正确，但软相位总被撤销 | 分析冲突/协调和收益成本，再决定是否需要更强但可放弃的指导 |
| 大量真实选择来自消元变量/辅助定义 | 研究预处理来源到原观察的语义映射；不靠名字猜测 |
| 现有A根本没有可作用的选择 | 明确A作为当前唯一通道的限制，不以扩大窗口掩盖 |

下一轮性能实验之前，至少需要在真实实例上有可核验的“目标→动作→理论→模型→观察”正链，或明确说明为什么该目标/通道不适用。即便有正链，也仅证明可操作性，不能直接宣称优于HighDiv。

---

## 13. 中文报告与上传

报告 `docs/round3_semantic_diagnosis.zh.md` 首先回答：

1. “没有观察到改变”分别有多少是值没有改变、没有访问、模型转换/补全、映射或测量问题？
2. 内部assignment与模型不一致，第一次可验证的差异发生在哪一层？
3. convert query11/decision64的同类事件是否重现；若没有，哪里首先分叉？
4. 有多少目标在原式可行、当前固定条件不可行？有多少仍Unknown？
5. 两个主实例真实决策原子为什么没有映射？
6. 条件干预对照支持哪项解释，不支持哪项？
7. 下一项只改变一个因素的策略是什么，预计解决哪个已证断点？

汇总按事件、唯一目标、唯一原子和查询分别统计，不把916个相关事件当916个独立随机试验。样本为有意选择的诊断案例，不估计全数据分布和统计显著性。

提交新代码、补丁、固定计划、全量诊断证据、失败记录和中文报告到新分支；原始诊断资料无损压缩并给SHA-256，实际验证可恢复。不上传编译目录、密钥或虚拟环境，不改写两轮历史报告。核对远端SHA；失败如实报告，不声称已推送。

---

## 14. 本指引依据

以下是实际核对的冻结代码。新增追踪结构、诊断矩阵和条件干预是本指引提出的方案，尚未实现或验证。

```text
S1 docs/round2_a_results.zh.md
S2 src/round2/a_context.inc
S3 scripts/patch_round2_z3.py
S4 results/round2_a/retention_audit_summary.json
S5 include/round2/a_guidance_bridge.hpp
S6 include/round2/a_shared.hpp
S7 scripts/audit_round2_retention.py
以上位于：
https://github.com/ChenKaichen-SCUT/guided_sampler/tree/2f839861acf0a8cec78e05dac256b98b0dc30099

U1 z3/src/smt/smt_context.cpp
  propagate_atoms：等式、其他理论原子的不同传播路径
  check_finalize：返回前的内部assignment阶段
  mk_proto_model / get_model：正常模型生成路径
U2 z3/src/smt/tactic/smt_tactic_core.cpp
U3 z3/src/solver/tactic2solver.cpp
以上位于：
https://github.com/laigroup/HighDiv/tree/f2c6e1756b13281d96cbf90a8bd940129e56cce4

官方背景说明（不是对当前事件根因的证明）：
https://z3prover.github.io/papers/z3internals.html
第4.7节 Relevancy filtering
```
