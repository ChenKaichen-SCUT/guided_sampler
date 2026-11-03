# convert 原预算交付与 real 方向阻塞：限定离线结果

本轮完成固定代码修改、Release/ASan/UBSan 正确性及原生隔离验证、4 个 convert 冷探针、22 条正式离线序列和 4 个 real 诊断 worker。43 个源模型共重放 518 个正式事件；没有新真实采样、真实 solver check、HighDiv 重跑、在线短会话、900 秒矩阵、追加 seed 或 B。基点 `2dde70ab203009afdb07e4337eb3cdd637906704`，源码冻结 `9558a4333fd2b2399682f4dbaf53ae20137a95fd`，分支 `refinement-budget-delivery`。

任务 A 分层：A0=True，A1=False，A2=False，A3=False（共同位置 []），A4=False。任务 B：B1=True，B2=True，B3=False。整体在线算法仍不自动 Go；`historical_cpu_credit_proven=false`，不能声称已满足原生 CPU 10% 双信用或低于重新求解成本。

## 1. 实现与验证

V0 保留 ValueCache；V1 以一次行槽、epoch/touched 做稀疏全等式验证；V2 在确定旧方向池后批量传播四字位集；V3 按完全相同的影响签名分组，并在事件入口对当前实际输出历史事务式同步 covered 分数。全部强制等式义务保留；未触及的行因方向支持与行系数无交集而结构上为零。x-x、未选分支、共享 DAG、Bool 和原 AST 身份均保留。hard AST 使用自己的影响节点空间。

四配置正式实验统一 FirstCovered、96/18 ms 算法软截止和 100/20 ms 最终上限；这项停止策略是显式算法变化，缓存/稀疏/位集/精确评分属于等价成本修复。AuditAll 探针关闭早停；固定工作量合成测试也关闭时限及早停，逐项比较元数据、方向、affected、分数、顺序、目标、区间、参数、赋值、实际观察、保护、得分和选择。不能将四配置差值直接归于 FirstCovered，也没有额外正式停止消融来量化其独立性能贡献。

两种构建通过 244612 算术、1356 模命中、7938 域点、4 方向系统、32 官方观察检查；新增独立核验 304 次合成候选、17 份完整域证书，68 份损坏证书全部拒绝。测试覆盖 epoch 清理取消恢复、深链/共享 DAG、评分身份/取消发布、真实 hard 条件、17+4 ms 收尾回退、19 ms 搜索软截止、二向协调/整数取整/远 OR 分支/三向才可移动例。四配置原生隔离均实际发生替代，保持完整 map、m_ls、RNG、参考、反馈、路由和原生计数；关闭行为与保存的基线一致。

真实独立审计：官方访问核验调用 804 次，涉及 114 个不同公式—完整赋值对象；完整候选核验 256 次，完整域证书 192 份。以上与 43 个源模型区分。22 条正式输出及原生序列各运行冻结官方 wire_coverage 脚本；完整输出前缀都保留原生观察。

## 2. 冷预处理与重复工作

| 轨道/实例 | 配置 | 重复 | CPU ms | 墙钟 ms | 冷合格 | 状态 |
|---|---|---|---|---|---|---|
| probes/convert | V0 | None | 132.339 | 136.235 | True | completed |
| probes/convert | V1 | None | 89.273 | 93.038 | True | completed |
| probes/convert | V2 | None | 92.758 | 96.276 | True | completed |
| probes/convert | V3 | None | 97.198 | 100.611 | True | completed |
| offline/convert | V0 | 1 | 97.372 | 98.170 | False | wall_budget_exhausted |
| offline/convert | V1 | 1 | 85.660 | 91.112 | True | completed |
| offline/convert | V2 | 1 | 90.499 | 94.307 | True | completed |
| offline/convert | V3 | 1 | 98.747 | 102.256 | False | wall_budget_exhausted |
| offline/convert | V2 | 2 | 101.353 | 102.293 | False | wall_budget_exhausted |
| offline/convert | V3 | 2 | 99.529 | 104.918 | False | wall_budget_exhausted |
| offline/convert | V0 | 2 | 97.576 | 98.123 | False | wall_budget_exhausted |
| offline/convert | V1 | 2 | 85.749 | 89.406 | True | completed |
| offline/convert | V3 | 3 | 99.850 | 103.208 | False | wall_budget_exhausted |
| offline/convert | V0 | 3 | 97.105 | 98.082 | False | wall_budget_exhausted |
| offline/convert | V1 | 3 | 85.053 | 88.729 | True | completed |
| offline/convert | V2 | 3 | 91.017 | 95.494 | True | completed |
| offline/convert | V0 | 1 | 97.089 | 97.900 | False | wall_budget_exhausted |
| offline/convert | V3 | 1 | 97.998 | 101.845 | False | wall_budget_exhausted |
| offline/convert | V3 | 2 | 98.397 | 101.838 | False | wall_budget_exhausted |
| offline/convert | V0 | 2 | 97.033 | 97.719 | False | wall_budget_exhausted |
| offline/convert | V0 | 3 | 97.148 | 97.873 | False | wall_budget_exhausted |
| offline/convert | V3 | 3 | 98.205 | 102.099 | False | wall_budget_exhausted |
| offline/SMT_random | V0 | 1 | 12.735 | 13.371 | True | completed |
| offline/SMT_random | V3 | 1 | 9.408 | 9.886 | True | completed |
| offline/SMT_real | V0 | 1 | 38.181 | 39.568 | True | completed |
| offline/SMT_real | V3 | 1 | 39.928 | 41.931 | True | completed |


