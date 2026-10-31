# Guided Sampler 第四轮：先修复语义映射，再实现覆盖优先的可回溯参考求解

## 0. 本轮目标与边界

基点：`fa68a9996a48cc2251ab2b8d9315da44606825af`。
上游：`laigroup/HighDiv@f2c6e1756b13281d96cbf90a8bd940129e56cce4`。
工作仓库：`https://github.com/ChenKaichen-SCUT/guided_sampler`。
建议新分支：`round4-mapping-soft-reference`。

本轮实际完成两项顺序推进、分别提交和验证的修改：

1. **M阶段：只恢复已有原生决策与原AST的可靠语义对应。** 检查新增映射是否在首模型之后产生真实单侧缺口，而非只增加匹配数量。
2. **S阶段：把采样器自己从CCSS模型继承的硬固定值改成可放弃的参考偏好，再让覆盖需求优先于参考偏好。** 原公式和真实外部约束仍是硬约束。

S阶段是新的算法机制，不是无行为变化的工程修复。不能一面去掉原来的assumptions，一面声称完整保持了HighDiv的固定策略或后端路由。必须保留同一新宿主、不使用覆盖优先级的对照。

原HighDiv、8个输入、历轮正式记录和冻结基线保持不变。不得重跑HighDiv、追加seed、开启B、增加模目标代理、做LIA赋值移动、在线宏观域分析、不可达排除或MaxSMT。本轮不自动启动新的900秒矩阵。少量独立可达性检查仅用于诊断，答案和模型不注入在线采样器。

不要停留在建议文档；完成代码、受控测试、限定短实验、独立审计、中文报告和非强制Git推送。收益为零也应完成归档。遇到无法支持的语义映射须保留未知，不强造对应。

## 1. 明确原本要实现的软偏好

### 1.1 四类信息必须分开

| 类别 | 例子 | 是否可被偏好推翻 |
|---|---|---|
| 原始问题的硬约束 | 原公式F、用户真实给定的限制 | 不可 |
| 本次调用真实外部assumptions | 非采样器产生的必要条件 | 不可 |
| 采样器继承的旧模型值 | HighDiv从m_ls抽取的x=c | S阶段是低优先级参考，不再作为assumption |
| 覆盖需求 | 某节点某位只见0，希望1 | 可尝试、可放弃，不要求全部满足 |

普通分支中的赋值也不是可随时覆盖的可变参数。在当前分支已经传播赋值的literal不能被直接反向写入；只能经过正常冲突、回溯和后续搜索改变。若求解器沿早先选择已找到合法模型，不承诺再为每一个较晚偏好搜索一遍。

### 1.2 位状态保持原语义

- 两侧未见：不设置位值偏好；首次观察可以更新历史。
- 只见0：偏好1。
- 只见1：偏好0。
- 两侧都见：不再给予该位覆盖奖励，不固定该位。

所有合法、不同、及时交付的模型沿用现有接纳规则。重复观察不算新增观察；covered仍必须见过两侧。官方短路访问和低64位语义不变。

### 1.3 一个必须通过的例子

原公式 `(or (= x 0) (= x 10))`，已有观察来自x=0，希望x的bit1为1（位号从0开始）。

- 原生决策为`x=10`时，可优先true。
- 原生决策为`x=0`时，可优先false：这是避开一个确定违背目标值的分支，不是声称`x!=0`单独蕴含bit1=1。
- 若x=0只是旧模型参考，可以违背参考。
- 若原公式或真实外部条件强制x=0，必须返回合法解或合法求解状态，不能破坏硬约束。
- 若另一个偏好与本目标冲突，允许正常回溯放弃其中一个；不要求两者都实现。

## 2. 已核对的源码事实与本轮新设计

现有`HighDiv/src/sampler/liasampler.cpp::LiaSampler::hybrid_sampling()`从m_ls选择部分值，建立`assertions_vector`，调用`cdcl_solver.check(assertions_vector)`。这些值在该次检查中是硬assumptions，不是相位偏好。

