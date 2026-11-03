# 观察保留改进器：成本修复与限定离线验证结果

结论：**整体 No-Go；保留已测得的局部成本/候选进展**。本轮完成代码、正确性、限定离线验证和独立审计；没有真实在线采样，没有重跑 HighDiv，没有追加 seed 或开启 B。历史逐模型 CPU 信用仍缺失，所有主结果均为 `historical_cpu_credit_proven=false`。

固定基点 `ae6da89e16be99142b7402fe6f0bccfb87e19893`；分支 `refinement-cost-repair`；实现冻结提交 `558ba2eff8dadf2d730a307177b704283d950e78`。同一个最终 Release worker 切换 Legacy、ValueCache、Shared。执行数为 9 个诊断 worker、39 条离线序列、24 个冷 oracle；43 个不同源模型共重放 559 个含首模型事件，重复不是独立模型或新 seed。

## 1. 实现与正确性

ValueCache 用每个 anchor 的空值缓存替换不变子项的整棵 ObservationTrace；缓存仅存精确数值，保留 AND/OR/ITE 短路、原操作次序和位长限制。仿射常数单独按旧系数点积顺序计算并复用，LineTerm 只在当前完整方向内共享。Shared 额外使用完整 DAG 父边和原变量出现点取得语法祖先闭包，保留 x-x、未选分支及所有观察点。真实硬条件各有独立 AST/缓存，按会话冻结配置编译。方向池、分量限制、原生 Ref、65536 守卫、动态库、原生 RNG/map/m_ls/参考/计数和候选规则均保持。

实现位置：`include/refinement/numeric_cache.hpp`、`dependency_index.hpp`、`affine_ir.hpp`、`line_domain.hpp`、`refiner.hpp`；阶段记录在 `cost_trace.hpp`，冷离线外壳在 `src/refinement/cost_repair_worker.cpp`。宿主模板与实际生成头文件均核对依赖和 SHA，保留旧树及旧二进制。

Release 和 ASan/UBSan 通过既有 244612 算术、1356 模命中、7938 域点、4 方向系统和 32 官方观察测试。新增固定工作量逐项核对等式、分量/跳过、方向/affected、顺序、目标、区间、参数、完整赋值、合法性、实际观察、保护缺失、得分与选中结果；独立 Python 复核 152 个合成候选。12001 节点链、共享 DAG、短路/未选异常分支、负数和高位、取消恢复、anchor/公式身份、x-x 支持集及四阶段取消均通过。原生隔离测试在三个配置、两种构建中都实际产生严格覆盖替代，保留完整 map、m_ls、RNG、参考及反馈比较；关闭模式与保存的原生行为一致。仅使用原有上游 LSAN 抑制。

真实审计复核 133 个带完整评分记录的候选、190 次官方访问轨迹核验（覆盖 113 个不同的“公式、完整赋值”对象，含原生及离线候选；真实来源仍为 43 模型），以及 128 对双方完成的真实诊断域。所有完成输出均合法、逐前缀包含原生观察；官方脚本对 39 条输出/原生序列分别统一计分。

保留的失败：预注册首次入口发生 Python 模块名冲突，重命名入口后通过；首个机制测试揭示首方向入口取消仍被记成 not_started，已先标记 incomplete 并保存实际抛出阶段。失败目录保留，没有将错误版本带入正式矩阵。共同日志补丁在 Legacy 三探针之后、最终三配置冻结之前应用；不重跑 Legacy，跨阶段探针不作为严格配对加速。冻结前复核还修复了局部捕获额度异常后 StageScope 误计 completed 的问题，新增对应合成测试；旧 Legacy 探针的该字段存在这一限制，实际域/候选计数不受影响。

审计计数口径：冻结审计脚本的 `unique_official_assignments_checked` 字段实际上计 LRU 未命中后的核验次数，逐序列复查和缓存淘汰会重复核验；不能将 190 当作不同模型数。独立按公式及完整赋值去重结果为 convert 95、random 8、real 10，共 113 个对象，见 `analysis/distinct_assignments.json`。没有更改冻结脚本或原日志来掩盖这个命名边界。

## 2. 固定诊断探针：上轮究竟卡在哪里

