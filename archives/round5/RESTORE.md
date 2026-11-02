# 第五轮完整证据恢复

在克隆的仓库根目录执行：

```bash
cat archives/round5/results.tar.gz.part* | tar -xzf -
```

所有新增正式/合成尝试、原始模型、收据、map、构造配方、RNG、初始化、重放、负结果和审计均包含在归档中。逐成员及分片SHA见manifest.json；已完整流式解压校验。历史证据沿用前四轮归档，不重复复制。原基准输入按前轮权限仅存来源和哈希。
