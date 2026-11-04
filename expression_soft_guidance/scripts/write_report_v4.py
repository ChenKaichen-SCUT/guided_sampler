import json,statistics
from prepare import ROOT,write
s=json.loads((ROOT/'results/v4_summary.json').read_text());d=json.loads((ROOT/'results/v4_diagnostics.json').read_text());v=json.loads((ROOT/'results/v4_final_verification.json').read_text())
assert s['audit_passed'] and s['filter_audit_passed'] and v['passed']
static=sum(r['static_unique_bits'] for r in d['filters'].values());unsat=sum(r['F_only_unsat_sides'] for r in d['filters'].values())
pairs=[r for r in s['sample_pairs'] if r['mode']=='soft'];completed=[r for r in pairs if r['complete']]
wins=sum(r['delta_bits']>0 for r in completed);losses=sum(r['delta_bits']<0 for r in completed);ties=sum(r['delta_bits']==0 for r in completed)
lines=[f'''# 软指引 v4：保持求解路径与不可翻转位过滤

本轮按用户要求完成两项改动：临时软指引不再让 combined solver 意外切换路径；采样中记录并跳过已有数学依据证明不可能补覆盖的位。两项正确性检查通过，但整体性能尚未胜过 HighDiv，尤其 convert 仍有严重的后续局部搜索停顿。

基点仍是 HighDiv `f2c6e1756b13281d96cbf90a8bd940129e56cce4`。未改动上游 2,935 个文件和旧 guided_sampler；v3 代码、库和二进制位于 `archive/v3`。

## 路径修复

旧方式在外层 combined solver 上 push/pop，不仅会使它永久选择增量后端，还会提前修改另一个后端的内部状态。试验中先只阻止切换，仍出现样本前缀变化，因此这版采用后端内部安装：

1. 外层保留原始后端选择逻辑，不安装临时 assertion、push 或 pop。
2. 原生选择 tactic 后端时，定义只加入本次局部 goal；选择增量后端时，只在那个后端内建立临时作用域。
3. 预处理消去变量后，目标沿同一 model converter 的定义按正向顺序代换。模型恢复顺序与目标代换顺序相反，这一点有专门回归测试。
4. 模型消费后撤销临时定义。合法的原生 assumptions 仍会按上游逻辑切换增量模式。

固定样本实验的 {s['prefix_checks']} 组检查全部一致：8 个输入 × 2 个种子 × native/observe/route 三种对照，比较模型来源与完整原变量赋值。random 未达到 20 个样本的运行比较共同前缀，不冒充完整 20 个样本测试。空接入一致证明原有接入扰动被移除；真正增加定义和偏好后，内部预处理、搜索以及 CCSS 的种子仍会受到影响。

## 不可翻转位的证据与缓存

静态分析计算精确模 2^k 同余和原公式蕴含的整数上下界，再推导固定 bit。在线查询只针对剩余的一个目标：`原公式 AND Reach AND 目标位值`。只有 UNSAT 会加入永久排除缓存。验证器使用独立上下文，绝不加入本轮继承的历史赋值。

30 秒实验的 soft 组按输入、节点、位去重后，共记录 **{static} 个静态固定 bit**，另有 **{unsat} 个经 UNSAT 证明不可达的方向**。这是已发现的集合，不是对所有不可能位的穷尽判定。历史掩码和官方覆盖率分母保持不变。超时、unknown、没有搜到目标都不会被视为“不可能”。

在线验证 timeout 为 5ms/次，累计调度预算为 min(0.5 秒, 总预算的 2%)；实际构建和查询耗时计入采样总时间。已启动构建会有小幅超出调度额度的可能，pb 本轮平均约 0.506 秒。记录在各运行的 `impossible.jsonl`。

## 实验与验证

在 8 个注册输入、种子 0/1 上完成 80 次 30 秒实验和 96 次固定 20 样本实验，共 **176 次正式运行**。8 个进程固定在不同物理核，每个采样进程仍为单线程；编译与离线审计均未与采样重叠。定时实验包含 baseline、route、soft_unfiltered、soft_static、soft；固定样本实验增加 native/observe，省略 soft_static。

两组实验共独立检查 **{s['models_audited']:,} 个交付模型**，全部合法、原变量投影正确、不同且按时；在线覆盖、历史参考方向、原节点访问和目标位值均与未修改的官方指标一致。排除结论由未修改上游 Z3 重新验证，并检查后续目标不再选中已经排除的方向；共复核 {s['exclusion_certificates']} 条去重后的结论记录（各实验组分别去重）。

单元验证包括 8,487 个位分解检查、6 个协调/冲突场景、12 次后端选择检查、773 个 Reach 检查、6,240 个数学事实检查，以及 UNSAT 缓存、历史赋值不污染证明、预算耗尽不能判不可能。实际二进制、动态库和实验保存的实现源码哈希全部一致。

## 30 秒净效果

以下为两种种子的平均值，覆盖率仍使用完整原始指标；“过滤贡献”比较 soft 与同样已修复路径的 soft_unfiltered。''',
(ROOT/'results/v4_tables.zh.md').read_text(),
f'''8 个输入等权平均覆盖率变化为 **{s['mean_soft_delta_pp']:+.5f} 个百分点**。不能据此声称软指引整体性能提升；两种种子、30 秒只是本轮工程验证范围，也不代表统计显著性。

固定 20 样本的 soft 比较共有 {len(completed)} 对完整结果：{wins} 对覆盖增加、{losses} 对减少、{ties} 对相同。其余 {len(pairs)-len(completed)} 对未达到 20 个样本，不计入等样本胜负。

## 当前瓶颈与继续优化的依据

- 过滤确实消除了大量无效干预：CAV 的平均样本数由修复路径但不筛除时的 2,030 提升到 5,835，接近基线 5,940；dillig 从 4,601 到 10,255，接近基线 10,334。主要作用是收回无效干预的成本，而非增加这些实例最终已饱和的覆盖。
- convert 的 soft 平均只有 14 个模型，基线为 606.5。种子 0 的准备时间合计约 0.107 秒、CDCL 检查约 0.199 秒，但第 4 次与第 5 次 CDCL 查询之间间隔约 29.025 秒；种子 1 也有约 29 秒的类似间隔。从宿主控制流与交付记录看，这段耗时集中在 CCSS 及其模型处理阶段。仅静态过滤也退化，因此不能把这个损失归咎于在线 UNSAT 检查的几毫秒开销。
- 这说明“更有希望补覆盖的 CDCL 模型”未必是“让完整 HighDiv 后续采样更快的种子”。下一步应首先隔离测量软指引模型作为 CCSS 初始赋值的影响，并给后续局部搜索设置可比较的阶段预算/恢复策略；评价整条 CDCL→CCSS 链的单位时间净覆盖。仅继续增加目标数或增大求解预算，缺少本轮证据支持。
- real/random 的在线验证大多为 unknown；这些位被保留，没有误筛。可以进一步增加廉价的约束传播/同余推导，但仍需用原公式依据保证安全，不能把继承赋值造成的暂时不可行当成永久不可能。

默认仍为 ESG_MODE=native；显式 ESG_MODE=soft 启用本轮机制。soft_unfiltered 和 soft_static 保留用于消融。报告未把整体性能尚未改善包装成成功提速。

## 文件

- `include/session.hpp`：目标调度、模式及查询生命周期。
- `include/impossible.hpp`：固定 bit 推导、原公式探测、缓存及证据日志。
- `kernel/tactic.inc`、`kernel/prepare.inc`、`kernel/decide.inc`：目标传输、准备及普通可回溯决策。
- `scripts/prepare.py`：由冻结上游重建补丁，含 combined/tactic 两条接入路径。
- `results/v4_summary.json`、`results/v4_diagnostics.json`、`results/v4_final_verification.json`：汇总、时间诊断与最终核对。
- `results/comparison_v4_t30`、`results/comparison_v4_n20`：逐运行模型、查询日志、排除记录、官方审计和源码快照。

复现命令见 README.zh.md。''']
write(ROOT/'REPORT_v4.zh.md','\n\n'.join(lines)+'\n')
print('wrote REPORT_v4.zh.md')
