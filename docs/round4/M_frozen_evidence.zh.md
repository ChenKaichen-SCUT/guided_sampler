# M 阶段结果冻结

仅执行预定的 6 个 seed=0 短会话；全部正常到达 CDCL 次数上限。实现提交 5df5eec，未修改历史 HighDiv 或重跑基线。S 尚未实现。

新增映射的实际原子独立 XOR 检查为 16/16 UNSAT，无原公式背景，因此不是利用原公式矛盾得到空真。两主实例在首个正式模型之后分别出现 39（random 两模式合计）和 89（real）次当前单侧需求映射事件。M_apply 的新规则实际相位改变为 random 6 次、real 2 次。convert 无新增门映射。

官方目标审计：random observe/apply 的目标记录新增覆盖为 15/10，real 为 23/34；convert 为 0/0。这些是 action-target 记录数，不能作为全局唯一覆盖量或相位改变的因果收益。observe 的自然命中必须保留。random apply 有 4 个 action 的完整链因有界事件缓冲溢出而为 Unknown。其余断点及理论、模型、官方 Reach 的逐项核验见 analysis/M。

按事前冻结顺序选取 6 个新映射需求，分别进行 F+G 与 F+inherited+G 的 2 秒独立检查，总共 12 次：4 SAT、2 UNSAT、6 Unknown。各个 SAT 均经过原式、精确位值及官方访问核验；不延长超时、不重试、不在线使用答案。两个条件中的 Unknown 不能解释为不可行；此清单来自 random，不能外推为全部映射或 real 的可行性结果。

两个主实例的 7 次 CCSS 全部 Unknown，8 次 CDCL 均无继承 assumptions。它们可检验映射和相位机制，不能单独证明软化继承的效果。convert 的 31 次 CCSS 均 SAT，后续 CDCL 实际继承 470–532 个等式，适合验证软化的来源与成本。S 阶段保持原定矩阵和用户明确的配额：每 check 至多 4 次覆盖建议；参考偏好独立受前 64 次普通决策窗口约束。

完整原始模型、负结果、Unknown、日志、SMT2 检查与选取清单将在本轮归档中保留。机器可读汇总为 results/round4/analysis/M_summary.json。
