# 第二轮原始证据恢复

在仓库根目录执行：

```bash
cat archives/round2_a/results.tar.gz.part* | tar -xzf -
```

逐成员与逐分片哈希见 manifest.json，已完整流式解压校验。第一轮原始归档引用基点 fc19bd22609295ed405e1ac96bf35d695c42832a，不重复复制。
