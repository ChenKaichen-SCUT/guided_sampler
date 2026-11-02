# 第五轮冻结协议

基点 ec5b2ab415a38a4e89b76ec5b427ce23f0fb0550；独立分支 round5-weak-target-ccss-diagnosis。执行完整附件 docs/round5/execution_guide.zh.md。

先只读复核第四轮六个 S 会话的全部归档 SHA、模型、覆盖分区和额度；缺项为 not_recorded，离线重算明确标记，不新增求解。完成后才实现唯一评分消融 SupportOnly：只删除 support 平分时的 block 仲裁。Full 完整保留原 S_cov；参考、配额、去重、RNG 和生产 CCSS 语义不变。

预先编号的十组受控测试见 configs/round5_diagnosis.json；Release 与 ASan/UBSan、原生回归及诊断开关测试后冻结构建。W 三实例三模式恰好九项独立 seed=0 会话，固定 CPU 槽 [0,2,4,6,8,10,12,14,1] 同批释放，60 秒和 32/8 次 CDCL 双上限。计时阶段不编译、审计或压缩。保存并发、亲和性、CPU 和墙钟，跨轮墙钟不作加速解释。

从 convert 三模式进程开始跟踪真实交换生产者，捕获前两次 CCSS 输入；只使用 Ref/Full 第二次。X1 只构造和初始化，不搜索；严格核验结构、读集及 R0–R3 RNG 后，才执行固定八项 X2。若捕获/兼容/重建失败则停止对应格并保留原因。各格为新进程，原生 cutoff 不变且上限 60 秒，父进程 65 秒，不重试、不改检查点。重放样本不进入正式历史。

本轮不重跑 HighDiv、不增加 seed、不运行 900 秒、不启 B、不改 CCSS 交换或超时策略。所有失败/Unknown/零触发保留；只选零或一个下一轮优先修改，本轮不继续实施该修改。
