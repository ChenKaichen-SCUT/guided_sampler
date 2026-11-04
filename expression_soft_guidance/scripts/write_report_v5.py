import json,statistics
from prepare import ROOT,write
s=json.loads((ROOT/'results/v5_summary.json').read_text())
v=json.loads((ROOT/'results/v5_final_verification.json').read_text());assert s['all_passed'] and v['passed']
diag=json.loads((ROOT/'results/v5_diagnostics.json').read_text())
def short(b):
    for key in ['Bromberger','CAV','random','real','convert','dillig','pb','prime']:
        if key in b:return key
    return b
lines=['# 软指引 v5：CCSS 模型交换、阶段预算与关闭对照','',
'本轮在 v4 的原表达式部分 bit 软指引上处理 CCSS 的后续成本，没有引入旧 guided_sampler 的精修算法。HighDiv 原始目录和旧实现均保留，v4 的代码、库、二进制已归档到 `archive/v4`。','',
'## 改动与证据边界','',
'1. CCSS check 使用独立毫秒预算，覆盖内部准备、表达式映射、实例构建、初始化、搜索及内核模型生成。原生 solver timeout 与 179 处循环检查共同生效，循环检查每 64 次访问读取一次时钟，阶段切换强制检查。超时返回 unknown；恢复后下一轮可继续求解。模型转换、原公式验证和写出另计时间，仍执行总截止检查。',
'2. 新增完整模型交换：只在原变量投影通过原公式验证后，整体替换 CCSS 交换表，避免内部预处理留下部分变量或混入旧值。原生交换、对软目标查询暂存/恢复旧表，以及关闭 CCSS 都保留为显式对照。',
'3. CCSS 使用这个模型推导采样区间，再随机初始化；它并非原样从合法模型开始搜索。因此“交换模型合法完整”不能推出“CCSS 一定很快”。',
'4. 完整模型替换是启发式选择，不改变硬公式或输出合法性要求。重复合法模型可以更新种子，覆盖历史仍只接受已交付的不同模型。超时不是不可翻转位的证据，v4 的 F＋Reach 排除逻辑保持不变。','',
'## 实验设计','',
'先完成 30 次 10 秒预实验（convert、real、random；种子 0），比较 25/100/500ms、原生/完整/保留旧表、关闭 CCSS。随后完成 128 次 30 秒全输入实验（8 个注册输入 × 2 个种子 × 8 个配置），96 次固定 20 样本对照，以及 convert 上 16 次 60 秒复验（未用于预实验的种子 2/3/4/5）。',
'每次定时实验使用 8 个固定物理核并行，每个采样器为单线程；编译与离线审计没有和性能采样重叠。使用原始覆盖分母，不剔除不可达位以抬高分数。原生 CCSS 因整数 timeout 在最后不足 1 秒时停止启动新阶段；毫秒预算组可以利用剩余时间，所以另列前 29 秒结果，并提供相同基础设施的无指引对照。','',
'| 配置 | 软指引 | CCSS 单次预算 | 交换方式 |',
'|---|---|---|---|',
'| baseline | 无 | 原生 | 原生 |',
'| base_budget | 无 | 100ms | 原生 |',
'| base_complete | 无 | 100ms | 完整模型 |',
'| soft | v4 | 原生 | 原生 |',
'| soft_budget | v4 | 100ms | 原生 |',
'| soft_complete | v4 | 100ms | 完整模型 |',
'| soft_hold | v4 | 100ms | 有软目标时保留之前的表 |',
'| soft_off | v4 | 关闭 CCSS | 不再产生 LS→CDCL 继承 |','',
'## 30 秒覆盖与净收益','',
'下表为种子 0/1 的均值，单位为覆盖率百分比。两种带预算软指引必须分别与采用同样预算/交换的无指引组比较，才能区分基础设施修复和软目标本身的贡献。','',
'| 输入 | HighDiv | v4 软指引 | 仅加预算的软指引 | 完整交换软指引 | 同预算无指引 | 同预算/完整交换无指引 | 关闭 CCSS |',
'|---|---:|---:|---:|---:|---:|---:|---:|']
for r in s['time']:
    m=r['modes'];arms=['baseline','soft','soft_budget','soft_complete','base_budget','base_complete','soft_off']
    lines.append('| '+short(r['bench'])+' | '+' | '.join(f'{m[a]["coverage_percent"]:.5f}' for a in arms)+' |')