现有`src/round2/a_context.inc::apply_A_phase_hint()`只调整原生已选变量的相位。当前评分通过`rule.one & rule.want_one`、`rule.zero & rule.want_zero`累计正向支持；没有对应的“相位一旦兑现便直接违背目标值”的评分项。

现有`include/round2/a_shared.hpp::canonical()`支持直接结构和线性规范化，但没有完整覆盖第三轮已验证的复合门等价。第三轮证明两个复合门与原式`not(x=0)`等价；代表来自coverage version=0，不能因此声称有实时需求。

以下新增类/函数都是本轮拟实现接口，不是现成Z3 API。按实际编译结构调整文件位置，但应保持模块职责与验收条件。

## 3. M阶段：只修复语义对应

### 3.1 修改位置

独立新文件/命名空间保存实现，避免改变历史重放：

```text
include/round4/semantic_correspondence.hpp
include/round4/preference_types.hpp
src/round4/a_context.inc
scripts/patch_round4_z3.py
tests/round4/test_semantic_correspondence.cpp
```

在`canonical()`或独立规范化层增加有界、只读、精确的等价规则：

```text
or(not(t <= c), not(t >= c))  <=>  not(t = c)
and(t <= c, t >= c)          <=>  t = c
```

允许孩子交换、已有NOT极性和等号换边；必须确认两边是同一精确数值项和同一常数。不能对不相等的上下界套用此规则。规则可参数化t、c，不允许按xH519等实例变量名特判。

这是直接逻辑等价化简，不是推导有限域或宏观可行域。不得利用原公式本身不相容而得到的空真验证为错误规则背书。

### 3.2 声明与极性

保留原声明身份、类型、skolem区分、跨manager安全IR和正负极性。新增匹配必须记录：

```text
native_expression_fingerprint
original_node_id / original_expression_fingerprint
mapping_rule
canonical_negated
equivalence_scope
coverage_version
```

对于只能在实际converter定义下成立的关系，保存该定义的真实来源与作用域。不根据名字猜测；不能将一个有条件对应升级为无条件等价。

### 3.3 测试和机会核验

先对通用模板、正负数、交换顺序、反例边界、严格比较和极性做受控测试；有限独立XOR检查只用于验证规则，不进入线上。

M阶段保持旧HighDiv固定条件、相位评分、relevance、候选顺序、64决策窗口、4建议额度和CCSS不变。

新增漏斗：

```text
新规则匹配
→ coverage_version > 0
→ 该原节点当前只见单侧
→ 当前原生literal未赋值
→ 原生确实选择了它
→ 正向支持分数非平分
→ 给出/改变相位
→ 理论参与
→ 模型值
→ 官方Reach与新增covered
```

首查询的映射只作接入证据。已覆盖、两侧未见、没有被原生选中、超出窗口分别计数。不得把“匹配次数”当“有效指导次数”。

### 3.4 不设置错误的后续门槛

在诊断中分别报告：

- `F + G`是否可行；G是精确观察目标。
- `F + inherited_assumptions + G`是否可行。

第二项不可行不能被解释为目标在新算法中不值得尝试，因为S阶段正是要取消这些继承值的硬性质。

如果新增映射没有产生需求，停止扩大映射规则，不自动放宽窗口。S阶段仍可使用第三轮已有的4个“F+G可行、被继承固定阻塞”的真实见证验证新语义；不得硬编码这些见证答案到在线评分器。

## 4. S阶段：继承值降级成参考，覆盖偏好优先

### 4.1 宿主入口改造

把m_ls中选取历史值的过程抽成新函数：

```cpp
InheritedReference collect_inherited_reference(
    const z3::model& last_ls_model,
    const OriginalDeclarations& originals,
    std::mt19937& highdiv_rng,
    double selection_rate);
```

保持原有选取条件、选择率0.5、遍历和随机数调用顺序；只记录原变量的精确值和来源，不构造`x=c`的新Z3表达式用于本轮check。每次调用的选择列表和RNG来源保存摘要。

