# 成本修复完整证据恢复

在仓库根目录执行：

```bash
cat archives/refinement_cost_repair/results.tar.gz.part* | tar -xzf -
```

manifest.json 列出每个成员与分片的 SHA256；verification.json 是全量解压复核结果。归档包含全部 9 探针、39 序列、24 oracle、成功和失败测试、原始候选、成本、审计和完整源文本溯源；没有构建树、库或虚拟环境。历史 43 模型及原始收据继续从 archives/refinement 和 archives/round5 恢复，未复制或改写旧冻结证据。

重建先恢复原第六轮 Release/SAN 依赖及上一轮宿主生成源码，然后执行 `scripts/refinement_cost_repair/build.py release <新尝试名>` 与 sanitize 构建。构建入口拒绝改写已冻结 implementation manifest，重建时应在新工作副本使用单独 manifest 目录；不可覆盖本轮正式结果。执行/审计入口也拒绝覆盖已有尝试。逐文件、二进制、库与指标 SHA 见 manifests/refinement_cost_repair/implementation.json。
