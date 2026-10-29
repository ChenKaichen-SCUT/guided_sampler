# 精确的上游 LeakSanitizer 例外

未过滤的 ASan/UBSan 内核测试发现一笔 32 字节泄漏。完整栈和原始失败保留在
`results/correctness/sanitize-unfiltered-upstream-leak/`。

独立程序 `tests/upstream_leak.cpp` 只调用标准 Z3 API，没有包含指导头文件，也没有
安装 A/B。它在同一检测库上对普通硬公式 `-20 <= x <= 20` 与
`mod(x,2^64) >= 2^63` 求解，即可复现相同 32 字节泄漏；将模数改为16时不泄漏。
原始日志、源码哈希核验在 `results/correctness/upstream-leak/`。

调用栈指向上游 `math/lp/dioph_eq.cpp::undo_fixed_column` 的复制构造。
该 region trail 对象保存未使用的 `const mpq m_fixed_val`，而 `undo()` 不销毁该值；
`trail_stack` 回滚只调用 undo 并回收 region。该源文件与指定上游逐字节一致。

按执行指引允许的“上游已存在问题＋独立复现＋精确例外”，仅启用
`tests/lsan-upstream.supp` 中这个具体复制构造函数的泄漏匹配。
`detect_leaks=1`、ASan 与 UBSan 检查仍开启；未屏蔽通用分配器、SMT 调用栈或新增模块。
因此最终报告应写“ASan/UBSan 通过，含此已复现的上游泄漏例外”，不能写无条件零泄漏。
