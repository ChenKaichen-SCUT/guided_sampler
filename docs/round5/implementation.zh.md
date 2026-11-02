# 第五轮实现与审计边界

`include/round5/coverage_policy.hpp` 是唯一新增评分选项：ReferenceOnly 不给覆盖建议；Full 与第四轮 lexicographic support/block 完全一致；SupportOnly 仅在两侧 support 不同时给建议。`src/round5/soft_phase.inc` 仍由原执行逻辑处理实际原生变量、NOT 极性、四次建议、64 决策窗口、参考回退、去重和暴露守卫。仅 block 差值时不消耗覆盖配额，也不写 attempted 集合。先评分后去重和同相位计额均保留。

生成脚本 `scripts/round5/patch_sources.py` 从冻结的第四轮源树与头文件生成独立构建覆盖层；未在版本库再复制全部历史实现。两个实际构建树位于 worktrees/round5_release、worktrees/round5_sanitize；补丁冻结同时核对两者对应源文件。单个宿主与库通过 CLI 配置选择三个模式。

DecisionAudit 在真实64窗口内记录原始分数、去重后可执行数量、配额前后、局部参考回退、成本/暴露检查时状态和实际选择；目标记录有4096上限及溢出标记。只有有完整证据、尚未赋值、仍有目标、守卫允许的额度拒绝才可归入 support_quota_only_blocked；局部回退不是整条 S_ref 轨迹。

`ccss_exchange_trace.hpp` 在原生写入之后旁路记录生产者，manager 以生命周期 generation 标识，析构删除旁路登记；不更改原生 map。消费入口复制完整 map 并保存来源。实际 map 只按 key 查找，没有依赖其遍历顺序的生产路径；JSON 排序仅作用于副本。

`ccss_probe.inc` 与生成的 sampler.cpp 一起编译，记录 constructor seed/R0、原始 build_lits 顺序与输入子句、R1/R2/R3、原生中间区间、溢出/缺项、初始化值及有界搜索进度。变量/literal/clause、closure、差分 pair、reconstruction stack 和相关查表结构一起导出。只读到初始化过或实际使用的字段；没有 LIA literal 时未初始化且不被使用的 most-lits 索引显式排除，不读取未定义数据。

RNG 用流序列化，不调用 mt() 探测。计时区分构造、区间、初始化、搜索和重构，nested 字段不重复求和；诊断输出开销仍计入会话。只捕获 convert 前两次 CCSS，固定第二次作为交叉对象；没有按慢例挑选入口。

重放器链接本轮实际生产 sampler 对象，fresh constructor 后按同一 build_lits/build_instance 路径重建。X1 在首次 initialize 完成后通过专用异常退出，不运行搜索步；生产宿主从不设置此模式。另用完全关闭内部 Probe 的合成重建对照，在外部边界核对 R2/R3，验证内部诊断未消费 RNG 或改变初态。

X2 只替换 map，保留非 map 配方、顺序、seed、R0、原生 cutoff；不重置 map 引起的后续 RNG 分叉。初始化重建失败或辅助键语义不兼容则停止对应格。CCSS 重放成功候选先核验 native check_solution 与零未满足子句；如果没有完成原始 converter 的可靠恢复，明确标记 ccss_solution_only，不作为完整 F 合法模型，更不注入正式历史。

冻结前测试包括13个核心可执行检查、官方观察语义、四模式诊断开关、S_ref/Full 旧固定输入原生/RNG/模型回归、三模式配方重建与 Probe 完全关闭对照、数字/缓冲及截断输入；另有6类构造边界：负数、空map、缺键、解析失败、128位溢出、差分溢出。全部构建和测试尝试保留，正式阶段不得重试。