| 配置 | 完整行槽初始化 | 全行扫描次数 | 触及行数 | 乘加数 | 位集 OR | affected 字节槽 |
|---|---|---|---|---|---|---|
| V0 | 247791 | 547 | 0 | 1922 | 0 | 838300 |
| V1 | 453 | 0 | 961 | 1922 | 0 | 838300 |
| V2 | 453 | 0 | 961 | 1922 | 60732 | 1204544 |
| V3 | 453 | 0 | 961 | 1922 | 60732 | 1204544 |


| 配置 | 阶段 | exclusive CPU ms | exclusive 墙钟 ms | 完成/未完成 |
|---|---|---|---|---|
| V0 | BuildAffected | 14.792 | 14.793 | 1/0 |
| V0 | CollectEqualities | 3.332 | 3.332 | 1/0 |
| V0 | CompileTerms | 6.627 | 6.907 | 1/0 |
| V0 | Components | 7.150 | 7.151 | 1/0 |
| V0 | CopyAst | 0.684 | 0.684 | 1/0 |
| V0 | DependencyIndex | 36.557 | 36.559 | 1/0 |
| V0 | Elimination | 6.790 | 6.795 | 149/0 |
| V0 | Metadata | 3.430 | 3.430 | 1/0 |
| V0 | SerializeResult | 6.539 | 9.652 | 1/0 |
| V0 | VerifyDirections | 45.418 | 45.416 | 547/0 |
| V1 | BuildAffected | 13.740 | 13.741 | 1/0 |
| V1 | CollectEqualities | 3.182 | 3.182 | 1/0 |
| V1 | CompileTerms | 6.095 | 6.353 | 1/0 |
| V1 | Components | 7.326 | 7.326 | 1/0 |
| V1 | CopyAst | 0.777 | 0.777 | 1/0 |
| V1 | DependencyIndex | 36.817 | 36.819 | 1/0 |
| V1 | Elimination | 6.682 | 6.687 | 149/0 |
| V1 | Metadata | 3.530 | 3.530 | 1/0 |
| V1 | SerializeResult | 6.956 | 10.172 | 1/0 |
| V1 | VerifyDirections | 3.522 | 3.517 | 548/0 |
| V2 | BuildAffected | 60.639 | 60.650 | 1/0 |
| V2 | CollectEqualities | 3.075 | 3.075 | 1/0 |
| V2 | CompileTerms | 6.250 | 6.341 | 1/0 |
| V2 | Components | 0.764 | 0.766 | 1/0 |
| V2 | CopyAst | 0.750 | 0.749 | 1/0 |
| V2 | DependencyIndex | 0.001 | 0.001 | 1/0 |
| V2 | Elimination | 6.712 | 6.715 | 149/0 |
| V2 | Metadata | 4.679 | 4.679 | 1/0 |
| V2 | SerializeResult | 6.283 | 9.427 | 1/0 |
| V2 | VerifyDirections | 3.105 | 3.102 | 548/0 |
| V3 | BuildAffected | 57.893 | 57.896 | 1/0 |
| V3 | BuildScoreIndex | 7.547 | 7.547 | 2/0 |
| V3 | CollectEqualities | 3.067 | 3.067 | 1/0 |
| V3 | CompileTerms | 6.005 | 6.105 | 1/0 |
| V3 | Components | 0.695 | 0.695 | 1/0 |
| V3 | CopyAst | 0.707 | 0.707 | 1/0 |
| V3 | DependencyIndex | 0.000 | 0.001 | 1/0 |
| V3 | Elimination | 6.590 | 6.594 | 149/0 |
| V3 | Metadata | 4.549 | 4.549 | 1/0 |
| V3 | SerializeResult | 6.536 | 9.553 | 1/0 |
| V3 | VerifyDirections | 3.072 | 3.069 | 548/0 |