| 实例 | 配置 | 冷预处理 CPU / 墙钟 ms | 域完成 | 完整候选 | NumericValues 阶段调用 | 全数组分配槽 / 扫描槽 | 数值阶段 CPU ms |
|---|---|---:|---:|---:|---:|---:|---:|
| convert | Legacy | 130.530 / 134.588 | 0 | 0 | 1054 | 30291960 / 10097320 | 1826.524 |
| convert | ValueCache | 124.314 / 126.848 | 64 | 64 | 61149 | 38320 / 0 | 57.508 |
| convert | Shared | 148.848 / 151.465 | 64 | 65 | 61149 | 38320 / 0 | 57.456 |
| SMT_random | Legacy | 13.839 / 14.388 | 0 | 0 | 0 | 0 / 0 | 0.000 |
| SMT_random | ValueCache | 12.617 / 12.839 | 0 | 0 | 4 | 23168 / 0 | 0.382 |
| SMT_random | Shared | 11.042 / 11.349 | 0 | 0 | 4 | 23168 / 0 | 0.360 |
| SMT_real | Legacy | 40.765 / 41.853 | 0 | 0 | 2880 | 34611840 / 11537280 | 1974.635 |
| SMT_real | ValueCache | 36.481 / 37.112 | 64 | 2 | 95729 | 16024 / 0 | 56.618 |
| SMT_real | Shared | 43.158 / 44.190 | 64 | 2 | 95729 | 16024 / 0 | 57.132 |

旧路径的整数组槽/扫描数来自实际计数，非推测；一个未完成扫描按其已启动的全数组扫描记录，因此 scan_slots 是要求扫描的规模，budget_checks 保留实际执行进度。新数值路径没有观察数组和最终全 AST 掩码扫描；每 anchor 冷分配计入 NumericValues/LineTerms。公式域自身和最终候选的独立验证/官方观察仍可分配数组，不能把这项局部修复说成整个改进器线性化。numeric_cache_bytes 仅为缓存槽存储下界，完整内存使用看 RSS。

预处理具体 exclusive 阶段如下（ms；嵌套时间不重复相加）：

| 实例 | 配置 | 依赖 | 系数 | 等式 | 分量 | 消元 | 验证方向 | affected | 元数据 | 序列化 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| convert | Legacy | 40.035 | 6.423 | 3.224 | 7.061 | 7.037 | 42.955 | 13.557 | 3.613 | 5.700 |
| convert | Shared | 4.735 | 5.924 | 3.075 | 0.746 | 6.702 | 42.198 | 75.173 | 4.734 | 4.851 |
| convert | ValueCache | 36.277 | 6.129 | 3.017 | 6.467 | 6.699 | 42.075 | 14.085 | 3.325 | 5.505 |
| SMT_random | Legacy | 3.642 | 4.001 | 1.863 | 1.856 | 0.148 | 0.000 | 0.019 | 1.005 | 0.783 |
| SMT_random | Shared | 3.307 | 3.872 | 1.896 | 0.421 | 0.122 | 0.000 | 0.022 | 0.596 | 0.369 |
| SMT_random | ValueCache | 3.589 | 3.881 | 2.000 | 1.557 | 0.123 | 0.000 | 0.016 | 0.629 | 0.418 |
| SMT_real | Legacy | 2.511 | 2.980 | 2.852 | 2.424 | 14.157 | 10.879 | 1.815 | 1.541 | 1.223 |
| SMT_real | Shared | 2.306 | 2.451 | 1.432 | 0.482 | 13.560 | 10.304 | 9.580 | 1.517 | 1.202 |
| SMT_real | ValueCache | 2.480 | 2.444 | 1.397 | 1.247 | 13.714 | 10.357 | 1.840 | 1.521 | 1.123 |

这些探针只使用固定第 2/3/4/5 位置的原生前缀，输出不进入后续历史。原配置在诊断上限未完成的域/候选是删失记录，不能用 500 ms 算精确加速倍数；双方完成的域和目标逐项一致，未有交集的部分用固定合成工作量验证。

