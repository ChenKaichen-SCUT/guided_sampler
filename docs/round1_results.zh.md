# Guided Sampler 第一轮结果

实际启动：64/64；正式会话记录：64/64；独立审计通过：64/64。全部 seed=0。基线是共同 Release 编译、原变量投影和截止测量适配的完整 HighDiv。


## 对五个研究问题的直接回答

1. **固定900秒没有总体净收益。** 八例等权平均相对完整HighDiv：A −0.069364、B −0.326116、AB −0.391081 个百分点。convert退步最明显；B/AB只在pb2010分别增加62/66个covered bit，原脚本两位小数仍显示4.13%。
2. **严格100模型均完成，但收益小且耗时增加。** 32个独立数量任务均达到100，各配置均为8/8；平均覆盖差分别为 A +0.058810、B +0.114757、AB +0.078102 个百分点。不存在本轮未完成100的配置。prime-cone从基线0.917秒增至B的113.528秒、AB的157.049秒；不能只报告小幅覆盖差而忽略吞吐。
3. **A-only没有实际相位介入。** A-only全部16项的A机会为0，其终点差异不能作为A软相位有效的证据。AB中A只有30次机会、28次实际改相位。B-only有9,466次显式目标尝试，AB有6,540次；B机制确实进入了搜索，但不代表具有净性能收益。AB的严格100模型均值还低于B-only，本轮没有证据证明组合成本值得。
4. **主要失败包括接入面不足、算术Unknown和持续搜索成本。** SMT_random与SMT_real两个实例的CDCL一直走不支持指导的tactic分支，A/B实际介入均为0。其端到端差异不能归因为目标决策。其他若干实例在B后反复返回`(incomplete (theory arithmetic))`；例如B-only的Bromberger有254次、CAV有1,503次、dillig有1,651次、prime-cone有238次，相关check分别累计约883、753、858、890秒。B-only/AB的已注册目标相关literal被原生队列取作候选累计约524万/615万次（随后仍可能由broker仲裁），远多于显式B尝试；5%的显式准备额度不能限制整个后续搜索成本。
5. **受控正确性与正式模型审计通过，适用范围仍有限。** 默认路由未被注册操作强制切换；原生CCSS、随机调用和变量固定主流程保留，关闭模式决策与模型轨迹一致。小有限问题投影保解、不可行目标回溯、取消/pop/reset等测试通过。全部正式模型再次通过官方Manual求值和原式精确代入，在线/离线覆盖增量一致；这些是工程证据，不是对所有LIA公式的形式化证明。

A-only及不支持后端运行中的差异只作为端到端观测保留。目录/表达式构造、墙钟限制与并发负载可能影响后续执行；本轮没有独立隔离这些因素，不能把差异解释为未发生的相位/目标干预。

完整逐实例主表另见 `results/analysis/time900_main.csv` 和 `results/analysis/n100_t900_main.csv`，包含首模型时间、AUC、CDCL/CCSS来源、状态、精确bit差和百分点差。`results/analysis/mechanism_details.json` 将实际目标尝试连接到同一查询的正式CDCL模型，分别记录Reach、目标命中、新目标观察、无正式模型和Unknown原因；不重复分配整个模型的gain。

**检测限制：** ASan/UBSan通过时保留一个已独立复现的上游32字节泄漏精确例外，详见 `sanitizer_exception.zh.md`。未关闭一般泄漏检查。成本停用后的原定义和学习历史仍存在；部分累计成本超过45秒，包含不可分操作超额和继续保留的观察/被动诊断，不表示重新开启指导额度。

**下一轮建议：** 先定位已有原子绑定/遇到率与SMT_random/SMT_real的后端覆盖，再对大模数目标触发的算术不完整性和历史代理成本做专门正确性与机制诊断。本轮不自动改参数、追加seed或重跑HighDiv。

## 固定 900 秒

单元格为官方覆盖率；精确 covered/total；正式模型数。

