# Guided Sampler，第一轮 A/B

在完整 HighDiv hybrid 流程中实现原子相位 A 与可回溯观察目标 B。
上游固定为 `laigroup/HighDiv@f2c6e1756b13281d96cbf90a8bd940129e56cce4`。
原始工作区 HighDiv、8 个输入保持不变，所有构建和运行位于独立副本。

协议见 [执行协议](docs/round1_protocol.zh.md) 和 [补充约定](docs/clarifications.zh.md)。
正式矩阵为 seed=0，4 配置 × 8 输入 × 2 独立预算，共 64 次；
唯一基线只有 16 次，禁止自动补跑。

构建：`python3 scripts/build_all.py baseline`、`python3 scripts/build_all.py guided`、
`python3 scripts/build_all.py sanitize`。需要 GNU C++20、Python venv、Boost 与
nlohmann/json 开发头文件。构建不会使用系统 Z3。

上游版权依原项目说明；Z3 为 MIT，见固定上游 `z3/LICENSE.txt`。
本仓库保存新增代码与可重放补丁，不提交上游整树、构建产物、虚拟环境或凭据。
