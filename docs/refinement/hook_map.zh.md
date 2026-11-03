# 原生反馈与正式交付的数据流

实际第五/六轮构建通过生成树根目录 round5_include/session.hpp 或 round6_include/session.hpp 编译，不直接包含展示用 include/round4/soft_reference/session.hpp。新构建复制已冻结 HighDiv 到独立树，编译新 Session；保存 .d 依赖、编译命令及链接库 SHA，Z3 库沿用冻结第六轮的对应 Release/SAN 库。

| 边界 | 保留或拆分 |
|---|---|
| hybrid_sampling 首次参考资格 / check 分支 | num_samples 来自 native_count |
| CDCL get_model 后 | 原生提取、原生接纳与反馈；随后输出选择 |
| CCSS get_model / subgoal.convert_model | 仍在原位置恢复 m_ls，再记录参考来源，随后处理输出 |
| collect_inherited_reference | 仅读原 m_ls，保留 RNG 次数与顺序 |
| mk_values / last_CDCL_model | 原库不改；实际写入/消费照旧 |
| native unique / pending_outcomes / guidance ast.version | 只接纳原生模型，旧 action 命中只解释原生观察 |
| output unique / observations / formal | 只在及时确认的交付事务后推进 |
| limit / summary formal_count | 使用输出正式数量 |
| CPU/墙钟信用 | 只在 check、get_model、原 model converter 调用边界测量；排除宿主日志、改进、等待 |

数值改进器独立表达式表仅从原 AST 读取，不创建原 manager 表达式，不调用 solver.check 或修改 model；候选始终以当前原生赋值为锚点。真实外部硬条件单独保留并参与域与最终验证，当前 CLI 没有外部 assumptions。
