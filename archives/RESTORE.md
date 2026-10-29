# 恢复原始结果

在仓库根目录执行：

```bash
python3 archives/verify.py
cat archives/results.tar.gz.part* | tar -xzf -
```

逐片与逐成员 SHA-256 见 manifest.json。所有片段均随 Git 提交，不依赖本机绝对路径。
`verify.py`流式解压并检查全部2680个成员的大小和SHA-256，无需先解压到磁盘。
已有原始结果的工作区只需运行验证；恢复命令用于新的克隆，避免覆盖已有证据。
最终中文报告及归档后生成的`results/analysis/`直接随Git提交，不在这个归档内。
