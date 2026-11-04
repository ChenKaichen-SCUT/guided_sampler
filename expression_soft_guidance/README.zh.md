# 原表达式部分 bit 软参考实验

本项目从 HighDiv `f2c6e1756b13281d96cbf90a8bd940129e56cce4` 的完整源码建立独立副本，不包含 guided_sampler 的 A/B、软参考、守卫或输出精修补丁。

目标：仅对历史上单侧已见的原 AST bit 建立相反偏好；两侧都见过或都未见的 bit 不产生偏好。原表达式使用精确整数分解，参考 bit 是普通可回溯决策，空白位自由，所有原始硬约束保留。

新增表达式定义属于投影保解的定义扩展，不断言参考 bit 必须取目标值。v4 不再对外层 combined solver 执行 push/pop：先按原逻辑选择后端，再在所选后端内部安装本轮定义。关闭的 native 模式不安装新目标。v3、v4 的源码、二进制和动态库已分别保存在 `archive/v3`、`archive/v4`，旧结果保留。本轮 v5 处理 CCSS 阶段预算与模型交换，见 `REPORT_v5.zh.md`。

## CCSS 模型交换与阶段预算（v5）

`ESG_CCSS_MS=100` 为每次 CCSS check 设置 100ms 预算，并裁剪到剩余总时间。计时从 check 前开始，包括 SMT 内部准备、表达式映射、实例构建、初始化、搜索和内核模型生成；原生 `timeout` 与 CCSS 循环内的协作检查共同生效。超时只返回 unknown，不导出局部搜索中的部分赋值，也不作为不可翻转位的证据。模型转换、原公式验证与交付另行计时，仍受总截止时间约束。这里是协作式预算，允许清理和检查间隔造成小幅超出，实验记录实际超出量，不把它宣称为严格实时上限。

`ESG_CCSS_FEEDBACK=complete` 在 CDCL 模型经过原公式验证之后，以完整原变量赋值替换整个交换表；不依赖内部预处理保留下来的部分变量，也不保留上一模型的残值。合法重复模型仍可作为种子，覆盖历史只更新正式交付的不同模型。`native` 保留上游逐项更新表的方式，`hold` 在有软目标的查询前保存交换表、消费模型后恢复，用于隔离软模型对 CCSS 的影响。

`ESG_CCSS_OFF=1` 关闭 CCSS 调用；保留原 CDCL 与软目标调度，不另外引入随机赋值或模型阻塞子句。因为不再产生 LS 模型，原来的 LS→CDCL 继承也随之消失，因此这是移除整个 CCSS 通路的对照，不是保持模型序列的等价加速。

默认不设置以上环境变量时仍采用原生交换与原生预算。`scripts/profiles.py` 定义了可复现实验配置：`soft_complete` 为软指引＋100ms＋完整交换，`base_complete` 为无软指引、相同预算与交换；`soft_budget` 只加预算，`soft_hold` 保留此前交换表，`soft_off` 关闭 CCSS。`soft` 保留 v4 的机制作为对照。

每次运行的 `ccss.jsonl` 记录各次调用的六个内核阶段耗时、结果、超时标记、模型数和覆盖增量，`queries.jsonl` 记录交换表大小，`run.json` 保存实际环境配置。`audit_ccss.py` 对齐阶段日志、正式样本和汇总，检查超时不能交付模型及关闭组没有 CCSS 调用。

未修改内核的 baseline 不含内部阶段接口，六段内核时间为 0 占位；该组只使用宿主测得的 check 和完整 CCSS 阶段时间进行比较。`deadline_hit` 标记本轮新增的循环检查触发，不把其他 unknown（包括 Z3 自身 timeout 或原生有限算术域限制）全部归类为这个标记。

## 实际实现

`include/observer.hpp` 在独立 Z3 context 中保存原 AST，按官方访问器的 AND/OR 短路和 ITE 分支规则，用任意精度整数求值。历史只来自已经交付的合法、不同原变量赋值。

对每个原节点，`mask = seen0 XOR seen1`，`desired = seen0 AND NOT seen1`。两侧都见过、都没见过的位均不产生补覆盖偏好；这里的“见过”要求该节点在原公式求值时实际被访问。

`include/pattern.hpp` 把选中的原整数表达式精确分解为整数位段：每个偏好位单独一段，连续自由位合并成一个有界整数段，高位剩余部分为无界整数。比如从最低位开始编号的 `1?????10` 可以写为 `x+y = 256*k + 128*b7 + 4*t + 2*b1 + b0`，其中 `0 <= t < 32`，`b0,b1,b7` 为 0/1 整数。三个偏好分别是 `b0=0、b1=1、b7=1`，不是硬断言。负数和第 63 位也按精确整数分解处理。