| 实例 | HighDiv | A | B | AB |
|---|---|---|---|---|
| 20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 96.38%；16330/16943；n=63432 | 96.38%；16330/16943；n=64805 | 96.3%；16316/16943；n=310 | 96.33%；16321/16943；n=249 |
| CAV_2009_benchmarks_problem__019.smt2 | 78.4%；8960/11429；n=71215 | 78.4%；8960/11429；n=68075 | 78.4%；8960/11429；n=1528 | 78.4%；8960/11429；n=1326 |
| SMT_random_LIA_ex14600_2600_100.smt2 | 12.9%；13501/104639；n=235 | 12.87%；13465/104639；n=247 | 12.89%；13485/104639；n=216 | 12.89%；13485/104639；n=225 |
| SMT_real_LIA_ex8500_2400_100.smt2 | 11.57%；7641/66061；n=1432 | 11.56%；7635/66061；n=1456 | 11.55%；7631/66061；n=1289 | 11.54%；7625/66061；n=1332 |
| convert_convert-jpg2gif-query-1459.smt2 | 26.42%；47370/179302；n=4767 | 25.91%；46453/179302；n=2861 | 23.92%；42887/179302；n=685 | 23.38%；41918/179302；n=467 |
| dillig_40-10.smt2 | 93.84%；47593/50715；n=90131 | 93.84%；47593/50715；n=83836 | 93.84%；47593/50715；n=1659 | 93.84%；47593/50715；n=1544 |
| pb2010_normalized-j3048_8-sat.smt2 | 4.13%；58452/1416258；n=1142 | 4.13%；58452/1416258；n=1109 | 4.13%；58514/1416258；n=843 | 4.13%；58518/1416258；n=1026 |
| prime_cone_sat_14.smt2 | 83.4%；14383/17246；n=82032 | 83.4%；14383/17246；n=82436 | 83.4%；14383/17246；n=254 | 83.4%；14383/17246；n=210 |

## 独立 100 模型／最多 900 秒

每个单元格为实际模型数、是否完成 100、到达时间、官方终点覆盖。未完成者不作为 C100。

| 实例 | HighDiv | A | B | AB |
|---|---|---|---|---|
| 20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | n=100；完成；1.208s；96.32% | n=100；完成；1.207s；96.32% | n=100；完成；82.678s；96.27% | n=100；完成；66.848s；96.29% |
| CAV_2009_benchmarks_problem__019.smt2 | n=100；完成；1.161s；78.4% | n=100；完成；1.148s；78.4% | n=100；完成；14.301s；78.4% | n=100；完成；14.537s；78.4% |
| SMT_random_LIA_ex14600_2600_100.smt2 | n=100；完成；375.684s；12.78% | n=100；完成；419.633s；12.75% | n=100；完成；410.330s；12.8% | n=100；完成；288.607s；12.8% |
| SMT_real_LIA_ex8500_2400_100.smt2 | n=100；完成；57.441s；10.93% | n=100；完成；62.833s；11.15% | n=100；完成；70.027s；11.19% | n=100；完成；67.526s；11.19% |
| convert_convert-jpg2gif-query-1459.smt2 | n=100；完成；6.368s；21.24% | n=100；完成；10.256s；21.52% | n=100；完成；141.140s；21.89% | n=100；完成；76.425s；21.58% |
| dillig_40-10.smt2 | n=100；完成；0.933s；93.84% | n=100；完成；0.954s；93.84% | n=100；完成；8.209s；93.84% | n=100；完成；10.428s；93.84% |
| pb2010_normalized-j3048_8-sat.smt2 | n=100；完成；40.792s；3.99% | n=100；完成；46.815s；3.99% | n=100；完成；112.815s；4.04% | n=100；完成；109.939s；4.04% |
| prime_cone_sat_14.smt2 | n=100；完成；0.917s；83.4% | n=100；完成；0.891s；83.4% | n=100；完成；113.528s；83.4% | n=100；完成；157.049s；83.4% |

## 差值与完成率

以各实例原分母归一化后等权平均百分点；不将 bit 数直接合并为总体增益。

### time900

