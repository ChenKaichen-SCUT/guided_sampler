# real：完整整数域、作用域和有限二方向组合

本诊断独立使用原生位置 2/3/4/5 及旧 ValueCache 选定的 16 方向，不读取 convert 候选，也不向正式 L2 注入任何结果。证书审计独立从原 AST/anchor/完整方向重建仿射项与全部 Bool 区间，未调用 C++ LineDomain 或真实 solver。原式根域含 0；额外真实硬条件为 none。

| 位置 | 类别 | 记录 | 完整根域 | 完整证书 | 独立核验 | {0} | 非零域 | 合法见证 | 保护 | 覆盖增益 | B2 | B3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | original | 16 | 16 | 16 | 16 | 15 | 1 | 1 | 0 | 0 | 0 | 0 |
| 2 | combination | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | original | 16 | 16 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | combination | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | original | 16 | 16 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | combination | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | original | 16 | 16 | 16 | 16 | 15 | 1 | 1 | 0 | 0 | 0 | 0 |
| 5 | combination | 32 | 32 | 32 | 32 | 31 | 1 | 1 | 0 | 0 | 1 | 0 |


| 作用域 | 边界类型 | 证书中的原子出现次数 |
|---|---|---|
| conditional_boolean_structure | negative_lower_zero | 46 |
| conditional_boolean_structure | nonzero_slope_equality_at_zero | 285 |
| conditional_boolean_structure | positive_upper_zero | 46 |
| mandatory_AND_path | negative_lower_zero | 293 |
| mandatory_AND_path | positive_upper_zero | 88 |


计数是每份 anchor—direction 证书的原子出现次数，不是不同原约束数。下列摘要不是最小约束核；完整共享 DAG 的交/并/补证明才排除所有非零整数。必需 AND 路径与 OR/NOT 等条件作用域分开，不把局部分支等式当作全局强制等式。正 slack 而 floor/ceil 产生 0 边界时称“整数取整参与阻塞”，不称其唯一原因。

## 位置 2，原方向 129

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 1858 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 1860 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3227 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3235 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3985 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3986 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 2，原方向 176

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1521 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | 1 | [['0', '0']] | 0 | 0 |
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 1858 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 1860 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3227 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3235 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3387 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3985 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3986 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 4005 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 3，原方向 176

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1521 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | 1 | [['0', '0']] | 0 | 0 |
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3387 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 4005 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 3，原方向 129

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 4，原方向 176

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1521 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | 1 | [['0', '0']] | 0 | 0 |
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3387 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 4005 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 4，原方向 129

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 5，原方向 176

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1521 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | 1 | [['0', '0']] | 0 | 0 |
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3387 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 4005 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 位置 5，原方向 129

完整根域为 [['0', '0']]，独立证书核验通过。相关边界（全部仍见归档）：

| 原节点 | 作用域 | 角色 | 规范化 c | 斜率 s | 域 | floor(-c/s) | ceil(-c/s) |
|---|---|---|---|---|---|---|---|
| 1856 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3206 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3211 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3219 | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 | -1 | [['0', '0']] | 0 | 0 |
| 3776 | mandatory_AND_path | positive_upper_zero | 0 | 1 | [['-inf', '0']] | 0 | 0 |
| 3983 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |
| 3984 | mandatory_AND_path | negative_lower_zero | 0 | -1 | [['0', '+inf']] | 0 | 0 |


## 全部有限组合结果