`kernel/decide.inc` 优先把 `Reach(原表达式) AND (目标位=目标值)` 当作普通 SAT 决策。原生理论传播、冲突分析、学习和回溯继续工作；回溯后重新考虑未赋值目标。每次查询最多在前 64 次决策调用中介入，之后恢复原生顺序。它不承诺找到全局满足偏好数最多的模型。

`kernel/tactic.inc` 把软目标沿原生预处理的 model converter 正向代换，处理 `solve-eqs` 消去原变量、辅助位的情况；目标再进入实际 SMT 后端。未知转换器类型会记录 `mapping_failures` 并跳过决策，不把消去后的同名新变量当原目标。原生 tactic 若已直接求解或使用其他后端，记录 `unprepared_sat_queries`，不伪称执行了偏好决策。每个交付的目标模型仍需通过原表达式位值与 Reach 的核对。

默认调度一次选择一个原表达式、至多 8 个仍需补覆盖的 bit；`ESG_MAX_BITS` 可设为 0–64。优先整数中间表达式，然后是不被原公式结构固定的 Bool，最后是整数变量。排除常量、依赖超过 16 个变量的目标，轮转扫描最多 512 个候选。编码支持完整部分模式，在线实验使用这个有限窗口；没有同时为所有原节点的所有 bit 建立定义。

## 不可翻转位

`include/impossible.hpp` 在运行中维护有依据的排除缓存，历史 seen0/seen1 与官方覆盖率分母不变：

- 静态推导：用精确的模 `2^k` 同余关系和原公式必然成立的整数上下界，推导固定 bit；覆盖加、减、负号、乘法和 ITE。例如 `-4294967296*x` 的低 32 位恒为 0。
- 在线验证：每次至多验证一个剩余目标，独立上下文只加入原公式、Reach 和该 bit 的目标值；结果为 UNSAT 才缓存为不可达。历史继承等式从不进入这个验证器。
- 单次求解 timeout 为 5ms，验证累计时间的调度预算为 `min(0.5s, 总预算的2%)`。构建及查询实际耗时都记入 proof_wall 与总采样预算；一次已启动的构建可能越过调度预算。超时、unknown、预算耗尽均不作为不可能证据。
- `impossible.jsonl` 记录固定掩码、值、上下界、同余关系及在线 SAT/UNSAT/unknown。`audit_impossible.py` 用未修改上游 Z3 独立重验排除结论，并检查后续目标未再次选中已经排除的方向。

## 与 HighDiv 的边界

- 从 `HighDiv-master` 的冻结上游复制；准备脚本核对 2,935 个文件的 SHA256。上游和旧 guided_sampler 实现都未改动。
- 高层仍是完整 CDCL(T)+CCSS 混合采样。新目标只放入 CDCL(T)，不把人工 bit 变量交给 CCSS。
- 新辅助声明按声明身份从 `last_CDCL_model` 排除，原变量模型仍按 HighDiv 原方式反馈。不是按变量名前缀粗略过滤。
- 原 AST 观察与内部预处理节点分离；每个交付模型都检查原公式，并核对内部目标与原表达式实际位值、访问状态。
- tactic 后端把定义加入本次局部 goal；增量后端在其内部临时作用域中安装定义，并在模型消费完后撤销。combined solver 的选择条件和状态迁移保持上游原样；正常继承 assumptions 仍会触发原生增量路径。
- `route` 是修复后的空接入对照，检查样本前缀是否与基线完全相同。`scope` 保留旧的外层空 push/pop，仅供诊断。真实软指引增加定义并改变模型，仍可能改变内部 tactic 的选择、搜索耗时和下一轮 CCSS 的行为；空接入一致不代表启用后没有这些成本。
- `soft` 保留 HighDiv 随机继承的历史变量等式；`soft_release` 只放开当前目标依赖变量上的这些历史等式，是独立消融。原始输入约束从不删除。
- 导出的样本只含原变量。离线使用未修改的官方 `calc_metric.py` 和未修改的基线 Z3，核对每个模型、历史偏好方向、原节点 Reach、目标命中和覆盖值。

## 模式