| 配置 | 方向 | affected 条目 | 签名组 | 组—方向条目 |
|---|---|---|---|---|
| V0 | 256 | 209575 | 不适用 | 不适用 |
| V1 | 256 | 209575 | 不适用 | 不适用 |
| V2 | 256 | 209575 | 不适用 | 不适用 |
| V3 | 256 | 209575 | 533 | 32554 |


同一新二进制、同一记录策略的 V0–V3 才是本轮配对对照。上轮 ValueCache/Shared 单次 convert 依赖分别 36.277/4.735 ms、affected 14.085/75.173 ms、完整预处理 124.314/148.848 ms，只作为历史背景，不据跨冻结版本的墙钟比值宣称精确加速。表中被截止的工作属于删失，不是完整耗时。方向验证总行、槽、触及行与乘加分别记录；位集和 affected 内存为容器槽容量，完整峰值看 worker RSS。

## 3. 排名、候选与交付

| 序列 | 位置 | 排名 CPU ms | 同步节点 | 变化bit | 脏组 | 评分更新 | 评价 | 首完成 CPU ms | 首保护增益 CPU ms | ready CPU ms | 事件 CPU ms | 实际交付 | 停止/拒绝 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| convert_V0 | 1 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.465 | 0.484 | False | first_output_identity |
| convert_V0 | 2 | 35.214 | 0 | 0 | 0 | 0 | 16 | 81.359 | 未知 | 543.105 | 543.140 | False | wall_budget_exhausted |
| convert_V0 | 3 | 35.098 | 0 | 0 | 0 | 0 | 16 | 81.554 | 81.652 | 542.198 | 542.231 | False | wall_budget_exhausted |
| convert_V0 | 4 | 34.630 | 0 | 0 | 0 | 0 | 15 | 78.648 | 未知 | 537.723 | 537.757 | False | wall_budget_exhausted |
| convert_V0 | 5 | 35.337 | 0 | 0 | 0 | 0 | 14 | 79.292 | 未知 | 470.883 | 470.921 | False | no_strictly_better_candidate |
| convert_V1 | 1 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.416 | 0.434 | False | first_output_identity |
| convert_V1 | 2 | 34.708 | 0 | 0 | 0 | 0 | 16 | 78.988 | 未知 | 543.750 | 543.788 | False | wall_budget_exhausted |
| convert_V1 | 3 | 34.658 | 0 | 0 | 0 | 0 | 17 | 80.664 | 80.769 | 544.816 | 544.849 | False | wall_budget_exhausted |
| convert_V1 | 4 | 34.217 | 0 | 0 | 0 | 0 | 16 | 78.168 | 未知 | 535.504 | 535.540 | False | wall_budget_exhausted |
| convert_V1 | 5 | 34.541 | 0 | 0 | 0 | 0 | 14 | 79.730 | 未知 | 472.465 | 472.497 | False | no_strictly_better_candidate |
| convert_V2 | 1 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.423 | 0.439 | False | first_output_identity |
| convert_V2 | 2 | 35.257 | 0 | 0 | 0 | 0 | 16 | 77.672 | 未知 | 544.313 | 544.349 | False | wall_budget_exhausted |
| convert_V2 | 3 | 35.347 | 0 | 0 | 0 | 0 | 17 | 77.386 | 77.487 | 547.297 | 547.332 | False | wall_budget_exhausted |
| convert_V2 | 4 | 35.373 | 0 | 0 | 0 | 0 | 17 | 77.264 | 未知 | 539.674 | 539.706 | False | wall_budget_exhausted |
| convert_V2 | 5 | 35.716 | 0 | 0 | 0 | 0 | 14 | 77.972 | 未知 | 455.650 | 455.683 | False | no_strictly_better_candidate |
| convert_V3 | 1 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.422 | 0.443 | False | first_output_identity |
| convert_V3 | 2 | 1.863 | 9580 | 0 | 0 | 0 | 18 | 43.907 | 未知 | 547.127 | 547.158 | False | wall_budget_exhausted |
| convert_V3 | 3 | 2.056 | 9580 | 26220 | 207 | 366 | 18 | 44.371 | 44.477 | 550.206 | 550.240 | False | wall_budget_exhausted |
| convert_V3 | 4 | 1.839 | 9580 | 1049 | 10 | 13 | 18 | 43.738 | 未知 | 541.918 | 541.949 | False | wall_budget_exhausted |
| convert_V3 | 5 | 2.203 | 9580 | 4323 | 164 | 313 | 14 | 45.127 | 未知 | 428.834 | 428.865 | False | no_strictly_better_candidate |
| convert_V3_L2_r1 | 2 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.377 | 0.399 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r1 | 3 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.357 | 0.373 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r1 | 4 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.666 | 0.692 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r1 | 5 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.415 | 0.437 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r2 | 2 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.444 | 0.470 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r2 | 3 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.355 | 0.370 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r2 | 4 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.416 | 0.432 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r2 | 5 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.388 | 0.403 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r3 | 2 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.451 | 0.473 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r3 | 3 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.374 | 0.388 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r3 | 4 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.437 | 0.459 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L2_r3 | 5 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.373 | 0.390 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r1 | 2 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.384 | 0.404 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r1 | 3 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.384 | 0.404 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r1 | 4 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.481 | 0.502 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r1 | 5 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.456 | 0.475 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r2 | 2 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.407 | 0.430 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r2 | 3 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.361 | 0.381 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r2 | 4 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.389 | 0.413 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r2 | 5 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.381 | 0.396 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r3 | 2 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.355 | 0.369 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r3 | 3 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.331 | 0.344 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r3 | 4 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.383 | 0.403 | False | preprocessing_disabled:wall_budget_exhausted |
| convert_V3_L1_r3 | 5 | 0.000 | 0 | 0 | 0 | 0 | 0 | 未知 | 未知 | 0.369 | 0.386 | False | preprocessing_disabled:wall_budget_exhausted |


