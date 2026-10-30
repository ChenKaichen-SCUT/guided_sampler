# 第三轮只读语义追踪钩子

基线为 `2f839861acf0a8cec78e05dac256b98b0dc30099`；第二轮源文件、补丁和构建产物保留不变。`scripts/patch_round3_diagnostics.py` 先在临时目录应用第二轮 A-only 补丁，再加入本轮观测，按内容差异写入独立第三轮源码目录。Release 与 ASan/UBSan 使用各自独立的库、前缀和构建目录。

## 原生位置与观测目的

| 实际编译位置 | 原生位置 | 记录 |
|---|---|---|
| `z3/src/smt/a_context.inc` | `apply_A_phase_hint` | 前 64 个普通决策的轻量键；至多 4 个建议；受控原子引用、原生/建议/有效极性和原节点支持 |
| `z3/src/smt/smt_context.cpp` | `assign_core` / `unassign_vars` | 每次赋值新 token；决策/传播来源；撤销；层级与 trail |
| 同上 | `relevant_eh` / `pop_scope_core` | 相关性转移、相关性恢复后回溯状态 |
| 同上 | 两个原生 atom queue enqueue 点和 `propagate_atoms` | 入队、消费；等式与其他理论原子分别记录 |
| 同上 | `propagate_bool_var_enode` | Bool enode 传递 |
| 同上 | `add_eq/add_diseq` 的原子消费调用点 | 等式合并、不等式加入；并不把其他来源的合并冒认为该相位的效果 |
| 同上 | `push_new_th_eq/diseq`、`propagate_th_eqs/diseqs` | 同步产生的理论队列项与实际 delivery；因果关联不完整时保留 unknown |
| 同上 | 原有 `get_model` 结束点 | 实际 `M_leaf`；从未额外调用 `get_model` |
| `z3/src/smt/tactic/smt_tactic_core.cpp` | 原有模型导出点 | 由该 context 给出明确提供者编号，而不是取共享 Run 中“最后一个”叶子 |
| `z3/src/tactic/goal.*`、`tactic.cpp` | goal 复制与真正的 converter 调用路径 | 获胜 goal 的提供者、实际 converter display、链 ID |
| `z3/src/api/api_solver.cpp` | 原有模型导出在 compress 之后 | 交给调用者的实际 `M_outer`；仅与同 manager、同提供者的持有引用比较 |
| `include/round3/session.hpp` | 原有 commit 投影与收据路径 | `M_original` 的独立补全信息，`M_formal` 的正式收据，CDCL 前覆盖快照 |
| `z3/src/util/util.h` | 原有 `random_gen::operator()` | 仅测试环境变量打开时记录原生 RNG 的单次原始状态更新；没有新增随机抽取 |

实现主体为 `src/round3/semantic_context.inc` 和 `src/round3/semantic_trace.h`，后者被安装为 `z3/src/model/semantic_trace.h` 以符合 Z3 组件依赖层次。新版动作字段称为 `final_internal_assignment`；旧日志不改名、不重写。

## 所有权与界限

`PendingSemanticSnapshot` 持有所属 manager 的 `expr_ref_vector`。persistent 内核 detach 后保留待导出快照；临时内核在原有模型导出时求值。跨 manager 的指针不交给宿主；同原始 manager 的快照可保留到正常 `M_outer` 导出。快照使用 Run 的弱引用，避免与 Run 所持快照形成环。下一查询、pop/reset、取消/异常 detach 和析构清理待导出状态；它不再是 active guidance。

每查询最多 4 个建议；每实例最多 8 个最早不同键的未映射代表（由 observe 会话采集）。每后端缓冲至多 8192 个事件，理论关联表也有上限。实际 generic model converter 的 add/hide 操作另存 origin、声明身份和精确替换定义，每链最多 1024 项/1 MiB，超限显式标记。converter 字符流在 256 KiB 截断，明确记录 overflow；不存在先构造无限字符串再截断的步骤。原始 AST 节点字典只保留结构、sort、声明身份和叶子的打印内容，复杂原式来自冻结输入。

所有模型先不补全求值；undef 保留为 unknown，只在模型副本上补全。四层不是四次求解，亦不把内部赋值拷贝成模型真值。没有独立恢复的辅助声明/转换定义时，原变量空间的原子求值和映射证明都降为 unknown。

本轮覆盖 watched 原子的直接原生消费入口；EUF 间接合并到其他理论变量的完整因果来源仍可能不可恢复。日志明确区分“最终 token 未观察到直接传递”与“所有理论影响均已排除”，后者不由这些日志自动得出。事件溢出也不得被解释为未传播。

## 路由及资源控制

D1 的相位仍由第二轮规则决定，不修改窗口 64、每查询配额 4、45 秒显式预算/查询暴露预算、HighDiv 路由、CCSS、原生变量选择或断言。新增 CDCL 查询上限在当前模型正常提交之后检查，不把最后一个合法模型误丢弃。诊断墙钟开销不用于性能结论。只读追踪环境变量关闭时不建立语义快照；测试用 RNG 记录环境变量在六项实验中关闭。
