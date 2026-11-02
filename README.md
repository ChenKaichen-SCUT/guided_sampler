# Guided Sampler，第五轮弱目标与 CCSS 交换成本诊断

本分支 `round5-weak-target-ccss-diagnosis` 从 `ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550` 建立。
完成 9 次 W 短会话、2 个原生初始化重建和 8 次固定交叉重放；Release、ASan/UBSan 与独立审计通过。
未重跑 HighDiv、追加 seed、启动 900 秒矩阵或启用 B；已有正式会话不得重新执行。

[第五轮中文报告](docs/round5_weak_targets_and_ccss_results.zh.md)｜[执行指引](docs/round5/execution_guide.zh.md)｜
[实现冻结](manifests/round5_implementation.json)｜[审计](results/round5/audit_summary.json)｜[完整原始证据恢复](archives/round5/RESTORE.md)

avoid 占用额度，但没有挤掉去重后可执行 support 的证据；support-only 未提高三个实例的全式覆盖。
convert 的慢搜索在可信重放中稳定跟随实际 M_full；M_ref 在 219 步成功，M_full 与空 map 到 52 秒截止。
81 个 W 正式模型合法；3 个重放 SAT 仅验证约简 CCSS，不进入正式样本。
三次 convert 会话有退出尾部延迟，正式计分仍截止 60 秒；未据此宣称优于完整 HighDiv。

第四轮资料：[语义映射与软参考报告](docs/round4_mapping_and_soft_reference_results.zh.md)。以下保留历史轮次说明。

---

# Guided Sampler，第三轮有限语义诊断

本分支 `round3-a-semantic-diagnosis` 从 `2f839861acf0a8cec78e05dac256b98b0dc30099` 建立。
已完成 6 次短会话、72 次可达性查询、2 次映射核验及 24 次有条件干预；
Release、ASan/UBSan 和独立审计通过。没有新增 900 秒矩阵、重跑 HighDiv、追加 seed 或启用 B。

[第三轮中文报告](docs/round3_semantic_diagnosis.zh.md)｜[追踪钩子](docs/round3_hook_map.zh.md)｜
[冻结计划](manifests/round3_semantic_cases.json)｜[原始证据恢复](archives/round3_semantics/RESTORE.md)

D1 实际改相位 50 次，指定目标仍零命中；12 个冻结见证分别出现全局值不可行、
观察不可行和当前固定条件阻塞。D3 的 15 个 SAT 模型也没有目标命中，9 个 Unknown 保留。
这些有限诊断不支持优于完整 HighDiv 的性能结论。历史阶段说明如下。

---

# Guided Sampler，第二轮 A-only

本分支从 `fc19bd22609295ed405e1ac96bf35d695c42832a` 独立开发。
已完成 Release、ASan/UBSan、36 次固定机制对照和 16 项 seed=0 正式实验，
404895 个正式模型通过官方计分与独立审计。未重跑 HighDiv、未追加 seed、未开启 B。

[第二轮中文报告](docs/round2_a_results.zh.md)｜[软相位实现说明](docs/A_soft_phase_guidance.zh.md)｜
[冻结计划](manifests/round2_a_plan.json)｜[原始证据恢复](archives/round2_a/RESTORE.md)

正式 A 实际改相位 534 次，但支持目标新增覆盖为 0。相对完整 HighDiv，
时间模式 1 胜 / 5 平 / 2 负，独立 100 模型模式 3 胜 / 5 平。
报告区分内部 Boolean assignment、返回模型真值、实际目标访问及成本，保留全部负结果。
第一轮历史负载与本轮不同，单 seed 不支持宣称稳定或普遍优势。

第二轮独立构建入口为 `scripts/build_round2.py release|sanitize`；
正式 `QUEUE_STARTED.json` 已冻结，构建器和执行器会拒绝覆盖本轮。
请读取或恢复已归档结果，不再次执行正式队列。第一轮归档通过上述固定 SHA 复用。

## 第一轮历史资料

在完整 HighDiv hybrid 流程中实现原子相位 A 与可回溯观察目标 B。
上游固定为 `laigroup/HighDiv@f2c6e1756b13281d96cbf90a8bd940129e56cce4`。
原始工作区 HighDiv、8 个输入保持不变，所有构建和运行位于独立副本。

协议见 [执行协议](docs/round1_protocol.zh.md) 和 [补充约定](docs/clarifications.zh.md)。
正式矩阵为 seed=0，4 配置 × 8 输入 × 2 独立预算，共 64 次；
唯一基线只有 16 次，禁止自动补跑。

本轮已完成64项正式会话与64项独立审计，32项独立100模型任务全部完成。
[中文结果报告](docs/round1_results.zh.md) 同时报告负结果：固定900秒无总体收益，
A-only没有实际相位介入，B确实进入搜索但部分实例出现大量算术Unknown。
[完整主表与机制数据](results/analysis/) 保留精确计数和耗时。
ASan/UBSan通过含一个[独立复现的上游32字节泄漏例外](docs/sanitizer_exception.zh.md)。

原始模型、正式/失败日志和审计证据存于39个无损分片，共约1.87 GiB；
逐片及全部2680个归档成员已验证SHA-256。
请先按[恢复说明](archives/RESTORE.md)恢复结果；不要重跑唯一正式基线。
归档后补充的分析CSV/JSON与最终报告直接保存在Git中。

构建：`python3 scripts/build_all.py baseline`、`python3 scripts/build_all.py guided`、
`python3 scripts/build_all.py sanitize`。需要 GNU C++20、Python venv、Boost 与
nlohmann/json 开发头文件。构建不会使用系统 Z3。

上游版权依原项目说明；Z3 为 MIT，见固定上游 `z3/LICENSE.txt`。
本仓库保存新增代码与可重放补丁，不提交上游整树、构建产物、虚拟环境或凭据。

从新的克隆复现环境：

```bash
python3 scripts/prepare_sources.py
python3 scripts/build_all.py baseline --jobs 8
python3 scripts/build_all.py guided --jobs 8
python3 scripts/build_all.py sanitize --jobs 8
python3 scripts/run_correctness.py release
python3 scripts/run_correctness.py sanitize
python3 scripts/run_upstream_tests.py guided
python3 scripts/run_upstream_tests.py sanitize
```

正式计划与运行脚本在正确性通过、实现提交后使用。运行器创建不可覆盖的
`QUEUE_STARTED.json` 和逐项 `attempt.json`；已执行轮次只能读取，不能调用这些
脚本重新生成已冻结的 HighDiv 基线。

- `scripts/freeze_plan.py`：绑定源码提交、输入、可执行文件和实际加载库。
- `scripts/run_experiments.py`：16个固定逻辑CPU槽、同步首批、固定队列补位。
- `scripts/audit_results.py`：全部采样结束后，正式收据回放、官方计分、精确覆盖和独立合法性审计。
- `scripts/summarize_round.py`：中文主表、差值、机制、前缀和成本。
- `scripts/archive_results.py`：无损归档与50MiB分片、逐片和逐成员SHA-256。
- `scripts/publish_round.py`：非强制推送指定分支，并核对远端SHA。

测试专用环境变量 `HIGHDIV_TEST_MAX_QUERIES`、`HIGHDIV_NATIVE_DECISION_TRACE`
只用于受控回归；正式调度器显式移除它们。测试失败现场同样保留在正确性目录。