| 位置 | 请求 | 状态 | 根域 | 独立核验 | 请求内 | 原池重合 | 合法 | 保护 | 增益 | B2 | B3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 0 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 1 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 2 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 3 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 4 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 5 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 6 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 7 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 8 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 9 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 10 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 11 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 12 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 13 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 14 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 15 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 16 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 17 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 18 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 19 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 20 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 21 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 22 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 23 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 24 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 25 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 26 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 27 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 28 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 29 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 30 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 2 | 31 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 0 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 1 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 2 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 3 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 4 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 5 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 6 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 7 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 8 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 9 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 10 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 11 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 12 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 13 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 14 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 15 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 16 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 17 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 18 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 19 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 20 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 21 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 22 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 23 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 24 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 25 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 26 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 27 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 28 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 29 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 30 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 3 | 31 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 0 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 1 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 2 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 3 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 4 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 5 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 6 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 7 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 8 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 9 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 10 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 11 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 12 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 13 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 14 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 15 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 16 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 17 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 18 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 19 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 20 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 21 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 22 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 23 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 24 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 25 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 26 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 27 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 28 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 29 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 30 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 4 | 31 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 0 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 1 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 2 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 3 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 4 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 5 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 6 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 7 | has_nonzero | [['-2500', '-2500'], ['0', '0']] | True | True | False | True | False | False | True | False |
| 5 | 8 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 9 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 10 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 11 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 12 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 13 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 14 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 15 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 16 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 17 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 18 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 19 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 20 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 21 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 22 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 23 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 24 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 25 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 26 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 27 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 28 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 29 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 30 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |
| 5 | 31 | singleton_zero | [['0', '0']] | True | True | False | False | False | False | False | False |


两个原方向都经完整域证书证明 {0}，且该组合在本诊断额度内完成合法非零见证，才记 B2；还需保护通过并严格增 covered 才记 B3。原池重合、零向量、重复、incomplete、unsupported、证书不完整、预算不合格全部保留。有限组合的负结果不能推出原公式唯一可满足或更高阶方向无效。

## 原约束及边界的具体读法

| 位置/方向 | 原节点与约束 | 作用域 | 作用 | c+s*t | 整数域 | floor/ceil |
|---|---|---|---|---|---|---|
| 2/129 | 1856 (le 0 xH170) | mandatory_AND_path | negative_lower_zero | 0 + (-1)*t | [['0', '+inf']] | 0/0 |
| 2/129 | 3206 (eq xH362 0) | conditional_boolean_structure | nonzero_slope_equality_at_zero | 0 + (-1)*t | [['0', '0']] | 0/0 |
| 2/129 | 3776 (le 0 xH362) | mandatory_AND_path | positive_upper_zero | 0 + (1)*t | [['-inf', '0']] | 0/0 |
| 2/128 | 2909 (ge xH130 1500) | conditional_boolean_structure | negative_lower_zero | 0 + (-1)*t | [['0', '+inf']] | 0/0 |
| 2/128 | 2912 (le xH130 1500) | conditional_boolean_structure | positive_upper_zero | 0 + (1)*t | [['-inf', '0']] | 0/0 |


## 可动组合仍然违反观察保护

位置 5 的 d9−d117 非零见证 t=−2500 使 xH172…xH179、xH180…xH189 各减 2500，xH364 加 2500，xH382 减 2500。它是远处的离散可行点，不是证明邻域连续可动。完整强制等式点积及完整原式验证通过；13 个缺失观察来自节点 1380、1381、1382、1383、3433，具体原表达式如下。

| 原节点 | 原表达式 |
|---|---|
| 1380 | xH177 |
| 1381 | (sub (add (sub xH176 xH369) 1000) xH561) |
| 1382 | (add (sub xH176 xH369) 1000) |
| 1383 | (sub xH176 xH369) |
| 3433 | (add xH406 xH430 xH454 xH478 xH502 xH526 xH550 xH574 xH214 xH238 xH262 xH286 xH310 xH334 xH358 xH382) |


缺失三元组完整保存在该 worker 的 combination ordinal=7 记录；差集为 [(1380,2,0),(1380,6,0),(1380,9,1),(1381,2,0),(1381,6,0),(1381,9,1),(1382,2,0),(1382,6,0),(1382,9,1),(1383,2,0),(1383,11,0),(1383,9,1),(3433,9,1)]。

## 61 个必需原子阻塞与 1 个布尔结构阻塞

