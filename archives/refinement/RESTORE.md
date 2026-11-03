# 观察保留改进：完整证据恢复

在仓库根目录执行：

```bash
cat archives/refinement/results.tar.gz.part* | tar -xzf -
```

全部原始成功、失败、未触发、超时、候选、原生/输出流、事务、Python 审计、官方计分和 oracle 记录均在归档。每成员/分片 SHA256 见 manifest.json；已全量流式解压复核。历史 Ref 序列仍由 archives/round5 恢复，历史 HighDiv 和守卫证据沿用此前归档。本轮附上实际使用的宿主补丁展开文本和头依赖作为构建溯源，不上传构建树、虚拟环境、第三方二进制或凭据。重建需先按仓库原有脚本恢复第六轮 Release/SAN 前置构建，然后运行 scripts/refinement/build.py；源码和动态库 SHA 以本轮 implementation manifest 为准。
