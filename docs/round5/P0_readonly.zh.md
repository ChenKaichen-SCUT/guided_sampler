# 实现前只读复核

完整流式读取第四轮归档，2659 个成员与当前恢复文件逐一 SHA 匹配；实际应用补丁的 Release 源树与冻结 manifest 匹配。未执行历史二进制、未新增求解。

官方访问器从全部正式原变量模型重算得到：random 全式净差 -94，其中 G1 +78、G2 -160、G3 -12；real 全式 -264，其中 G1 -37、G2 -219、G3 -8。集合互斥且完整，逐位差异、另一侧访问及纯值诊断、全部共同正式前缀、convert 前4个 CDCL 和共同墙钟点均另存。convert 完整37比5模型为 G1 +140、G2 -8388、G3 0，不解释为等样本性能差异。原节点和 NOT 仍是不同官方观察点。

实际覆盖额度：convert Support 5、Avoid 0；random Support 6、Avoid 10；real Support 7、Avoid 17。random Avoid 的10次均改变原生相位；real Avoid 的17次中15次改变、2次同相位仍计额。Support 改相位分别为4、4、3。两个主实例没有参考，因此这些改变也与同状态局部回退不同。

在记录到的64窗口内，没有重算出“额度已满、仍有去重后support目标”的候选。不能根据大量展开的avoid目标记录宣称挤占有效support。real 另有5次原始评分有偏好但去重后目标为空；本轮不更改先评分后去重顺序。

旧日志没有每次拒绝的精确成本/暴露守卫状态、完整早退记录、内部交换map/生产者和CCSS R0–R3。缺项统一为 not_recorded；局部回退与去重状态明确标记 recomputed_from_frozen_prefix，不冒充 S_ref 整条反事实轨迹。

输入源 SHA、分区及额度明细见 results/round5/readonly。该证据先于 support-only 实现冻结。