lines+=['',f'按输入等权，soft_budget 相比原 HighDiv 为 **{s["mean_budget_vs_original_pp"]:+.5f} 个百分点**，相比同预算无指引为 **{s["mean_budget_vs_matched_pp"]:+.5f} 个百分点**。soft_complete 对应为 **{s["mean_vs_original_pp"]:+.5f}** 和 **{s["mean_vs_matched_pp"]:+.5f} 个百分点**。这不是吞吐量提升百分比，也不表示所有输入都改善。','',
'| 输入 | HighDiv 样本 | v4 样本 | 仅加预算样本 | 完整交换样本 | 仅加预算：29 秒覆盖% | 完整交换：29 秒覆盖% | HighDiv：29 秒覆盖% |',
'|---|---:|---:|---:|---:|---:|---:|---:|']
for r in s['time']:
    m=r['modes'];lines.append(f'| {short(r["bench"])} | {m["baseline"]["models"]:g} | {m["soft"]["models"]:g} | {m["soft_budget"]["models"]:g} | {m["soft_complete"]["models"]:g} | {m["soft_budget"]["coverage_29_percent"]:.5f} | {m["soft_complete"]["coverage_29_percent"]:.5f} | {m["baseline"]["coverage_29_percent"]:.5f} |')
lines+=['','## convert 的阶段归因','',
'| 配置 | CCSS 平均耗时(s) | 最长单次 CCSS(s) | CDCL 平均耗时(s) | CCSS 直接补到的 bit 均值 | CDCL 直接补到的 bit 均值 |',
'|---|---:|---:|---:|---:|---:|']
conv=next(r for r in s['time'] if short(r['bench'])=='convert')
for a,m in conv['modes'].items():lines.append(f'| {a} | {m["ccss_wall"]:.4f} | {m["max_ccss"]:.4f} | {m["cdcl_wall"]:.4f} | {m["ccss_bits"]:g} | {m["cdcl_bits"]:g} |')
lines+=['','内核六阶段计时显示：v4 的长停顿主要位于 CCSS 搜索阶段，并非模型转换或初始化时间。25ms 预实验截断了较多本来能成功的调用；100ms 显著压缩长尾，同时保留大部分有效调用。CCSS 的覆盖增量是样本交付当时的归因，不代表删除该阶段后其他阶段仍会沿相同路径运行。',
'baseline 使用未修改内核，没有内部六阶段接口；对应零值是占位，不表示没有耗时。其总体 check 与阶段时间仍由宿主实测。deadline_hit 只表示新增检查点触发，不把其他来源的 unknown 都当作相同超时。',
'关闭 CCSS 后同时失去其样本、模型继承和原有调用序列，不能把它解释成只去掉空耗。real/random 的 CCSS 在本轮未交付样本，时间主要在 CDCL；仅处理 CCSS 不会消除这两类输入的主要瓶颈。','',
'## 新种子、60 秒复验','',
'| 种子 | HighDiv 覆盖% | 同预算无指引% | 仅加预算软指引% | 完整交换软指引% | 仅加预算软指引－同预算基线(pp) |',
'|---|---:|---:|---:|---:|---:|']
for r in s['confirmation']:
    m=r['modes'];lines.append(f'| {r["seed"]} | {100*m["baseline"]["coverage"]:.5f} | {100*m["base_budget"]["coverage"]:.5f} | {100*m["soft_budget"]["coverage"]:.5f} | {100*m["soft_complete"]["coverage"]:.5f} | {r["budget_vs_matched_pp"]:+.5f} |')
for a in ['soft_budget','soft_complete']:
    delta=[100*(r['modes'][a]['coverage']-r['modes']['base_budget']['coverage']) for r in s['confirmation']]
    lines.append(f'\n{a} 对同预算无指引的均值差为 {statistics.mean(delta):+.5f}pp；逐种子范围 [{min(delta):+.5f}, {max(delta):+.5f}]pp。'+('此处完整交换组还包含交换策略差异；其同交换无指引对照只在 30 秒主实验中提供。' if a=='soft_complete' else ''))
