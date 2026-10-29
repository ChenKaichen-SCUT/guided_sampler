# 归档后的只读分析

这些表从冻结审计与原始日志生成，不修改采样器、参数、计划或正式证据。
`time900_main.csv`与`n100_t900_main.csv`分别是32行完整主表；
`paired_comparisons.csv`给出逐实例的五组消融差值。
`time900`中的第100模型时间仅是时间任务的前缀，不是独立100模型任务。
AUC是900秒区间覆盖曲线面积除以900，单位为百分比；100模型模式提前结束后
保持终点覆盖的扩展AUC不是本轮主要比较指标。

`mechanism_main.csv`为48项引导运行提供统一列。窗口计数是重复入窗次数，
`distinct_selected_targets`才是不同目标数。low为bit 0–15（含Bool的bit 0），
mid为16–47，high为48–63。`window_a_static_match`是至少有一个静态匹配的
入窗次数；`a_live`是逐check绑定计数，均非不同原子总数。
`b_internalized`、`b_relevant`也为逐check累计，可重复涉及同一个目标。
`native_registered_targets`记录原生队列候选，broker可能随后替换该候选。
终点单侧位数由`new_observed - 2 * covered`精确计算，包含常量；并非可选目标队列长度。

`mechanism_details.json`按实际决策事件连接同一check的正式CDCL收据。
目标命中/新观察不表示该目标独立造成整个模型的覆盖收益。
无正式模型不能解释为不可达；算术Unknown、重复、迟到等都可能造成该结果。
本轮没有记录逐目标的全部回溯放弃次数，也未把已传播目标细分为
固定assumptions冲突/其他赋值。因此对应CSV列明确为`not_recorded`；
不能用`propagated`、最终未命中或Unknown次数代替这些指标。
受控测试验证了不可行目标可回溯和解除固定后重试，未补跑正式任务。

生成：恢复原始结果后，先`python3 scripts/summarize_round.py`，再
`python3 scripts/enrich_report.py`及`python3 scripts/summarize_mechanisms.py`。
不能重新运行会独占创建文件的正式调度/审计脚本来覆盖证据。