- a_only − highdiv：8例实际终点均值 -0.069364 个百分点；退步实例：SMT_random_LIA_ex14600_2600_100.smt2、SMT_real_LIA_ex8500_2400_100.smt2、convert_convert-jpg2gif-query-1459.smt2。
- b_only − highdiv：8例实际终点均值 -0.326116 个百分点；退步实例：20180326-Bromberger_v45_problem__003.smt2.slack.smt2、SMT_random_LIA_ex14600_2600_100.smt2、SMT_real_LIA_ex8500_2400_100.smt2、convert_convert-jpg2gif-query-1459.smt2。
- a_plus_b − highdiv：8例实际终点均值 -0.391081 个百分点；退步实例：20180326-Bromberger_v45_problem__003.smt2.slack.smt2、SMT_random_LIA_ex14600_2600_100.smt2、SMT_real_LIA_ex8500_2400_100.smt2、convert_convert-jpg2gif-query-1459.smt2。
- a_plus_b − a_only：8例实际终点均值 -0.321717 个百分点；退步实例：20180326-Bromberger_v45_problem__003.smt2.slack.smt2、SMT_real_LIA_ex8500_2400_100.smt2、convert_convert-jpg2gif-query-1459.smt2。
- a_plus_b − b_only：8例实际终点均值 -0.064965 个百分点；退步实例：SMT_real_LIA_ex8500_2400_100.smt2、convert_convert-jpg2gif-query-1459.smt2。
### n100_t900

- a_only − highdiv：双方严格完成100的实例 8/8；该子集平均 +0.058810 个百分点。
- a_only − highdiv：8例实际终点均值 +0.058810 个百分点；退步实例：SMT_random_LIA_ex14600_2600_100.smt2。
- b_only − highdiv：双方严格完成100的实例 8/8；该子集平均 +0.114757 个百分点。
- b_only − highdiv：8例实际终点均值 +0.114757 个百分点；退步实例：20180326-Bromberger_v45_problem__003.smt2.slack.smt2。
- a_plus_b − highdiv：双方严格完成100的实例 8/8；该子集平均 +0.078102 个百分点。
- a_plus_b − highdiv：8例实际终点均值 +0.078102 个百分点；退步实例：20180326-Bromberger_v45_problem__003.smt2.slack.smt2。
- a_plus_b − a_only：双方严格完成100的实例 8/8；该子集平均 +0.019291 个百分点。
- a_plus_b − a_only：8例实际终点均值 +0.019291 个百分点；退步实例：20180326-Bromberger_v45_problem__003.smt2.slack.smt2。
- a_plus_b − b_only：双方严格完成100的实例 8/8；该子集平均 -0.036656 个百分点。
- a_plus_b − b_only：8例实际终点均值 -0.036656 个百分点；退步实例：convert_convert-jpg2gif-query-1459.smt2、pb2010_normalized-j3048_8-sat.smt2。
完成100实例数：highdiv=8/8；a_only=8/8；b_only=8/8；a_plus_b=8/8。

## 实际机制与成本

下表是实际普通决策次数；A 同相位建议也计为机会，实际改相位另列。目标命中不被重复归因为该目标独立造成全部模型收益。