再明确分开：

```cpp
struct QueryInputs {
    HardAssumptions user_hard;       // 原本就真实必须满足的条件
    InheritedReference reference;   // 采样器历史启发式，可放弃
};
```

在M模式保留旧assumptions行为；在S模式，只有`user_hard`进入`check(assumptions)`。当前项目若没有用户外部assumptions，就对已含原公式F的solver调用普通check。继承参考走sidecar，不走assumption、assertion或新的代理。

必须记录`hard_assumptions_count/hash`与`reference_count/hash`。不可根据条件长得像`x=c`就删除；只有来源明确为采样器m_ls继承选择的条件可以降级。

### 4.2 路由变化是算法后果，必须正面报告

去掉非空assumptions可能改变combined_solver自然选择的后端。允许这种新模式的自然路由变化，必须记录；不得通过dummy assumption、push/pop或ignore_solver1强制伪造与旧路线相同。

S_ref与S_cov必须共享相同的参考降级、接口、自然路由规则，才能比较覆盖优先级的增量。不能将S_cov相对旧HighDiv的一切差异归于覆盖评分。

仍保留完整HighDiv的CDCL/CCSS混合循环、局部搜索实现、正常模型恢复、模型交换与输出规则。明确承认被修改的是其中的“历史模型硬固定”策略。

### 4.3 在现有literal上使用参考，不重新实现B

新增纯只读函数：

```cpp
std::optional<bool> evaluate_reference_phase(
    const ExistingNativeAtom& atom,
    const SemanticCorrespondence& mapping,
    const InheritedReference& reference);
```

只在该已有原子的必要自由变量可以由参考值或已验证的原始语义恢复时，计算它在参考赋值中的真值。使用精确整数。

未给定值、内部辅助声明无可靠来源、映射不完整时返回`nullopt`。不能补零，不能额外求解，不能追加`x=c`的atom来获得偏好。不能把部分参考赋值假定为一个完整合法模型。

参考偏好只是低优先级的先试方向；即使参考所有值来自一个合法旧模型，部分参考与覆盖偏好合起来仍可能不可满足，允许正常回溯。

## 5. 覆盖相位评分：支持目标，也避免确定违背目标

### 5.1 保留正向支持，增加直接反向证据

对一个已有原子p，分别考察p=true/false。只使用当前已验证的直接语义规则，维护两个计数：

```text
support[p,phase]：该相位若兑现为模型事实，将给出目标期望位值的需求数。
block[p,phase]：该相位若兑现为模型事实，将给出相反位值、排除目标值的需求数。
```

注意：support是位值层信息，未额外证明Reach时不声称保证观察覆盖。block也不是全局不可达证明，不能用来永久删除需求。

对规则的位掩码：

```text
support_one  = known_one  & want_one
support_zero = known_zero & want_zero
block_one    = known_zero & want_one
block_zero   = known_one  & want_zero
```

按原`(node,bit,desired)`去重。对没有事实支持的phase记未知，不凭空补足。

关键例子：

```text
p = (x=0)，希望x.bit1=1。
p=true：support=0，block>=1。
p=false：对应位未知，support=0，block=0。
```

可以因此偏好false，但日志必须记为`avoid_direct_blocker`，不记为保证命中。

### 5.2 冻结一个无需调权重的优先顺序

S_cov第一版比较两个相位的字典序：

```text
(support_count, -block_count)
```

先偏好可以直接支持更多需求的相位；正向支持数相同再避开明确排斥需求的一侧；完全相同则使用参考相位，再无参考则采用原生相位。

不要采用未经分析的`support-block`总和：大量未知可达性的高位缺口可能使一个能补齐少量真实缺口的值被全部罚掉。即使采用本版字典序也不保证全局最优；它只是事前冻结的局部规则。

统一顺序：

```text
硬约束传播/已有赋值
    > 覆盖相位建议
    > 继承参考相位
    > HighDiv原生相位
```

