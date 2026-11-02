# 实际应用补丁后的交换调用链

来源：worktrees/round4_S_release；P0/restoration_verification.json 将实际源文件 SHA 与第四轮冻结 patch manifest 逐项核对。这里的相对源码位置均指这棵树。

`smt/smt_model_generator.cpp::mk_values` 的 send-model 循环遍历当前 enode，仅 relevant、uninterpreted constant、非 hidden 声明写 `ast_manager::last_CDCL_model[name] = mk_pp(value)`。全树只有这一处写入；没有显式 clear 或跨 manager 复制。容器生命周期随 manager；当批未写的旧键可残留，但是否消费及适用尚待捕获证明。`mk_model_sampling()` 使用 `mk_values_ls()`，不是该写入循环。

`smt/smt_context.cpp` 构造 context 时建立新 `ls_sampler(random_seed, ls_timeout)`；构造器 `mt.seed(seed)`，cutoff 单位为秒。`setup_and_check()` 在原 LS 路由调用 `expr_bool_var_map()` → `build_instance(clauses_vec, m.last_CDCL_model)` → `ls_sampling()`；成功则 `mk_model_sampling()` 构造叶模型，再走原 converter。std::exception 被捕获并返回 Unknown，原日志没有具体异常原因。

`smt_context_pp.cpp::expr_bool_var_map()` 按 `m_b_internalized_stack` 顺序 `make_lits_space(size)`、生成实际字符串并 `build_lits()`；同时将 or/if 等转换子句追加到 clauses_vec。顺序影响变量身份，不能只保存排序表达式。`build_lits` 会修改传入字符串，配方应在入口捕获原串。

`sampler.cpp::build_instance` 复制 map 到私有 last_cdcl_model；执行变量约简、unit_prop/resolution/reduce_clause、occurrence/等式closure及make_space，最后 `calc_var_intervals()`。map消费只通过 find(name)，没有依赖 map 遍历顺序；因此保留完整键值和原迭代顺序，但交叉重建无须伪造桶布局。

`calc_var_intervals()` 检查128位原始十进制值，差分变量通过 pair_x/pair_y 求差；未知或溢出不替补0。满足的单变量不等式区间按 clause 合并、交集形成 feasible；高频closure取其与domain交集，普通变量通过 random_complement 消费 mt，等式closure另行处理。

`ls_sampling()` 才设置 _total_start，故原 cutoff 不含前述构造；调用 `search()`，先 `initialize()`，其中 `construct_solution_score()` 继续消费 mt，构造 literal/clause 统计后进入搜索步。原检查每1000步比较 TimeElapsed_total() 与 cutoff；溢出或50万无改善可重启。首次满足时 `choose_value_for_pair()`、`up_bool_vars()` 恢复差分/布尔信息，然后返回。`print_var_solution()` 通过原变量映射供模型生成器消费；不能以简化后的 _solution 数组冒充原始输入完整模型。

捕获计划为 R0 构造器seed后、R1区间前、R2区间后、R3首次initialize后；只序列化 mt，不取样。分阶段计时将构造、区间、初始化、搜索、恢复、日志分开，嵌套字段不重复求和。