所有首次时间从事件可选工作入口累计，不是候选内部计时；完整原式合法性、官方观察、保护差集和评分先完成，保存赋值/完整观察后才可能交付。序列化、全部候选日志写出、临时对象清理、staging 账本复制、外层记录和回滚均计费。proposal 非最终输出；超时恢复原生交付，再以真实历史运行下一事件。详细每位置 CPU/墙钟、首次方向/参数、全部缺失观察、分数、分阶段成本和尾部见归档 events.json 与 stream.jsonl。

## 4. 22 条正式序列：三次重复全部保留

| 序列 | 完整评价 | 预算可交付 | 实际替代 | 严格 covered 交付 | 终点额外 covered | 可选 CPU/墙钟 ms | 进程 CPU/墙钟 ms | RSS KiB |
|---|---|---|---|---|---|---|---|---|
| convert_V0_L2_r1 | 0 | 0 | 0 | 0 | 0 | 110.590/126.011 | 377.429/421.041 | 25744 |
| convert_V1_L2_r1 | 0 | 0 | 0 | 0 | 0 | 568.630/591.216 | 837.829/886.438 | 31632 |
| convert_V2_L2_r1 | 0 | 0 | 0 | 0 | 0 | 573.452/597.386 | 842.022/895.161 | 33992 |
| convert_V3_L2_r1 | 0 | 0 | 0 | 0 | 0 | 111.426/124.200 | 377.914/419.345 | 43092 |
| convert_V2_L2_r2 | 0 | 0 | 0 | 0 | 0 | 114.381/136.712 | 382.446/433.693 | 45184 |
| convert_V3_L2_r2 | 0 | 0 | 0 | 0 | 0 | 111.516/126.777 | 374.358/414.883 | 45184 |
| convert_V0_L2_r2 | 0 | 0 | 0 | 0 | 0 | 110.198/125.302 | 374.707/414.655 | 45184 |
| convert_V1_L2_r2 | 0 | 0 | 0 | 0 | 0 | 569.553/594.946 | 838.039/887.497 | 45184 |
| convert_V3_L2_r3 | 0 | 0 | 0 | 0 | 0 | 112.167/130.923 | 378.207/421.291 | 45184 |
| convert_V0_L2_r3 | 0 | 0 | 0 | 0 | 0 | 110.518/122.151 | 376.409/412.548 | 45184 |
| convert_V1_L2_r3 | 0 | 0 | 0 | 0 | 0 | 567.509/590.546 | 832.815/882.450 | 45184 |
| convert_V2_L2_r3 | 0 | 0 | 0 | 0 | 0 | 573.388/599.466 | 838.151/888.035 | 45184 |
| convert_V0_L1_r1 | 0 | 0 | 0 | 0 | 0 | 109.520/125.041 | 371.860/412.094 | 45184 |
| convert_V3_L1_r1 | 0 | 0 | 0 | 0 | 0 | 110.462/128.432 | 372.686/419.364 | 45184 |
| convert_V3_L1_r2 | 0 | 0 | 0 | 0 | 0 | 110.486/129.291 | 377.363/421.900 | 45184 |
| convert_V0_L1_r2 | 0 | 0 | 0 | 0 | 0 | 110.219/127.200 | 382.851/453.509 | 45644 |
| convert_V0_L1_r3 | 0 | 0 | 0 | 0 | 0 | 109.887/131.275 | 373.710/421.429 | 45644 |
| convert_V3_L1_r3 | 0 | 0 | 0 | 0 | 0 | 110.276/131.725 | 382.025/432.058 | 45644 |
| SMT_random_V0_L2_r1 | 0 | 0 | 0 | 0 | 0 | 31.833/35.563 | 86.355/113.813 | 45644 |
| SMT_random_V3_L2_r1 | 0 | 0 | 0 | 0 | 0 | 36.233/39.762 | 90.163/114.597 | 45644 |
| SMT_real_V0_L2_r1 | 0 | 0 | 0 | 0 | 0 | 169.551/176.847 | 207.753/234.724 | 45644 |
| SMT_real_V3_L2_r1 | 0 | 0 | 0 | 0 | 0 | 171.869/179.271 | 210.454/236.350 | 45644 |


