"""Evidence-indexed bounded conclusions, not a new strategy or experiment."""
from common5 import *
def main():
    a=BASE/'analysis';assert read(a/'X_independent_arithmetic_audit.json')['passed'];assert read(a/'X_capture_details.json')['passed']
    claims=[
      ('weak_quota','avoid占额已证实；挤占去重后有效support未证实','W Full: convert 0/4, random 10/16, real 17/24；real q13/d38 support去重后为0；严格quota-only support=0','W_advice_funnel.csv','W_quota_opportunities.csv','src/round5/soft_phase.inc'),
      ('coverage_outside_pool','局部收益被集合外损失抵消','random Full G1 +78/G2 -160/G3 -12；Support +73/-206/+4；real Support相对Full +11/-29/+8','W_prefix_comparisons.csv','W_loss_diagnosis.csv','scripts/round5/coverage_partition.py'),
      ('support_only_negative','移除block tie-break未提高本次全式覆盖','Support相对Full convert 0/random -35/real -10；均未超过同宿主Ref','W_performance.csv','W_prefix_comparisons.csv','include/round5/coverage_policy.hpp'),
      ('map_not_formal','实际map不是正式原变量模型的完整替身','593键，503读取名=454命中+49缺项；544当前批+49旧批；旧批键未消费；共同原变量数值差异0','X_capture_details.json','X_producer_identity_audit.csv','include/round5/ccss_exchange_trace.hpp'),
      ('reconstruction','当前捕获重建可信；历史完整状态不可恢复','两个对角R1/R2/R3、intervals一致；R0构造状态核验；辅助键消费兼容；历史完整map/RNG未记录','X_capture_fidelity.json','X_capture_details.json','src/round5/ccss_replay_main.cpp'),
      ('map_search_effect','该捕获案例慢搜索随M_full，非构造耗时','rr/cr/rr_repeat: 219步SAT；rc/cc/cc_repeat:52秒native_cutoff；H非map字段一致，19区间/初值改变，R0-R3 RNG及初始未满足集合相同','X_replay_results.csv','X_independent_arithmetic_audit.json','src/round5/ccss_probe.inc'),
      ('empty_map_negative','没有清空map能改善本例的证据','r0/c0均52秒cutoff，初始未满足279，最佳21；缺项503，RNG从R2分叉','X_replay_results.csv','X_initialization_diff.csv','src/round5/ccss_probe.inc'),
      ('candidate_scope','重放候选仅验证约简CCSS','3个SAT候选原生及任意精度子句验证通过；原converter恢复未验证，不计入W正式样本','X_summary.json','X_independent_arithmetic_audit.json','scripts/round5/audit_X_details.py'),
      ('cost_limit','60秒正式预算保留，进程退出存在尾部延迟','convert Ref/Full/Support实际60.015/62.633/62.474秒；没有60秒后的正式样本；不是增加正式预算','W_cost_and_limit_details.json','W_performance.csv','scripts/finalize_round2_stream.py'),
      ('full_highdiv','本轮不构成超过完整HighDiv的验证','未重跑HighDiv、900秒矩阵或新seed；仅同宿主seed0的有限诊断','W_summary.json','X_summary.json','configs/round5_diagnosis.json')]
    rows_=[]
    for id,conclusion,evidence,f,g,source in claims:
        paths=[a/f,a/g,ROOT/source];rows_.append({'id':id,'conclusion':conclusion,'evidence':evidence,'artifacts':';'.join(str(p.relative_to(ROOT)) for p in paths),'sha256':';'.join(digest(p) for p in paths)})
    csvwrite(a/'root_cause_matrix.csv',rows_)
    decision={'priority_changes':[{'name':'原生CCSS连续无全局best改善的提前交还守卫','factor':'只加一个固定步数停滞守卫，建议阈值65536；保持map、初始化规则、随机流、move规则、原cutoff、A评分和宿主路由不变，触发时正常返回Unknown','basis':['X_rr/X_cr/X_rr_repeat均219步成功，已记录最长无全局改善段20步','M_full三次cutoff，已记录无全局改善段至少1096794步；空map两次至少565196步','W convert Full/Support的CCSS占用约52.4秒，各仅3正式模型；Ref有27正式模型','avoid没有挤占去重后有效support的证据，support-only全式覆盖未改善；清空map也未改善'], 'expected_metrics':['先降低失败CCSS的原生步数、CPU与宿主阻塞时间','在相同会话预算下观察正式模型供给与官方全式覆盖，不以提前Unknown当作采样成功'], 'controls':['保持本轮冻结原生版、同一实际捕获H/M和R0','随后仅比较原版与单守卫版；A策略和所有其他因素固定','继续保留成功M_ref、失败M_full与空map，不能挑慢例或追加seed补救'], 'failure_criteria':['打断本来219步成功的M_ref','未显著减少本次慢状态的资源占用','相同预算下官方全式覆盖或合法模型供给净下降','出现非法候选、RNG或构造输入非预期变化'], 'limitations':'仅是成本保护的下一项待检验修改；不能声称修复了CCSS搜索能力，也未证明全局性能收益。阈值由当前有限证据提出，尚未执行。'}], 'not_prioritized':['继续调整avoid或扩大support配额','清空交换map或改为正式模型','同时更换初始化分布、LIA move或目标池'], 'implemented_this_round':False,'new_experiments_triggered':0,'evidence_sha256':digest(a/'X_independent_arithmetic_audit.json')}
    write(a/'next_change_decision.json',decision)
    write(a/'known_limits_and_missing.json',{'missing':['cutoff时精确最终_step未单独保存；使用最后进度点下界，不当作最终步数','历史R4内部map、生产者与RNG不可恢复','未可靠恢复独立重放候选的原model converter，因此不能声称原始F合法','交换生产者每次日志CPU未单列；计入进程CPU和查询墙钟','random/real未安装完整CCSS捕获，42个CCSS Unknown原生内部原因未细分','未记录复合目标完整间接理论赋值链；最终访问与bit观察已独立验证'], 'trace_overflow':0,'W_protocol_exit_tail_overrun_runs':3,'formal_budget_seconds':60,'no_extra_formal_samples_after_budget':True,'historical_exact_59_seconds_reproduced':False,'long_call_phenomenon_reproduced_at_recorded_52_second_cutoff':True})
    print('Wrote evidence matrix and exactly one unimplemented next-factor decision')
if __name__=='__main__':main()