单次数值诊断的具体解释：ValueCache 与 Shared 都让 convert 的四位置完成 64 个域、real 完成 64 个域；旧配置在相同诊断上限均未完成第一个域。NumericValues 的整数组扫描从旧路径的千万级要求槽数降为 0，新路径每 anchor 的值槽和仿射常数槽仍分别分配并计费；上表 NumericValues 的调用还包含四次冷初始化，不能拿调用数直接当作相同工作量。

**Shared 没有带来总体预处理降本。** convert 的依赖阶段从本阶段 ValueCache 的 36.277 ms 降到 4.735 ms，但 affected 构造从 14.085 ms 升到 75.173 ms，抵消并超过前项节省；整个已完成的诊断冷预处理为 124.314 vs 148.848 ms CPU。这个对照只有一次，不能声称普遍精确加速/退化倍数。主 L2 的 real 三次完整预处理则稳定显示 Shared 更贵：中位 CPU 43.736 ms，ValueCache 36.525 ms。父边表示减少传递依赖存储，不代表逐方向反复走父边就更便宜；原预算检查频率没有为新实现稀疏化。

## 3. 主 L2 三次重复：成本与收益分开

表中预处理为中位数 [最小, 最大]，单位 ms；完整候选与最终额外 covered 按 r1/r2/r3 全列。

| 实例 | 配置 | 冷预处理 CPU | 冷预处理墙钟 | 完整候选（三次） | 最终额外 covered（三次） | 预处理状态（三次） |
|---|---|---:|---:|---|---|---|
| convert | Legacy | 100.896 [100.798, 100.935] | 100.908 [100.859, 100.950] | 0/0/0 | 0/0/0 | wall_budget_exhausted / wall_budget_exhausted / wall_budget_exhausted |
| convert | ValueCache | 100.943 [100.913, 100.952] | 100.961 [100.947, 100.968] | 0/0/0 | 0/0/0 | wall_budget_exhausted / wall_budget_exhausted / wall_budget_exhausted |
| convert | Shared | 100.540 [99.284, 100.665] | 100.670 [100.608, 100.675] | 0/0/0 | 0/0/0 | wall_budget_exhausted / wall_budget_exhausted / wall_budget_exhausted |
| SMT_random | Legacy | 12.476 [12.401, 12.549] | 12.759 [12.648, 12.796] | 0/0/0 | 0/0/0 | completed / completed / completed |
| SMT_random | ValueCache | 12.624 [12.502, 12.684] | 12.886 [12.717, 12.937] | 0/0/0 | 0/0/0 | completed / completed / completed |
| SMT_random | Shared | 11.118 [10.933, 11.254] | 11.387 [11.162, 11.527] | 0/0/0 | 0/0/0 | completed / completed / completed |
| SMT_real | Legacy | 36.554 [36.203, 36.989] | 37.305 [37.269, 37.608] | 0/0/0 | 0/0/0 | completed / completed / completed |
| SMT_real | ValueCache | 36.525 [36.485, 36.848] | 37.129 [36.989, 37.664] | 0/0/0 | 0/0/0 | completed / completed / completed |
| SMT_real | Shared | 43.736 [43.485, 43.984] | 44.697 [44.609, 44.704] | 0/0/0 | 0/0/0 | completed / completed / completed |

配对表只把成功完成的预处理当作完成耗时；超时值是截断成本。计时期间单进程顺序、固定物理核 0 的线程 0，主配置顺序按预登记三轮轮换，无并行编译、压缩、上传、oracle 或其他本任务实验。