V0 convert L2 三次合格预处理 CPU 中位/范围 ms：无完成记录；墙钟：无完成记录；未合格 3 次单列，不计完成中位数。

V1 convert L2 三次合格预处理 CPU 中位/范围 ms：85.660 [85.053, 85.749]；墙钟：89.406 [88.729, 91.112]；未合格 0 次单列，不计完成中位数。

V2 convert L2 三次合格预处理 CPU 中位/范围 ms：90.758 [90.499, 91.017]；墙钟：94.900 [94.307, 95.494]；未合格 1 次单列，不计完成中位数。

V3 convert L2 三次合格预处理 CPU 中位/范围 ms：无完成记录；墙钟：无完成记录；未合格 3 次单列，不计完成中位数。

L1 后续历史始终是原生前缀，预算合格仅表示假设可交付；L2 才使用真实预算决定后的输出历史。首模型原样交付。完整前缀曲线在 analysis/audit_v1/prefixes.csv：局部替代 covered 增益与终点差值分开，原生后续可能补齐前缀新增 bit。后续 L2 机会不能强求与旧位置 3 的 +43 完全相同。

旧 +43 只读 fixture 在两种构建的独立审计中均合法、保护 1049 个观察完整、covered 多 43。生产选择器不读此 fixture、不按实例名/位置/方向 186/参数 3 指定快路径。若本轮原预算没有重新找到，fixture 仍不能算本轮发现。

## 5. real 完整域与有限协调诊断

| 位置 | 类别 | 记录 | 完整根域 | 完整证书 | 独立核验 | {0} | 非零域 | 合法见证 | 保护 | 覆盖增益 | B2 | B3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | original | 16 | 16 | 16 | 16 | 15 | 1 | 1 | 0 | 0 | 0 | 0 |
| 2 | combination | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | original | 16 | 16 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | combination | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | original | 16 | 16 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | combination | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | original | 16 | 16 | 16 | 16 | 15 | 1 | 1 | 0 | 0 | 0 | 0 |
| 5 | combination | 32 | 32 | 32 | 32 | 31 | 1 | 1 | 0 | 0 | 1 | 0 |


