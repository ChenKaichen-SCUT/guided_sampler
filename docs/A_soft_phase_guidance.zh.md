# A 的软相位指引：第二轮机制与边界

软相位的实际赋值位于 `src/round2/a_context.inc::context::apply_A_phase_hint()`：

```cpp
effective_phase = r.mode == 1 ? native_phase : suggested;
```

`mode=1`是只观察测试模式；正式`a_only_v2`使用`mode=2`。`scripts/patch_round2_z3.py`
把调用放在原`context::decide()`的队列选变量、原生`guess()`和用户传播器处理之后，
原有literal构造、`assign(..., decision=true)`、传播和回溯之前。
`native_var`按值传入；返回值只表示得到建议。原生变量不变，A不恢复/调整变量队列。
特殊phase、量词、用户传播器、已有赋值和无原生候选均不强造决策。

## 观察、直接规则和规范化

`AGuidanceBridge`复用第一轮逐节点精确观察语义；只有正式提交成功后，才根据
`Evaluation::changed`更新反向索引。Bool原子自身的值，以及显式`t=c`为真时t的
低64位，是唯一规则来源。等式为假不推导t的相反位。常量不作为引导目标，官方分母不变。

原生决策处只读规范化`bool_var2expr(native_var)`，再反查整个当前索引，
不使用旧8位窗口。`include/round2/a_shared.hpp::canonical()`使用精确大整数、
NOT极性、等号交换、线性常量合并和整数严格比较规范化；在宿主数据中构建键，
不构造交换等式或新Z3 AST。有限操作/深度/时间额度未完成时整次拒绝建议。
原变量按symbol种类、名字和sort识别；内部skolem声明使用独立前缀，不能冒充原声明。
请求限定当前公式/solver/check，跨manager只传规范IR和整数节点ID，不传AST裸指针。

每相位支持以原节点的one/zero位掩码去重。已覆盖和两侧未见都不计分；
平分保留原生相位。一次外层check共享前64个普通决策、最多4次建议（含同相位），
同一DemandId最多建议一次；回溯、重启、fallback或新的tactic内核不重置。

## 元数据、路由和生命周期

A专用C入口`Z3_solver_set_A_guidance()`接收本项目固定C++ ABI的共享索引引用。
库复制shared_ptr所有权，不持有宿主栈地址；外层查询期间索引只读，清理后才能更新。
`combined_solver`把非逻辑请求交给两端，保留原路由判断。
`tactic2solver`把sidecar附在goal上，goal复制、子goal和跨manager翻译保留它；
逻辑reset不结束外层查询，API clear的close标记撤销旧sidecar，避免复用污染。

持久`smt_solver`及`smt_tactic`创建的临时内核都用RAII attach/detach；
`check()`和`setup_and_check()`使用相同生命周期。每个内核独立缓存并持有表达式引用，
外层配额和统计共享并由互斥量保护。内部多线程SMT的另一路复制入口明确禁用A；
公共goal并行分支使用只读IR和共享配额，受控测试覆盖跨manager传播。

CCSS的宿主solver不发送sidecar；即使误传到`m_ls_sampling`内核也拒绝A。
SAT叶子和预处理直接决定结果的情况如实记录，不改变路由来获得SMT决策。
实际tactic子阶段、叶子、入口和未介入原因分别记录；“已注册”不等于“实际改相位”。

## B 完全隔离

本轮从冻结上游新副本应用A补丁，没有应用第一轮B补丁。
A桥接对象不构造`TargetEncoder`、`ReachBuilder`、encoded缓存或B注册表。
A不调用add、push/pop、internalize、mark_as_relevant、额外check或phase缓存接口。
注册前后断言和布尔变量数快照相等；原生搜索之后创建变量属于原实现。
旧B源码仅为历史重放保留，不在第二轮入口中启用。

## 回溯、命中和成本

每次建议先保存有限的typed事件，查询结束再序列化；不在决策热路径打印表达式。
assignment token、正常unassign钩子和后续重赋值区分原赋值撤销、相反重赋值、
同相位重赋值和最终原子真值。撤销不是不可达证明。
最终命中只关联同一次CDCL查询的正式模型，分别记录原节点是否访问、期望位、
提交前缺口和该目标的新covered位。随后CCSS的收益不归给该A事件；整个模型增益单列。

显式观察/索引/注册/绑定/回调/日志成本单列，预算45秒。
发生真实override后保守计入整次外层check的墙钟暴露，累计预算45秒。
它是改变过的查询成本，不是精确的额外开销，两类时间不能相加当总耗时。
首次override前检查剩余额度；随后在原有安全取消检查点退出，sticky标志阻止后继fallback。
专门的`guidance_exposure_limit`和原始取消原因都保留；不可分操作的超额也报告。
同相位建议及observe模式不消耗override暴露。

停用后不再更新索引或注册请求，不继续逐决策诊断；原式验证、去重、输出和收据继续。
在线覆盖停用后的增量记为缺项，由离线冻结官方类补全。已有合法学习和phase历史保留，
不声称恢复为从未引导的HighDiv，也不声称所有查询终止行为完全不变。

固定设置见`configs/round2_a.json`；旧8位窗口的损失不能由第一轮缺失的日志补造。
静态exact分类以目录代表表达式的规范结构为准，其他等价原形记为normalized；
未匹配不冒称已经证明被消元。成本/命中和完整性能须以正式报告为准。