| 实例 | 配置 | 全序列可选 CPU ms（中位/范围） | 必需 CPU ms | 完整进程 CPU ms | 完整进程墙钟 ms | RSS KiB（中位） |
|---|---|---:|---:|---:|---:|---:|
| convert | Legacy | 108.515 [108.275, 108.712] | 236.836 [235.454, 236.970] | 370.504 [368.744, 371.250] | 403.292 [402.723, 412.514] | 27984 |
| convert | ValueCache | 108.525 [108.511, 108.628] | 237.388 [235.401, 237.655] | 370.840 [368.982, 371.462] | 404.404 [400.242, 404.915] | 27408 |
| convert | Shared | 108.084 [106.915, 108.420] | 237.913 [237.506, 238.339] | 370.778 [369.673, 371.663] | 403.479 [402.166, 414.572] | 27984 |
| SMT_random | Legacy | 29.346 [29.338, 29.562] | 38.493 [38.210, 39.431] | 83.919 [83.654, 85.250] | 107.606 [105.132, 113.955] | 27984 |
| SMT_random | ValueCache | 30.744 [30.188, 30.775] | 38.326 [38.046, 38.576] | 85.115 [85.064, 85.393] | 107.830 [107.417, 117.270] | 27984 |
| SMT_random | Shared | 29.248 [28.801, 29.420] | 38.310 [37.925, 40.299] | 83.660 [82.619, 85.868] | 106.785 [105.773, 109.764] | 27984 |
| SMT_real | Legacy | 179.568 [179.214, 180.134] | 26.561 [26.225, 26.863] | 218.475 [217.944, 219.093] | 241.623 [240.866, 243.383] | 27984 |
| SMT_real | ValueCache | 180.627 [180.576, 181.095] | 26.484 [26.400, 26.594] | 219.705 [219.597, 219.837] | 243.108 [241.398, 244.890] | 27984 |
| SMT_real | Shared | 187.933 [187.566, 188.265] | 26.542 [26.402, 26.737] | 226.992 [226.843, 227.766] | 251.718 [250.851, 254.617] | 27984 |

完整逐次表在 `results/refinement_cost_repair/analysis/sequences.csv`，逐事件曲线、拒绝原因、目标和参数、失败候选、实际观察及成本原记录见归档。optional_unscoped_cpu 单列作用域外的账本/JSON准备/清理成本；record_tail_cpu 单列成本记录自己的输出。最终总结不能自测自己的写出时间，全部进程由父进程 wait4/pidfd 计量。没有将未完成事件输出算进覆盖。

可选成本与尾部边界：每个被取消的 20 ms 事件仍可能因非中断式 JSON/清理/记录尾部产生超支，逐次额外量见 `sequences.csv` 的 `event_overrun_cpu/wall` 和逐事件文件。旧/新配置均计入，不能拿标称 20 ms 当最终耗时。上表 RSS 是完整进程高水位，不是仅数值缓存的净增量；本轮没有把缓存所有动态大整数容量单独做精确堆计量。

## 4. 候选、保护与覆盖得失

| 实例 | 配置 | 主 L2 完整评价总数 | 保留通过 / 拒绝 | 严格 covered 替代 / 仅单侧替代 | 无保护选中不同 | 输出重复 |
|---|---|---:|---:|---:|---:|---:|
| convert | Legacy | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| convert | ValueCache | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| convert | Shared | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| SMT_random | Legacy | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| SMT_random | ValueCache | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| SMT_random | Shared | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| SMT_real | Legacy | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| SMT_real | ValueCache | 0 | 0 / 0 | 0 / 0 | 0 | 0 |
| SMT_real | Shared | 0 | 0 / 0 | 0 / 0 | 0 | 0 |

**诊断轨道的实际见证：** convert 的原生位置 3，两种缓存配置都选到方向 186、参数 t=3 的候选；完整保留 1049 个 protected 观察，新增 covered 从原生的 1049 提高到 1092，即 **+43**。原式合法、官方实际访问和完整保护已独立核验。完整赋值和访问轨迹见 `analysis/diagnosis_v1/diagnostic_opportunities.json`。这是同一个固定位置在两个实现中的一致见证，不是两个独立实例，更不是 100/20 ms 主结果；两个探针都继续使用原生历史，没有交付或将见证带入后续排序。

诊断共完成 133 次候选评价：99 次因 protected 观察缺失被拒，34 次为严格覆盖改进候选（集中在上述同一位置，两配置各 17 次）；另保留 4 条候选重复和 6 条未完成候选。不能用这个截断且有限的集合估计全问题的保护拒绝率。real 的每个缓存配置只有位置 2、5 各完成一个候选，均保护失败，且没有更高的无保护得分；位置 3、4 没有候选。