原生guess仍按正常顺序调用，后面只在同一仲裁入口覆盖返回相位，不让两个回调相互覆盖。

### 5.3 配额、重复和不保证事项

保持每次外层check前64次普通决策和最多4次覆盖建议，跨回溯、tactic叶子、fallback共享。参考建议也只在该64次观察窗口中使用，不无限遍历。

同一个`(native_key,phase,target,advice_kind)`在本次check不反复主动引导。`avoid_direct_blocker`不得把一个需求永久标为“已实现”，也不能因此禁止后面不同原子对同一需求提供正向支持。所有建议仍受4次总额度约束。

已经传播赋值的literal不能强行反转；原始强制值不可推翻。不能因为希望成立就重开分支到成功为止。不执行最大覆盖优化。

A仍不更换原生决策变量。因此它不能承诺每一个缺口都会在本次check被尝试。若缺口没有对应的已有选择，保持未知并回退原生搜索，不偷偷开启B。

## 6. 理论参与与访问仍须独立验证

本轮先保持既有relevance策略，不把第三轮局部激活自动并入S_cov，也不全局关闭relevancy。

持续保留：

```text
actual internal literal + polarity
→ actual assigned token
→ normal theory/EUF delivery
→ M_leaf
→ M_outer / original projection
→ pure value hit
→ official Reach
→ observed target / new covered
```

支持/排斥计数只有当相位确实成为模型原子事实时才有其语义含义。若S_cov仍只改变不参与理论的Boolean值，必须报告“偏好到理论的链路仍未成立”，不能只报告更多override。

若出现这种断点，本轮可以整理定位证据，但不得不经独立消融就把relevance激活、选择变量重排或B加回来。已知F+G可行并不保证软偏好找到该模型；这是要测量的机制性能，不是可绕过的正确性条件。

## 7. 函数级改动建议

| 原/新增位置 | 本轮职责 |
|---|---|
| `include/round2/a_shared.hpp::canonical()`的R4副本 | 复合界门的精确等价、极性恢复、受限converter对应 |
| `AGuidanceBridge`的R4副本 | coverage demand与继承reference分离；正式提交后更新bit状态 |
| `LiaSampler::hybrid_sampling()`的新副本/补丁 | 区分hard assumptions和sampler reference；M与S分别选择不同策略 |
| 新`evaluate_reference_phase()` | 只读评估已有atom在部分参考中的值，不生成atom |
| 新`score_phase_evidence()` | 正向支持与直接排斥的独立去重计数 |
| `context::apply_A_phase_hint()`的R4副本 | 单一相位仲裁，原生变量不变，覆盖优先、参考其次 |
| 既有sidecar传递 | 两后端、goal、临时SMT生命周期保持；不泄漏到CCSS |
| 独立审计脚本 | 验证hard/reference来源、最终值、Reach与正式covered |

伪代码（新增设计，非现成API）：

```cpp
Advice advise(const NativeDecision& d,
              const QueryGuidance& q) {
    if (!d.ordinary || d.already_assigned || q.disabled)
        return Advice::keep_native();

    // Mapping and evidence routines never mutate live solver state.
    auto mapping = q.correspondence.lookup(d.atom);
    auto reference = evaluate_reference_phase(d.atom, mapping, q.reference);
    auto fallback = reference.value_or(d.native_phase);

    if (!q.coverage_enabled || q.coverage_quota_exhausted())
        return Advice::reference_or_native(fallback, reference.has_value());

    auto evidence = score_phase_evidence(mapping, q.committed_demands);
    if (!evidence.complete || evidence.false_score == evidence.true_score)
        return Advice::reference_or_native(fallback, reference.has_value());

    return Advice::coverage(evidence.best_phase(), evidence);
}
```

真实实现须在进入此函数前/内部检查64决策窗口、剩余显式成本与暴露成本，延续现有安全取消契约。图示伪代码省略了计账，不代表可省略预算。