对已经独立核验的 62 个 singleton-zero 原方向，进一步只交原根经必需 AND 可达的原子域（不把 OR 内原子提升为全局约束）：61 个仅这些必需原子就得到 {0}。强制等式的方向点积均为 0，实际收紧来自必需不等式。例：位置 2、方向 129，节点 1856 的 `0<=xH170` 规范化为 `-t<=0`，故 t>=0；节点 3776 的 `0<=xH362` 规范化为 `t<=0`，故 t<=0。这两个全局必需原子已经足以证明本方向只能取 0；条件结构里的等式 3206 虽也钉住 0，但无需把它误当全局等式。

剩下的是位置 5、方向 11：必需原子域为 [-1000,0]，需要完整布尔结构才能排除负移动。必需 OR 节点 373 的两支分别为 AND 节点 374 和 377。第一支的节点 375 是语法不变的假命题，因此整支空域，即使其另一个原子 376 的方程 `-1000-t=0` 在 t=-1000 有解也无效。第二支节点 378 是语法不变真命题，原子 379 是 `-t=0`，故该支域 {0}；OR 373 的完整并集就是 {0}。另一个必需 OR 2299 有 {-1000,0} 两点，不能只看当前分支，但它的远点仍被 OR 373 排除。这是完整分支推导，不是用 ±1 抽样证明。

本批原方向证书没有出现“正 slack、经整数 floor/ceil 后边界恰为 0”的参与阻塞模式；不能将 real 的全部 {0} 归因于整数取整。该机制在规定的合成 (2,1) 方向例中已单独验证。完整证书和原子域仍保留所有 floor/ceil/整除记录。

## 两个原方向的非零域

| 位置/方向 | 完整域 | 最近非零 t | 合法 | gain covered/observed | 原生 gain | 保护缺失数 |
|---|---|---|---|---|---|---|
| 2/6 | [['0', '0'], ['2500', '2500']] | 2500 | True | [2864, 2991] | [2865, 2992] | 18 |
| 5/6 | [['-2500', '-2500'], ['0', '0']] | -2500 | True | [307, 315] | [308, 316] | 6 |


两条原方向非零见证都完整验证了合法性和官方观察，但保护分别缺失 18、6 个观察，且 marginal covered 比对应原生少 1。它们单列于 62 个阻塞方向之外。

## 诊断实际资源和测量边界

| 位置 | 解析/前缀CPU/墙钟ms | 预处理CPU/墙钟ms | 16原方向CPU/墙钟ms | 32组合CPU/墙钟ms | 整进程CPU/墙钟ms | wait4 RSS KiB | 最大证书占用额度Bytes |
|---|---|---|---|---|---|---|---|
| 2 | 19.291/26.483 | 37.162/38.318 | 147.805/160.777 | 296.511/324.328 | 505.481/569.127 | 17752 | 8179520 |
| 3 | 22.501/29.707 | 37.811/38.410 | 135.923/147.707 | 275.095/299.582 | 475.709/533.732 | 114448 | 8218080 |
| 4 | 27.083/34.624 | 37.220/37.980 | 136.998/150.136 | 278.994/302.005 | 485.033/545.515 | 210192 | 8159776 |
| 5 | 29.552/37.304 | 36.987/37.540 | 144.929/158.229 | 290.324/326.628 | 506.549/580.793 | 210916 | 8136928 |


时间均远低于固定诊断上限，全部 192 请求的记录及清理在各自请求上限内。64 MiB 证书限制采用序列化大小的 32 倍保守占用额度；最大约 8.22 MB。没有逐证书分配器实测净堆增量，不能把它称作实测 64 MiB 内存证明。父进程 wait4 RSS 从 17752 到 210916 KiB 的差异保留；驱动器在启动后续 worker 前已解析并暂存前序大日志，fork/exec 启动内存未单独剥离，因此这里仅报告完整进程观测，不能将该差异直接归因于证书变大。这一归因是测量边界，未据此调整额度或重跑。
