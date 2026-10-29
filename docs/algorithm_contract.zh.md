# 冻结边界

采用用户给定的两份协议，参数文件为 configs/round1.json。
不改变 hybrid 调度、cdcl_epoch=1、fixed_var_pct=0.5、原 RNG、预处理和模型恢复。
共同测量修改仅涉及原变量投影、独立完整模型验证、截止/收据和日志。
A 只调整原生普通决策原子相位；B 的谓词在内核作为定义内部化，绝不作为必真 assertion 或 assumption。
安装元数据不切换 combined solver；tactic 后端不支持指导并记录。

正式运行前必须通过正确性门；目前处于开发阶段，尚未启动正式基线。