## 8. 成本与日志

沿用已冻结的显式/干预暴露保护参数，且将参考建议也纳入计账。只要覆盖或reference任一建议实际改变原生相位，都计入该整次外层check的保守暴露；同相位只记录机会，不作为override。

暴露是整次被干预查询的成本，不是精确的新增开销；取消/停用不恢复既往学习状态。历史查询重建也不等于内部状态复制。

每个action至少增加：

```text
preference_source: coverage_support / avoid_direct_blocker / inherited_reference / native
hard_assumptions_hash
reference_hash
support_true / support_false
block_true / block_false
native_phase / reference_phase / coverage_phase / effective_phase
coverage_overrode_reference
new_mapping_rule
assignment_token / backtracked / theory_delivery
value_hit / metric_reached / observation_hit / new_covered
```

分别统计`unsupported_mapping`、`missing_reference_value`、`already_propagated`、`no_active_demand`、`same_phase`、`quota_exhausted`、`history_hard_blocker_removed`（仅表示来源降级，不表示目标已变可行）等。

日志使用现有有界缓冲。正式热路径不打印完整表达式。保留模型来源、重复率、无模型check、首模型和整体查询成本，尤其检查软化以后是否大量重复旧模型。

## 9. 必须完成的正确性与机制测试

### 9.1 M阶段

- 两个已知门模板的通用化、非零/负常数、交换顺序和NOT极性。
- 不互补上下界不能被误认成等式。
- 声明同名不同sort/内部辅助身份不得混淆。
- coverage version=0没有取值建议；两侧未见/已覆盖不计分。
- 新映射不开启时，受控原生轨迹保持已有回归。

### 9.2 S阶段

1. `x=0 or x=10`，参考x=0、希望bit1=1：分别在原生选中`x=0`与`x=10`时验证建议方向，合法模型可覆盖目标。
2. 原公式额外强制x=0：偏好可被放弃，合法性不变，不死循环。
3. 真正的外部assumption强制x=0：不能被reference软化代码删除。
4. 两个单独可行但联合不可行的希望：例如x属于0、1、2，同时希望bit0和bit1为1；正常返回合法解，允许仅完成部分需求。
5. 正向支持与避免排斥分开：`x!=0`不能被审计器当作必然bit1=1。
6. 已被传播的literal不强行反向赋值；回溯后新token与旧token不混用。
7. reference缺值时不补零、不追加新atom；完整原式仍由求解器正常检查。
8. S_ref和S_cov采用相同的硬条件与自然路由；只有覆盖优先规则不同。
9. B计数、指导新断言、新代理、新相关性标记、新LIA移动均为零。
10. 有限原变量赋值逐个核对投影保解；原公式UNSAT不能因偏好变SAT。
11. CCSS隔离、goal跨manager、取消、异常、pop/reset、sidecar清理全部回归。
12. 参考偏好变化不得伪装成原生随机数保持所有轨迹不变；只保证未干预的前缀不额外消耗原生RNG。

Release及ASan/UBSan通过。沿用已核实的精确上游泄漏例外，不扩大抑制。

## 10. 有限实验矩阵

所有新运行seed=0。既有HighDiv基线只读取。先执行M，冻结结果，再执行S；不混合提交后挑赢家。

### M：映射单因素

SMT_random、SMT_real、convert × `{M_observe, M_apply}` = 6次短会话。

- M保持旧继承assumptions和旧正向支持评分；只有映射规则变化。
- 每会话最多60秒；两个主实例最多8次CDCL，convert最多32次CDCL。
- 正常CCSS模型仍输出并更新正式观察；observe不修改相位。
- 记录新映射是否发生在版本>0且有需求的时刻。

### S：新软参考宿主下的覆盖增量

同三实例 × `{S_ref, S_cov}` = 6次短会话。