完整原子算术、节点作用域、完整 Bool DAG 推导和组合逐条结果见 real_blocking.zh.md 与归档证书。合法域先于保护；完整域为 {0} 时，不能把不能移动归因为观察保护。组合结果只对预登记的有限二方向集合有效，失败不能推出没有三向协调、其他模型或全局无解。原池重合方向不算新增组合首次解除阻塞。

## 6. 成本边界、失败与结论限制

每 worker 冷启动清空模型值缓存、重新生成方向池/索引/评分状态，未清操作系统页缓存。正式计时顺序执行、绑定逻辑 CPU 0（物理 core 0，sibling 0–1）；没有与本任务编译/归档/上传/real 诊断重叠，也不宣称宿主完全独占。全部 CPU/墙钟、失败尾部和父进程 wait4/pidfd 成本保留，调度超限没有自动重跑。

末尾成本记录无法计量自己的最终写出；父进程完整 CPU/墙钟补充，不能填 0。摘要序列化单列 summary tail；event postlude 与测量余量单列，临界无法确认时保守回退 budget_eligibility_unknown。容器字节是槽存储与证书保守额度，不是所有 BigInt 动态堆的精确快照；RSS 为整进程高水位。仍缺历史逐模型原生 CPU 信用，没有本轮 oracle，也没有重新求解成本估计。

保留了空组取消检查测试失败、测试 JSON 期望格式错误、构建 -B 触发已有依赖占位目标失败，以及源码仍在复核时被“编译期间源码变化”检查拒绝的构建。均在真实探针开始前修复或完成最终一致构建；失败目录未删除。工具会话重启中断 SAN 审计时，复用已经完成的机制证据，只继续未完成测试；不重跑真实探针。所有正式 worker 尝试目录拒绝覆盖。

全部工件保存在 results/refinement_budget_delivery；可恢复归档、成员 SHA 和验证见 archives/refinement_budget_delivery/RESTORE.md；源/生成文件/二进制/动态库/输入/官方脚本身份见 manifests/refinement_budget_delivery。分支正常提交推送并由 git ls-remote 核对最终完整 SHA，发布收据在 build/refinement-budget-delivery-publish-receipt.json。

## 7. 指引十二项直接回答

1. 稀疏验证在 convert 探针把全行 Big 槽初始化从 247791 降为 453，减少 247338 槽；全行扫描从 547 次降为 0。实际触及 961 行次，乘加仍为 1922，覆盖全部 453 强制等式的数学义务。独立检查器重新算全部行点积，没有忽略未触及行。

2. 共同完成部分及合成固定工作量的 affected 完全相同。V2/V3 消除了传递变量集合，但批量方向位集及输出 affected 仍有大量枚举和预算检查；本轮该阶段分别 60.639/57.893 ms CPU，V1 affected 为 13.740 ms、依赖为 36.817 ms。因此“批量影响必然更便宜”未成立；相比历史 Shared 的 75.173 ms affected 有单次下降，但跨版本不能当严格配对加速。

3. 分组把 209575 个 affected 条目压为 533 个签名组、32554 个组—方向条目，条目比 6.438。宽探针 V3 排名（含同步）约 1.8–2.2 ms；原三配置约 34–36 ms。第一次同步也在约 2 ms 范围，未见它成为当前首要瓶颈。正式 V3 因冷预处理失败而没有事件评分机会，不能把探针温态排名写成正式交付。

4. 四个 AuditAll 探针在位置 3 首次保存保护通过的 covered 增益，CPU/墙钟如下。这个首增益之前已有 9 条目标记录（方向 185 的 8 项及方向 186 的首项），首完整候选本身约 21–23 ms；V3 首增益累计约 44.48 ms。失败的目标探索、保护、排序和缓存从同一入口计时；后续 AuditAll 会继续搜索。其整事件最终日志/清理约 0.44–0.56 秒，不等于首见证时间。

| 配置 | 首增益 CPU ms | 首增益墙钟 ms | 方向 | 参数 | ready CPU ms | ready墙钟 ms | 整事件CPU ms | 整事件墙钟 ms |
|---|---|---|---|---|---|---|---|---|
| V0 | 81.652 | 81.656 | 186 | 3 | 542.198 | 552.663 | 542.231 | 552.696 |
| V1 | 80.769 | 80.774 | 186 | 3 | 544.816 | 554.349 | 544.849 | 554.381 |
| V2 | 77.487 | 77.491 | 186 | 3 | 547.297 | 557.004 | 547.332 | 557.040 |
| V3 | 44.477 | 44.479 | 186 | 3 | 550.206 | 563.025 | 550.240 | 563.059 |