带更高无保护分数且有观察缺失的记录共 85 条（含诊断及补充轨道，不能混入主 L2）。完整差集保留于 `analysis/audit_v1/protected_losses.json`。

具体例子（完整差集仍以 JSON 为准）：
- probes/new_v1/convert_Shared，位置 2，方向 186，t=1：原生增益 [26220, 26250]，无保护候选增益 [26233, 26263]，丢失 16 个观察；前 5 个 `(node,bit,side)` 为 `[[2436, 1, 1], [2438, 1, 1], [2442, 0, 0], [2444, 0, 0], [2446, 1, 1]]`。
- probes/new_v1/convert_Shared，位置 2，方向 183，t=1：原生增益 [26220, 26250]，无保护候选增益 [26231, 26261]，丢失 15 个观察；前 5 个 `(node,bit,side)` 为 `[[2436, 1, 1], [2438, 1, 1], [2442, 0, 0], [2444, 0, 0], [2446, 1, 1]]`。
- probes/new_v1/convert_Shared，位置 2，方向 98，t=1：原生增益 [26220, 26250]，无保护候选增益 [26228, 26258]，丢失 16 个观察；前 5 个 `(node,bit,side)` 为 `[[2436, 1, 1], [2438, 1, 1], [2442, 0, 0], [2444, 0, 0], [2446, 1, 1]]`。

G1/G2/G3 沿用原冻结映射与首模型划分，完整得失见 `analysis/partitions.csv`。所有完成前缀都保留全部原生观察，因此没有通过集合外覆盖损失换取集合内收益。方向池为空、域取消、目标恒定、精确不可达、unsupported、有限搜索未完成分别保留，零收益不叫 UNSAT。

补充 L1/component_only（各一次，不增加模型证据）：

| 实例 | 配置 | 模式 | 完整评价 | 选中改进（诊断/输出按模式区分） | 最终额外 covered |
|---|---|---|---:|---:|---:|
| convert | Legacy | L1 原生历史 | 0 | 0 | 0 |
| convert | Legacy | component_only | 0 | 0 | 0 |
| convert | Shared | L1 原生历史 | 0 | 0 | 0 |
| convert | Shared | component_only | 0 | 0 | 0 |
| SMT_random | Legacy | L1 原生历史 | 0 | 0 | 0 |
| SMT_random | Legacy | component_only | 0 | 0 | 0 |
| SMT_random | Shared | L1 原生历史 | 0 | 0 | 0 |
| SMT_random | Shared | component_only | 0 | 0 | 0 |
| SMT_real | Legacy | L1 原生历史 | 0 | 0 | 0 |
| SMT_real | Legacy | component_only | 0 | 0 | 0 |
| SMT_real | Shared | L1 原生历史 | 0 | 0 | 0 |
| SMT_real | Shared | component_only | 0 | 0 | 0 |

**real 无参数的直接原因已进一步核对。** 主 L2 中，ValueCache 完成 101 个完整域，Shared 完成 105 个；全部精确为 `{0}`，并非不完整记录被写成空域。补充轨道另有 67 个同样的 `{0}` 域。已记录的 2118 次 `no_nonzero_legal_parameter` 均与原式完整域 `{0}` 一致，另有 2 次命中搜索未完成；生产轨道提出参数总数为 0。较宽探针中，每种缓存配置的 real 64 个域有 62 个 `{0}`、2 个有非零位置。说明原有单方向集合在这些 anchor 上大多不能移动，不能归因为保护筛选，也不能推广为原问题不存在其他模型。检查只是分类已落盘区间，没有重算未完成工作、没有新 worker/solver 调用，见 `analysis/domain_records_v1/summary.json`。

完整原式域包含已验证原生 anchor，故本批完成域的 `exact_empty` 为 0；`{0}`、unsupported、not_started 和 incomplete 分开统计。目标的 `complete_no_hit_in_domain` 与预算取消也分开，未记录的目标内部中间状态不作填补。

random 仍为 89 个分量，10 个原超限分量均跳过，方向池为 0；完整行/非零项/行长/单位系数结构见 `analysis/audit_v1/random_skipped_structure.json`。本轮没有算这些分量的秩、没有新增方向或调用求解器，秩为 rank_unknown。