- S_ref：采样器继承值变软参考，无覆盖优先级。
- S_cov：相同软参考宿主，启用第5节冻结的support/avoid规则。
- 保持与M相同的会话上限、seed、采样接纳和官方评测。
- 全部公式、输入hash及选择列表归档；不基于结果追加seed/预算。
- M与S之间的差异包含硬参考软化与自然路由变化，不把差值归为纯覆盖作用。

第三轮4个已证明被继承固定阻塞的目标只作为有限机制验收清单：验证新模式未把继承值作为硬条件、目标是否实际遇到并被命中。它们的oracle模型不成为启动样本，oracle答案不指导线上目标优先级。

可以利用16逻辑CPU并行独立任务，先后阶段不能交错，计时阶段不编译/压缩/审计。这里是短机制实验，不基于不同负载下的墙钟差宣称性能优势，也不宣称同状态因果对照。

## 11. 报告与去留

本轮必须分别回答：

1. 新映射是否实际关联了历史单侧需求？若没有，缺口在哪里？
2. 软化的条件是否全部来源于采样器继承，而非原式/真实外部限制？
3. S_cov是否比S_ref更常实现其选定的可观察缺口？
4. 是否出现真实实例完整链：缺口→已有选择→理论→模型→官方访问→新增covered？
5. 是否只是reference软化造成不同轨迹，而覆盖规则没有额外价值？
6. 是否出现重复模型增加、理论Unknown、路由丢失、观察成本或吞吐明显退化？

分类决策：

- 仅匹配数增加，没有需求：映射工程完成，机制机会未建立。
- 需求存在，但原式全局不可行：如实报告，不在本轮永久删除。
- 原式可行、M被继承条件阻塞，S真实命中：建立软化语义的局部机制证据。
- S_ref与S_cov都改善但差别小：软化有线索，覆盖优先额外价值未建立。
- S_cov有真实目标命中但完整采样更贵：完成机制证据，仍不宣称性能提升。
- 仍是Boolean值未成为理论事实：保留具体断点；不自动增加relevance/B来补救。

有正链也不自动进入16项900秒矩阵。先冻结报告、明确成本与模型供给，再单独决定正式性能确认；真正的性能目标仍是同条件下优于完整HighDiv，而不是只比某个退化版本好。

## 12. 交付与上传

至少提交：

```text
docs/round4_plan.zh.md
docs/round4_mapping_and_soft_reference_results.zh.md
configs/round4.json
manifests/round4_short_plan.json
include/round4/
src/round4/
patches/round4/
tests/round4/
results/round4/analysis/
results/round4/BASELINE_UNCHANGED.json
archives/round4/（恢复说明、分片与成员哈希）
```

M、S、计分/审计修复分别提交。所有失败、Unknown、零触发、缺映射、重复模型和不支持情况保留。

实际推送到用户既有仓库，使用本地已有凭据，非强制推送，核对远端SHA。不要提交密钥、编译目录、虚拟环境或伪造上传成功。

## 13. 资料与证据边界

- SamplingCA，Algorithm 4 / Section 3.4.1：参考赋值规定每个被选未赋值布尔变量的先试值，另一值仍可在递归搜索中尝试。论文没有实现本项目的LIA原AST位映射、HighDiv继承值软化或本轮support/avoid评分；这些是这里提出的新设计。
- HighDiv固定源码：
  `https://github.com/laigroup/HighDiv/blob/f2c6e1756b13281d96cbf90a8bd940129e56cce4/HighDiv/src/sampler/liasampler.cpp`
- 当前A评分：
  `https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fa68a9996a48cc2251ab2b8d9315da44606825af/src/round2/a_context.inc`
- 当前规范化：
  `https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fa68a9996a48cc2251ab2b8d9315da44606825af/include/round2/a_shared.hpp`
- 第三轮结果：
  `https://github.com/ChenKaichen-SCUT/guided_sampler/blob/fa68a9996a48cc2251ab2b8d9315da44606825af/docs/round3_semantic_diagnosis.zh.md`

本文件是下一轮实施方案，不是已经执行的代码修改或实验结果。
