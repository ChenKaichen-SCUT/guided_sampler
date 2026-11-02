# 第六轮完整证据恢复

在仓库根目录执行：

```bash
cat archives/round6/results.tar.gz.part* | tar -xzf -
```

归档包含本轮全部成功及失败的合成测试、正式尝试、原始模型、收据、原生退出、map/RNG身份、诊断、计分及审计。没有丢弃 Unknown、取消、失败和未完成记录。分片及每个成员的 SHA256 见 manifest.json；已完整流式解压核验。历史记录沿用此前归档。构建树、第三方二进制、虚拟环境和凭据不在归档中。