## 5. 冷 oracle：编码、导出和 check 分开

旧轮 12 案只可说没有记录到 check 入口，不能从旧日志反推具体卡点。本轮新外壳在重型导入前写阶段记录，两个编码使用完整同一问题、同一冷 3 s 上限，check 最多 2 s 且不超过整案剩余时间；完整 SMT2 导出仍在 check 之前。没有用 SAT 见证供应采样。

本轮 24 案共记录 check_attempt=0、check_return=0、截止内已验证交付=0。只有 check_return 才证明 API 返回；强制终止不推造内部求解步数。

| 案例 | 配置 | 最后工作阶段 | 状态 | check_attempt / return | 已验证交付 | 进程 CPU / 墙钟 ms |
|---|---|---|---|---:|---:|---:|
| convert #2 | OracleLegacy | extra_build | parent_deadline | 0 / 0 | 0 | 2865.048 / 3010.529 |
| convert #2 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2870.414 / 3008.827 |
| convert #3 | OracleLegacy | extra_build | parent_deadline | 0 / 0 | 0 | 2832.994 / 3011.088 |
| convert #3 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2873.559 / 3013.271 |
| convert #4 | OracleLegacy | extra_build | parent_deadline | 0 / 0 | 0 | 2866.849 / 3010.598 |
| convert #4 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2875.317 / 3013.108 |
| convert #5 | OracleLegacy | extra_build | parent_deadline | 0 / 0 | 0 | 2869.618 / 3007.825 |
| convert #5 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2870.529 / 3006.500 |
| SMT_random #2 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2864.677 / 3007.876 |
| SMT_random #2 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2857.561 / 3009.758 |
| SMT_random #3 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2858.196 / 3006.770 |
| SMT_random #3 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2849.963 / 3013.993 |
| SMT_random #4 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2868.378 / 3004.604 |
| SMT_random #4 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2854.564 / 3009.903 |
| SMT_random #5 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2865.618 / 3005.190 |
| SMT_random #5 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2852.612 / 3011.925 |
| SMT_real #2 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2856.833 / 3003.920 |
| SMT_real #2 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2868.074 / 3010.146 |
| SMT_real #3 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2866.222 / 3008.762 |
| SMT_real #3 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2869.333 / 3007.870 |
| SMT_real #4 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2871.750 / 3006.303 |
| SMT_real #4 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2872.493 / 3010.916 |
| SMT_real #5 | OracleLegacy | reach_build | parent_deadline | 0 / 0 | 0 | 2859.648 / 3009.172 |
| SMT_real #5 | OracleShared | extra_build | parent_deadline | 0 / 0 | 0 | 2870.261 / 3008.814 |

OracleShared 仅复用 AND/OR 前缀、完整 incoming 的析取、正侧 bit 谓词，以及按节点分组的完整 extra；不删原观察点或保护。625 个有限赋值点比较旧编码、新编码和解释器观察（含宽度 1/2/8/64、共享 DAG、NOT 和数值 ITE）通过，合成测试 solver checks=0。真实编码未完成时 AST 统计仅保留已经编码计数；不能把未得到的最终问题大小填成 0。原始逐阶段日志、完整/部分导出、Unknown、截止与退出延迟全保留。

当前 oracle 证据是编码推进而非求解推进：Legacy 的 random/real 八案均停在 reach_build，Shared 的相同八案进入 extra_build；convert 两种编码八案都停在 extra_build。24 案均未进入 solver_add、SMT2 完整导出或 check。没有产生可用的完整问题 DAG 大小统计或求解答案，缺值保留未知，不能写成 0 大小或 UNSAT。阶段 enter 记录的计数是最近已落盘的下界；父进程杀死后不能补造末尾计数。

## 6. 十项直接回答

1. 能。旧 convert 预处理的阶段成本已经拆开，real 的旧首方向主要停在 NumericValues；具体取消节点和方向保留在 trace。新瓶颈按本报告各阶段表和逐事件 last_incomplete_stage 报告，不把未完成称为空域。

2. 旧 real 四个诊断位置 NumericValues 要求分配 34611840 个槽、扫描 11537280 个槽，共 2880 次调用，CPU 1974.635 ms。这个值是被截断工作，不是完整求值成本。

