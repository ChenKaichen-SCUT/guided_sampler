# 接入与测量差异

上游逐文件 Git blob 与 SHA-256 见 manifests/upstream.json，全部 2935 文件匹配指定提交。

1. `solver/solver.h` 增加 solver 专属强引用元数据；`combined_solver` 只向 solver2 转发，未改 `m_inc_mode`、push、assert、assumption 路由判断。
2. `smt_solver::check_sat_core2` 在自然调用时将计划传给自己的 context，RAII 在正常、取消与异常退出时清除当前计划。不会装到同一 context 的另一个 solver。
3. `context::check` 在 `internalize_assertions` 后、`add_theory_assumptions/init_assumptions` 前内部化 B 的定义。这是基层安全边界；assumptions 随后建立，传播仍由原生 init/search 路径执行。注册不增加必真 assertion。
4. `context::decide` 保留原生 case split queue 与 `guess` 调用。原生 user propagator 具有优先权。普通决策经唯一 broker 后走原 push scope / decision assign；B 替换原变量时调用 queue 原有 `unassign_var_eh` 恢复未使用的候选。
5. 内核 registry 强引用表达式，每次使用重新查询 internalized/literal，不把裸 bool_var 跨 pop/reset 保存。尝试集合和普通决策序号属于外层 query epoch，restart 不重置。
6. A 静态目录以原节点反向索引到原 Bool 原子、显式常量等式及交换等式。每个窗口只更新当前目标对应项并计分；等式 false 从不产生 Int 相反位结论。
7. `observation.hpp` 显式栈建立和求值原 DAG，精确整数只在观察时截低64位。Reach 缓存父边和短路前缀，编码超过4096新中间节点时保留 incomplete。
8. HighDiv 原 hybrid、预处理、模型恢复、LS seed 和固定变量比例未改。共同差异为：明确 unlimited、严格截止、原变量投影与去重、独立 model 快照验证、收据和查询日志；不足1秒不向 LS 传整秒0，保留 CDCL 余时使用。没有新增完整模型阻塞。
9. baseline 不创建 GuidanceBridge、原 AST 观察目录或目标。guided-off 走同一共同测量分支。B 目标构造、目录、写日志与在线反馈的显式成本计入 guided 会话，达到5%停止新增指导。
10. `samples.raw` 写入完成后，prepare、commit、confirm 收据形成可审计交付事务；正式文件按原序复制完整、及时、合法、不同的交付，不按覆盖筛选。

辅助定义不会进入样本身份或 LS→CDCL 固定变量列表。模型 hash 用 FNV-1a64 作日志索引，实际去重比较完整带长度和 sort 的 key，避免 hash 碰撞导致误计数；文件证据统一使用 SHA-256。

工作副本在 `/tmp`，项目 `worktrees/` 为本机入口；二者都不提交。正式二进制 RPATH、运行加载库、哈希独立保存。

共同诊断另外记录 `combined_solver` 实际调用的后端及每次 check 序号。
`routes.jsonl` 由真实分支发出，离线与 `queries.jsonl` 及指导统计交叉核对，
并生成 `queries.audited.jsonl`；不把接口安装成功等同于进入 SMT 决策。
新模块达到显式成本上限后仅保留零干预的历史代理诊断，使用表达式集合做常数时间查询。

基线和新方法均保留重复/非法候选的完整 raw 行与 reject 收据；重复不提交观察状态。
检测版测试含一个精确的既有上游泄漏例外，见 `sanitizer_exception.zh.md`。