| 模式 | 用途 |
|---|---|
| baseline | 相同测量适配，链接同编译器构建的未修改 HighDiv 库 |
| native | 链接新库，关闭观察与软指引 |
| observe | 只观察和更新覆盖历史 |
| scope | 观察 + 空 push/pop，测求解路径变化 |
| route | 修复后的空接入，不对外层 solver 作任何临时修改 |
| definitions | 加精确定义，不给偏好决策 |
| soft_unfiltered | 修复路径，原表达式软指引，不筛除不可翻转位 |
| soft_static | 修复路径 + 静态同余/范围过滤 |
| soft | 修复路径 + 静态过滤 + 有预算的原公式 UNSAT 验证 |
| soft_release | 软指引 + 选择性放开继承的历史等式 |

直接执行 `bin/highdiv_soft` 时默认 `ESG_MODE=native`；显式设置 `ESG_MODE=soft` 才启用机制。

## 重现

在 WSL Ubuntu 中，从本目录执行。编译依赖 g++、Python 3、Boost 和 nlohmann/json；当前构建脚本使用工作区已有的第三方头文件。这里只复用上游身份清单、输入清单、官方度量和第三方依赖，不复用旧版本的指引代码。

```bash
python3 scripts/prepare.py --destination /tmp/my_fresh_expression_soft_build
python3 scripts/build_kernel.py
python3 scripts/build_baseline.py --destination /tmp/my_fresh_expression_baseline_build
python3 scripts/build_host.py --tests-only
python3 scripts/build_host.py
python3 scripts/verify.py

python3 scripts/run.py --name my_time_run --seconds 30 \
  --modes baseline,soft,soft_budget,soft_complete,soft_hold,soft_off,base_budget,base_complete --seeds 0,1 --workers 8
python3 scripts/audit_parallel.py my_time_run
python3 scripts/audit_impossible.py my_time_run
python3 scripts/audit_ccss.py my_time_run

python3 scripts/run.py --name my_n20_run --seconds 30 --samples 20 \
  --modes baseline,native,observe,route,base_complete,soft_complete --seeds 0,1 --workers 8
python3 scripts/audit_parallel.py my_n20_run
python3 scripts/audit_impossible.py my_n20_run
python3 scripts/audit_ccss.py my_n20_run
python3 scripts/compare_prefix.py my_n20_run
```

两个构建目录都必须尚不存在；用不同的 `--destination` 即可另建副本。

直接运行示例：

```bash
mkdir -p /tmp/my_soft_run
ESG_MODE=soft ESG_MAX_BITS=8 ESG_CCSS_MS=100 ESG_CCSS_FEEDBACK=complete ./bin/highdiv_soft \
  -i benchmarks/convert_convert-jpg2gif-query-1459.smt2 \
  -o /tmp/my_soft_run -n 20 -t 30 -s 0
python3 scripts/export_samples.py /tmp/my_soft_run
```

正式导出以 `receipts.jsonl` 中 `accepted=true` 的记录为准；审计生成干净的 `accepted.samples`。独立运行时可用 `export_samples.py` 转出同一格式；该脚本仅导出，不代替独立审计。上游旧文件名的 `.samples` 文件仍由兼容宿主创建，但不用于输出，请读取 `accepted.samples`。`samples.raw` 是计时写出记录，截止边缘可能包含随后被拒绝的一行。查询细节在 `queries.jsonl`，每次实验保存源码快照、二进制/动态库哈希、输入哈希和 CPU 分配。

采样计时从解析前开始。使用原生 CCSS 预算的组为避免整数秒 timeout 变成 0，在最后不足 1 秒时不再启动 LS，因此部分 30 秒运行会在约 29 秒结束。v5 毫秒预算组可以继续使用剩余时间；报告同时提供前 29 秒覆盖，并比较同样使用毫秒预算的无指引基线。求解器清理可以晚于截止，晚交付模型不计入覆盖。固定样本实验未达到 20 个模型时，等样本比较标记为未完成。

## 当前验证与结果

语义测试覆盖 8,487 个位值检查、6 个协调/冲突/作用域场景、12 次后端路由检查、773 个 Reach 检查与 6,240 个数学事实检查，还验证 UNSAT 缓存、原公式下可行位不受历史赋值影响、预算耗尽不筛除。CCSS 单元验证覆盖交换表整体替换、旧值清除、快照恢复以及连续 8 次超时→下一次正常求解。结果分别见 `REPORT.zh.md`、`REPORT_v4.zh.md`、`REPORT_v5.zh.md`；机制正确实现不等于在每个输入上都有性能收益。

重放归档二进制时，需显式使用相应 `LD_LIBRARY_PATH=archive/v4/deps/soft/lib`（v3 换成 v3；基线使用对应 baseline/lib）；二进制内原有的绝对 rpath 不随归档移动。
