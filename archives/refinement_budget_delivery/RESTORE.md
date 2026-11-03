# 原预算交付与 real 阻塞诊断：完整证据恢复

请在新的恢复目录执行，不覆盖已有冻结数据：

```bash
cat /path/to/repo/archives/refinement_budget_delivery/results.tar.gz.part* | tar -xzf -
```

manifest.json 含全部成员及分片 SHA256；verification.json 是逐成员完整解压核对结果。包含所有构建/测试失败、4 探针、22 离线序列、4 real 诊断、全部候选、观察、区间证书、成本与独立审计。43 个源模型和原生收据从 archives/refinement 与 archives/round5 恢复；上一轮证据见 archives/refinement_cost_repair。没有第三方二进制、虚拟环境、构建树或凭据。

源码、实际生成宿主文件、二进制和动态库 SHA 见 manifests/refinement_budget_delivery/implementation.json；生成源码副本在本归档的 build_provenance 下。重建应使用新的工作副本和结果/构建目录，build.py 在存在实现冻结清单时拒绝重建，所有执行器拒绝覆盖尝试。不得通过删除冻结清单在原工作目录改写实验。