5. 没有原预算内严格增益交付：22 条正式序列完整候选为 0、实际替代为 0。convert 主 L2：V0 三次均在 96 ms 软截止附近停止；V1 三次预处理合格但 26 个后续事件均停在排序；V2 的 r1/r3 预处理合格后也停在排序，r2 在元数据阶段超过总上限；V3 三次均在序列化/收尾超过 100 ms 墙钟。V3 的三次 CPU/墙钟约为 98.747/102.256、99.529/104.918、99.850/103.208 ms，不以 CPU 单边小于 100 ms 冒充合格。

6. FirstCovered 与成本修复必须分开：前者允许第一个合格 covered 候选提前进入收尾，后者保留同一有限搜索顺序。合成测试证明四配置停在同一首个合格候选；正式没有完整候选，故本轮没有测得正式 FirstCovered 收益。探针用 AuditAll，不能把其日志尾部当成 FirstCovered 交付成本，也不能推测若早停就会在 20 ms 内成功。

7. 正式没有前缀新增，全部 L2 终点与原生相同。L1 与 L2 在本轮都实际保持原生输出，未发生“前面替代改变后续历史”的分叉；但实现和合成测试已经验证二者历史隔离。旧 +43 及本轮探针 +43 都没有进入正式连续交付曲线。

8. real 独立复核 64 个完整原方向域：62 个 {0}、2 个有非零点。完整证书说明是原式 Bool 组合的整数可行域限制，发生在保护筛选前；原子具体作用域和整数边界见独立诊断报告。不是靠 t=±1 的有限测试作此判断，也不等于原公式只有一个模型。

9. 预登记 128 个组合请求全部完成：127 个 {0}，1 个非零域。位置 5 的 d9−d117（第 8 条请求，ordinal=7）归一化后不在原池，两个原方向各自确证 {0}，组合域为 {−2500,0}；t=−2500 完整合法。该见证 marginal gain 为 374/385，原生为 308/316，即无保护比较多 66 covered、69 observations，但缺失 13 个 protected 观察，故 B2 通过、B3 失败。没有注入历史。全部其余负结果只限制于这个固定有限集合。

10. 历史逐模型 CPU 信用仍未知；没有真实新 oracle 或重新求解成本。整进程 RSS 不是精确缓存净堆用量；stage trace 未单列首候选之前每个子阶段的独立累计截面，不能从整事件汇总反推其精确拆分。完整 CPU/墙钟及最终成本记录的未归属余额下表单列；全部正式输出都是 native，不存在被当作成功的临界资格未知替代。探针多次超过 500 ms 的不可中断日志尾部保留为超支，算法内候选不能据此称作 500 ms 内完整交付。

11. A0 正确性通过；正式 A1/A2/A3/A4 均未达到，convert 原预算目标 No-Go。real 达 B1（完整证书）及 B2（有限协调解除单方向阻塞），未达 B3；不能用 B2 替代任务 A 的失败。

12. 新真实采样=0、真实 solver check=0、oracle=0、在线实验=0、未登记真实重试=0；4 探针+22 序列+4 诊断均只执行预登记一次。合成隔离沿用现有合成原生 solver 检查来获得实际 CPU 信用，这些不是 benchmark 新采样或真实 oracle；不混入 43 模型。全部失败构建/测试、超时、拒绝和父进程成本保留。