| 配置／模式／实例 | A机会／改变 | B尝试 | 不支持后端 | 显式成本秒 | 状态 |
|---|---:|---:|---:|---:|---|
| a_only/time900/20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 0/0 | 0 | 0 | 35.775554615999546 | deadline |
| a_only/time900/CAV_2009_benchmarks_problem__019.smt2 | 0/0 | 0 | 0 | 38.00321551799979 | deadline |
| a_only/time900/SMT_random_LIA_ex14600_2600_100.smt2 | 0/0 | 0 | 247 | 0.57681561 | deadline |
| a_only/time900/SMT_real_LIA_ex8500_2400_100.smt2 | 0/0 | 0 | 1456 | 2.6292322059999944 | deadline |
| a_only/time900/convert_convert-jpg2gif-query-1459.smt2 | 0/0 | 0 | 0 | 8.117251388999971 | deadline |
| a_only/time900/dillig_40-10.smt2 | 0/0 | 0 | 0 | 48.30589169099909 | deadline |
| a_only/time900/pb2010_normalized-j3048_8-sat.smt2 | 0/0 | 0 | 0 | 12.661237998000031 | deadline |
| a_only/time900/prime_cone_sat_14.smt2 | 0/0 | 0 | 0 | 35.296264392999554 | deadline |
| a_only/n100_t900/20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 0/0 | 0 | 0 | 0.04805564100000003 | complete100 |
| a_only/n100_t900/CAV_2009_benchmarks_problem__019.smt2 | 0/0 | 0 | 0 | 0.055993179000000004 | complete100 |
| a_only/n100_t900/SMT_random_LIA_ex14600_2600_100.smt2 | 0/0 | 0 | 99 | 0.2215513059999999 | complete100 |
| a_only/n100_t900/SMT_real_LIA_ex8500_2400_100.smt2 | 0/0 | 0 | 99 | 0.15706780700000006 | complete100 |
| a_only/n100_t900/convert_convert-jpg2gif-query-1459.smt2 | 0/0 | 0 | 0 | 0.28377167100000006 | complete100 |
| a_only/n100_t900/dillig_40-10.smt2 | 0/0 | 0 | 0 | 0.061612803 | complete100 |
| a_only/n100_t900/pb2010_normalized-j3048_8-sat.smt2 | 0/0 | 0 | 0 | 1.0622576379999995 | complete100 |
| a_only/n100_t900/prime_cone_sat_14.smt2 | 0/0 | 0 | 0 | 0.037996774000000025 | complete100 |
| b_only/time900/20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 0/0 | 721 | 0 | 3.940358258999995 | deadline |
| b_only/time900/CAV_2009_benchmarks_problem__019.smt2 | 0/0 | 3438 | 0 | 29.41443214700003 | deadline |
| b_only/time900/SMT_random_LIA_ex14600_2600_100.smt2 | 0/0 | 0 | 216 | 11.264771776000003 | deadline |
| b_only/time900/SMT_real_LIA_ex8500_2400_100.smt2 | 0/0 | 0 | 1289 | 25.60861696999989 | deadline |
| b_only/time900/convert_convert-jpg2gif-query-1459.smt2 | 0/0 | 386 | 0 | 24.761065453999976 | deadline |
| b_only/time900/dillig_40-10.smt2 | 0/0 | 3511 | 0 | 26.427289238999997 | deadline |
| b_only/time900/pb2010_normalized-j3048_8-sat.smt2 | 0/0 | 79 | 0 | 53.627812309000205 | deadline |
| b_only/time900/prime_cone_sat_14.smt2 | 0/0 | 708 | 0 | 4.384002641000003 | deadline |
| b_only/n100_t900/20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 0/0 | 86 | 0 | 1.0184657799999999 | complete100 |
| b_only/n100_t900/CAV_2009_benchmarks_problem__019.smt2 | 0/0 | 88 | 0 | 1.547874342 | complete100 |
| b_only/n100_t900/SMT_random_LIA_ex14600_2600_100.smt2 | 0/0 | 0 | 99 | 5.565233293 | complete100 |
| b_only/n100_t900/SMT_real_LIA_ex8500_2400_100.smt2 | 0/0 | 0 | 99 | 3.8548258689999986 | complete100 |
| b_only/n100_t900/convert_convert-jpg2gif-query-1459.smt2 | 0/0 | 58 | 0 | 3.516068854 | complete100 |
| b_only/n100_t900/dillig_40-10.smt2 | 0/0 | 140 | 0 | 1.5162316180000013 | complete100 |
| b_only/n100_t900/pb2010_normalized-j3048_8-sat.smt2 | 0/0 | 78 | 0 | 45.30464330700003 | complete100 |
| b_only/n100_t900/prime_cone_sat_14.smt2 | 0/0 | 173 | 0 | 1.0692726230000003 | complete100 |
| a_plus_b/time900/20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 0/0 | 351 | 0 | 3.3949077449999976 | deadline |
| a_plus_b/time900/CAV_2009_benchmarks_problem__019.smt2 | 4/3 | 2130 | 0 | 25.30898407400007 | deadline |
| a_plus_b/time900/SMT_random_LIA_ex14600_2600_100.smt2 | 0/0 | 0 | 225 | 11.35356716600001 | deadline |
| a_plus_b/time900/SMT_real_LIA_ex8500_2400_100.smt2 | 0/0 | 0 | 1332 | 26.359667122000015 | deadline |
| a_plus_b/time900/convert_convert-jpg2gif-query-1459.smt2 | 13/13 | 272 | 0 | 16.513382105000012 | deadline |
| a_plus_b/time900/dillig_40-10.smt2 | 9/8 | 2660 | 0 | 23.61422717700001 | deadline |
| a_plus_b/time900/pb2010_normalized-j3048_8-sat.smt2 | 0/0 | 75 | 0 | 53.582581644000044 | deadline |
| a_plus_b/time900/prime_cone_sat_14.smt2 | 0/0 | 401 | 0 | 3.5350484659999983 | deadline |
| a_plus_b/n100_t900/20180326-Bromberger_v45_problem__003.smt2.slack.smt2 | 1/1 | 104 | 0 | 1.0253805229999997 | complete100 |
| a_plus_b/n100_t900/CAV_2009_benchmarks_problem__019.smt2 | 0/0 | 88 | 0 | 1.6183373219999997 | complete100 |
| a_plus_b/n100_t900/SMT_random_LIA_ex14600_2600_100.smt2 | 0/0 | 0 | 99 | 4.009178961000005 | complete100 |
| a_plus_b/n100_t900/SMT_real_LIA_ex8500_2400_100.smt2 | 0/0 | 0 | 99 | 3.8082034449999997 | complete100 |
| a_plus_b/n100_t900/convert_convert-jpg2gif-query-1459.smt2 | 3/3 | 59 | 0 | 3.0959653669999985 | complete100 |
| a_plus_b/n100_t900/dillig_40-10.smt2 | 0/0 | 138 | 0 | 1.4808034040000002 | complete100 |
| a_plus_b/n100_t900/pb2010_normalized-j3048_8-sat.smt2 | 0/0 | 81 | 0 | 45.22588860800003 | complete100 |
| a_plus_b/n100_t900/prime_cone_sat_14.smt2 | 0/0 | 181 | 0 | 1.067404149 | complete100 |

