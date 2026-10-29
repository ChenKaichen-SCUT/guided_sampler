# Guided Sampler，第一轮 A/B

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