| 正式序列 | 必需 CPU ms | 必需墙钟 ms | 摘要尾部CPU ms | 摘要尾部墙钟 ms | 进程CPU未归属余额ms |
|---|---|---|---|---|---|
| convert_V0_L2_r1 | 239.519 | 239.652 | 2.170 | 8.419 | 7.948 |
| convert_V1_L2_r1 | 240.844 | 240.871 | 1.780 | 3.444 | 9.298 |
| convert_V2_L2_r1 | 242.298 | 242.303 | 1.725 | 2.889 | 6.890 |
| convert_V3_L2_r1 | 240.041 | 240.054 | 1.697 | 2.914 | 6.921 |
| convert_V2_L2_r2 | 240.228 | 240.232 | 1.742 | 8.212 | 8.391 |
| convert_V3_L2_r2 | 236.866 | 236.874 | 1.580 | 2.887 | 6.706 |
| convert_V0_L2_r2 | 238.749 | 238.757 | 1.661 | 8.115 | 6.585 |
| convert_V1_L2_r2 | 241.733 | 241.747 | 1.770 | 9.226 | 7.454 |
| convert_V3_L2_r3 | 240.184 | 240.191 | 1.624 | 8.922 | 6.482 |
| convert_V0_L2_r3 | 240.368 | 240.397 | 1.638 | 3.030 | 6.578 |
| convert_V1_L2_r3 | 238.556 | 238.563 | 1.779 | 8.545 | 7.830 |
| convert_V2_L2_r3 | 238.711 | 238.717 | 1.614 | 8.084 | 7.181 |
| convert_V0_L1_r1 | 236.325 | 236.333 | 1.680 | 8.280 | 6.901 |
| convert_V3_L1_r1 | 236.717 | 236.732 | 1.704 | 8.104 | 6.338 |
| convert_V3_L1_r2 | 241.425 | 241.433 | 1.586 | 8.195 | 6.503 |
| convert_V0_L1_r2 | 244.576 | 244.583 | 1.735 | 8.679 | 7.318 |
| convert_V0_L1_r3 | 236.866 | 236.875 | 1.635 | 8.878 | 6.459 |
| convert_V3_L1_r3 | 246.249 | 246.256 | 1.701 | 8.723 | 6.568 |
| SMT_random_V0_L2_r1 | 38.381 | 38.382 | 0.506 | 1.264 | 4.248 |
| SMT_random_V3_L2_r1 | 38.079 | 38.109 | 0.505 | 1.171 | 3.772 |
| SMT_real_V0_L2_r1 | 26.524 | 26.523 | 0.391 | 1.373 | 3.631 |
| SMT_real_V3_L2_r1 | 26.741 | 26.741 | 0.394 | 1.393 | 3.760 |


进程余额含启动、未分阶段管理开销、最终清理和末条记录自尾部，不能全部归因于某一临界事件。它不是把未知耗时置零的豁免。

## 8. 下一步的证据约束

本轮停止，不追加配置、额度或真实重跑。后续若继续，应首先单因素检验候选专用完整求值的容器/遍历成本：当前首个候选本身已经约 21–23 ms，单靠进一步省排序或预处理无法证明达到 20 ms。可以研究保持两套独立合法性/官方访问校验的稀疏已访问结果表示，但不能借数值缓存替代正式观察，也不能承诺仅这一项就足够。real 的协调方向研究是另一条独立问题，当前见证还需要解决 13 个观察缺失，不能直接加入生产方向池。

## 9. 最终记录补充

原 worker 对首模型或预处理停用事件不执行可选基线评分，保留了 364 条 native_gain=null；它们不是 0 gain。analysis/receipt_gain_supplement.json 在独立官方审计之后，从冻结模型补算全部 538 个正式/探针事件的原生和实际交付 marginal gain，明确标为事后分析，未写回原日志、未算作预算内算法完成工作。候选在途状态由 cost_diagnosis_v1/events.json 保留原 incomplete 记录。

V1 的预处理合格使它实际花费了每个事件的排序预算，因此总进程约 0.88 秒，明显高于 V0/V3 预处理停用后的约 0.42 秒，却没有新增覆盖。局部成本修复不能写成整个采样流程更快。未执行等时间 HighDiv 对照，因而未证明优于完整 HighDiv。

real 阻塞的进一步解释：62 个 {0} 域中，61 个仅全局必需原子已能证明阻塞；位置 5、方向 11 的必需原子仍允许 [-1000,0]，完整 OR 373 才将域缩为 {0}，而 OR 2299 的远处 -1000 分支并未被忽略。具体节点、边界和完整分支推导见 real_blocking.zh.md。本批没有观察到正 slack 经整数取整形成零边界的阻塞模式。

real 证书内存采用固定 64 MiB 保守额度，缺逐证书实测堆增量；wait4 RSS 还包含未分离的启动阶段峰值，不能直接解释为证书内存。这项资源测量限制单列，不影响完整区间证书的数学核验，也不能据此声称获得了内存净增量的精确证明。