3. ValueCache 消除了热不变子项的重复整数组初始化/掩码扫描，并共享相同 anchor 的仿射点积；Shared 再用直接父边代替传递依赖物化。阶段表分别列出实际减少与剩余工作；不能混用跨冻结时点的探针来给精确加速倍数。

4. convert 的 Shared 三次冷预处理状态为 wall_budget_exhausted / wall_budget_exhausted / wall_budget_exhausted；random 的十个跳过分量保持；real 的 Shared 三次完整评价数为 0/0/0。

5. 完整候选和选中输出经独立合法性、保护、去重、严格字典序增益核验；严格 covered 与仅单侧新增分开计数。主 L2 完整评价共 0 次；整个事件连同日志尾部均不超额度的完整评价共 0 次。算法内完成与含日志的总成本不能混称。

6. 无保护与完整保护差异按实际 missing 集合解释；高分但缺保护观察记录共 85 条，例子及全量 JSON 已给出。未评价候选的位置不能估算保护拒绝率。

7. 三次结果全部列出。Shared 在三次都严格增加 covered 的实例为 无；有任何偶发单次正值也保留在主表，不据最好一次宣布成功。

8. 旧轮缺日志，具体阶段未知；本轮最后工作阶段分布为 `{'OracleLegacy:extra_build': 4, 'OracleShared:extra_build': 12, 'OracleLegacy:reach_build': 8}`。实际 check_attempt/return/验证交付分别为 0/0/0，截止不是 UNSAT。

9. 计算复用和工作计数下降属于成本证据；完成合法候选属于阶段可达；至少两实例三次均严格覆盖增益的整体离线门槛未成立。在线等时间/等样本收益和完整历史信用仍未知。

10. 没有逐模型原生 CPU，不能证明原双信用策略，不用墙钟或平均值代填。预处理算法/元数据/写出、事件候选/失败/验证/观察/评分、日志尾部、必需观察及全部进程成本均记录；超支逐事件单列，未完成输出不进覆盖。无新真实采样、无在线曲线。

## 7. 边界与后续

本轮四层结论分别为：正确性与状态隔离通过；数值复用消除了特定重复扫描并在同预算内完成更多域，属于局部成本/工作量进展；Shared 的整体预处理降本未成立；100/20 ms 的合法候选阶段与整体离线覆盖机会均未成立。convert 的 +43 见证只证明较宽预算下存在局部机会。

最值得下一轮独立检验的单因素是：**将 Shared 的 affected 构造改为等价的批量/共享祖先传播，消除现有逐方向重复遍历**，仍核对完全相同的语法影响集合，不改方向池或保护，不以减少预算检查频率获胜。本轮没有实施这第三项修复。即使这一阶段修好，convert 诊断位置 2 的排序本身已花 34.93 ms CPU，超过整个生产事件上限；因此不能承诺一个局部修复就会使候选可达。real 的大量 `{0}` 域则是另一个需要独立研究的方向供给问题。

其余记录边界：预处理构造/验证方向时 trace 未填充稳定方向 ID（为 -1），可定位到具体阶段、节点和累计工作，不能给出精确的在途方向身份；事件中的方向槽与取消阶段均保留。没有为补这个记录缺口重跑已冻结实验。冷启动指每 worker 的空数值缓存、空索引和新方向池；未清空操作系统文件页缓存。CPU 绑定为逻辑 CPU 0，sysfs core_id=0，兄弟线程列表 0–1；不是对宿主所有背景进程的独占声明。

本轮止于离线报告，没有在线短会话、900 秒矩阵、真实 HighDiv 重跑、新 seed 或 B 补救。历史逐模型 CPU 信用、真实生成供给以及等时间/等样本在线收益仍未知。

完整原始证据与全部失败见 `archives/refinement_cost_repair/RESTORE.md`；逐成员及分片 SHA256 与全量恢复验证随仓库提交。冻结清单在 `manifests/refinement_cost_repair/`，最终发布的完整 SHA 用 git ls-remote 核对，发布收据保存在本地 build/refinement-cost-repair-publish-receipt.json。