## 正确性、限制与证据

- Release、ASan/UBSan 测试、逐节点观察器差分和关闭行为证据位于 `results/correctness/`。
- 每个正式样本经过原式快照验证，离线再以官方 Manual 求值和原式精确代入交叉核对；在线增量与官方逐模型增量核对。
- `queries.jsonl` 的求解统计为累计快照，未冒充查询差分；阶段时间可能包含彼此，不能重复相加。
- 默认 combined solver 的 tactic 路径不支持指导；元数据安装本身不改变路由。CCSS 及原 HighDiv 随机流保留，指导不使用随机数。
- B 的历史定义可被原生队列再选择；撤销优先权不删除学习历史。窗口、内部化与实际决策分阶段记录。
- 初始16项同步释放，固定队列空槽补位；100模型提前完成会改变瞬时并发，因此不声称各配置负载完全相同。
- 只有一个seed、8个开发观察实例；不能推断显著性、稳定性或跨LIA泛化。零收益、未完成、Unknown和失败均保留。
- 完整差值、时间前缀、模型前缀、首模型时间、AUC、来源、路由、额度和资源信息保存在每项 `audit.json` 及 `results/summary.csv`。
- 原输入未额外公开；其哈希和已公开上游对应路径在 `manifests/inputs.json`。

如存在性能退步，本轮不追加seed、不改额度、不重跑唯一基线。下一轮应依据实际接入率、映射覆盖面与完整求解成本分别定位问题。


## 完整机制表与诊断缺口

[逐项机制表](../results/analysis/mechanism_main.csv)列出48项引导运行的终点单侧位数、窗口Bool/Int及低中高位分布、静态匹配与实际绑定、A机会与相位改变、B编码/内部化/实际尝试/最终命中、准备不完整、注册上限、成本停用、check成本及吞吐。[逐项消融](../results/analysis/paired_comparisons.csv)覆盖全部五组差值。计数口径见[分析说明](../results/analysis/README.md)。

本轮日志没有独立记录逐目标的全部回溯放弃次数，也没有将已传播目标细分为固定assumptions冲突或其他赋值。这两项不能从Unknown或最终未命中数量推算，机制表明确标记为`not_recorded`。对应可回溯性和解除固定后的重试由受控正确性测试验证，正式实验没有补跑。

39个归档分片与全部2680个成员的SHA-256及大小通过流式解压校验，见[归档验证](../archives/verification.json)和[恢复说明](../archives/RESTORE.md)。归档后补充的分析与最终报告直接随Git提交。