lines+=['','只有 8 个实例、主实验两个种子，以及 convert 的四个额外种子；不据此声称对整个 LIA 分布具有统计显著优势。完整交换和原生交换的胜负会随种子/时长变化，不能根据单轮结果固定宣称某种交换总是最好。','',
'## 等样本数与正确性','']
for control in ['baseline','base_complete']:
    rows=[r for r in s['sample_pairs'] if r['control']==control];complete=[r for r in rows if r['complete']]
    wins=sum(r['delta_bits']>0 for r in complete);loss=sum(r['delta_bits']<0 for r in complete)
    lines.append(f'soft_complete 相比 {control} 的 16 对固定 20 样本对照中，{len(complete)} 对完成；覆盖 {wins} 胜、{loss} 负、{len(complete)-wins-loss} 平。未完成的 {len(rows)-len(complete)} 对不作等样本收益判断。')
count=sum(r['runs'] for r in v['runs']);certs=sum(r['exclusion_certificates'] for r in v['runs']);over=max(r['max_ccss_overshoot_ms'] for r in v['runs']);phase=max(r['max_bounded_ccss_phase_seconds'] for r in v['runs'])
lines+=['',f'正式实验及复验共 **{count} 次运行、{s["models_audited"]:,} 个正式交付模型**，全部通过未修改 HighDiv 官方度量与未修改 Z3 的原公式验证；同时检查投影、去重、总截止、历史方向、原节点 Reach 和目标位值。共复验 {certs} 条排除结论（各套实验分别去重）。',
f'48 组 native/observe/route 对原 HighDiv 的共同模型前缀全部一致。单元测试通过，包括已有位语义与路径/排除检查，以及交换表替换、旧值清除、快照恢复和 8 轮 CCSS 超时后恢复检查。全部 {v["upstream_verified_files"]} 个冻结上游文件哈希未变；{v["patch_replay"]["compared"]} 个内核文件从冻结上游重新打补丁后与编译来源逐字节一致。实验二进制、动态库、实现源码快照均匹配。',
f'CCSS 协作预算在这些实验中的最大 check 超出量为 **{over:.3f}ms**。加上模型转换、原公式验证和交付，100ms 组中整个 CCSS 阶段的最长观测耗时为 **{phase*1000:.3f}ms**。这些额外成本计入总预算并拒绝总截止外的交付，但没有独立中断模型转换/交付；因此阶段并非严格的 100ms 硬上限。','',
'## 使用与后续方向','',
'保留 CCSS，并用 100ms 预算防止一次局部搜索耗尽整个采样窗口。原生交换与完整交换均保留开关；完整交换解决了部分/陈旧交换表问题，但本轮不足以证明它在所有输入上都更快。关闭 CCSS 可用于诊断，不建议作为全局默认。',
'下一步应处理预算释放后暴露的 CDCL 长尾：依据当前查询的实际耗时限制困难目标的连续占用，评估继承等式和软目标组合的求解成本。real/random 的主要成本本来就在 CDCL，应直接在那里做同预算对照。不要把 CCSS 优化的收益全部归因于软指引。','',
'```bash',
'# 原生交换＋100ms（保留未指定变量的现有规则）',
'ESG_MODE=soft ESG_CCSS_MS=100 ./bin/highdiv_soft -i INPUT -o OUTPUT -n 4294967295 -t 30 -s 0',
'# 完整合法模型交换',
'ESG_MODE=soft ESG_CCSS_MS=100 ESG_CCSS_FEEDBACK=complete ./bin/highdiv_soft -i INPUT -o OUTPUT -n 4294967295 -t 30 -s 0',
'```','',
'OUTPUT 目录须先建立。正式导出使用 `receipts.jsonl` 中 accepted=true 的模型；审计后读取 `accepted.samples`。完整复现实验命令见 `README.zh.md`；配置见 `scripts/profiles.py`。逐次数据位于 `results/comparison_v5_t30`、`results/comparison_v5_n20`、`results/confirmation_v5_t60`；汇总、诊断和完整性证明分别是 `results/v5_summary.json`、`results/v5_diagnostics.json`、`results/v5_final_verification.json`。']
write(ROOT/'REPORT_v5.zh.md','\n'.join(lines)+'\n');print('REPORT_v5.zh.md written')
