"""Post-run interpretation of frozen records; adds explicit protocol answers, no new runs."""
from common_bd import *
from runner import stream_rows
import collections,statistics
A=BASE/'analysis/audit_v1';seq=read(A/'sequences.json');ev=read(A/'events.json');certs=read(A/'certificates.json');real=read(A/'real_funnel.json');gate=read(BASE/'analysis/gate.json');cfg=read(ROOT/'configs/refinement_budget_delivery.json')
D=ROOT/'docs/refinement_budget_delivery'
def ms(x):return f'{1000*x:.3f}'
def table(h,rs):return '| '+' | '.join(h)+' |\n|'+ '|'.join(['---']*len(h))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rs)+'\n'
raw={};pstats={};metas={}
for s in seq:
 rr=stream_rows(BASE/s['stage']/'frozen_v1'/s['sequence']/'stream.jsonl')[0];raw[s['sequence']]=rr
 if s['stage']=='probes':pstats[s['configuration']]=next(x for x in rr if x['kind']=='preprocess');metas[s['configuration']]=next(x['metadata'] for x in rr if x['kind']=='metadata')
v0=pstats['V0']['trace']['work'];v1=pstats['V1']['trace']['work'];idx=metas['V3']['score_index']
text=['\n## 7. 指引十二项直接回答\n',f'1. 稀疏验证在 convert 探针把全行 Big 槽初始化从 {v0["verify_slots"]} 降为 {v1["verify_slots"]}，减少 {v0["verify_slots"]-v1["verify_slots"]} 槽；全行扫描从 {v0["verify_full_scans"]} 次降为 0。实际触及 {v1["verify_touched"]} 行次，乘加仍为 {v1["verify_multiply_adds"]}，覆盖全部 {v1["equality_rows"]} 强制等式的数学义务。独立检查器重新算全部行点积，没有忽略未触及行。\n','2. 共同完成部分及合成固定工作量的 affected 完全相同。V2/V3 消除了传递变量集合，但批量方向位集及输出 affected 仍有大量枚举和预算检查；本轮该阶段分别 60.639/57.893 ms CPU，V1 affected 为 13.740 ms、依赖为 36.817 ms。因此“批量影响必然更便宜”未成立；相比历史 Shared 的 75.173 ms affected 有单次下降，但跨版本不能当严格配对加速。\n',f'3. 分组把 {idx["original_affected_entries"]} 个 affected 条目压为 {idx["groups"]} 个签名组、{idx["compressed_group_direction_entries"]} 个组—方向条目，条目比 {idx["original_affected_entries"]/idx["compressed_group_direction_entries"]:.3f}。宽探针 V3 排名（含同步）约 1.8–2.2 ms；原三配置约 34–36 ms。第一次同步也在约 2 ms 范围，未见它成为当前首要瓶颈。正式 V3 因冷预处理失败而没有事件评分机会，不能把探针温态排名写成正式交付。\n','4. 四个 AuditAll 探针在位置 3 首次保存保护通过的 covered 增益，CPU/墙钟如下。这个首增益之前已有 9 条目标记录（方向 185 的 8 项及方向 186 的首项），首完整候选本身约 21–23 ms；V3 首增益累计约 44.48 ms。失败的目标探索、保护、排序和缓存从同一入口计时；后续 AuditAll 会继续搜索。其整事件最终日志/清理约 0.44–0.56 秒，不等于首见证时间。\n']
gains=[]
for mode in ['V0','V1','V2','V3']:
 e=next(e for e in ev if e['sequence']=='convert_'+mode and e['position']==3);m=e['first_preserved_covered'];gains.append([mode,ms(m['cpu']),ms(m['wall']),m['direction'],m['parameter'],ms(e['delivery_ready_cpu']),ms(e['delivery_ready_wall']),ms(e['event_total_cpu']),ms(e['event_total_wall'])])
text.append(table(['配置','首增益 CPU ms','首增益墙钟 ms','方向','参数','ready CPU ms','ready墙钟 ms','整事件CPU ms','整事件墙钟 ms'],gains))
text+=['5. 没有原预算内严格增益交付：22 条正式序列完整候选为 0、实际替代为 0。convert 主 L2：V0 三次均在 96 ms 软截止附近停止；V1 三次预处理合格但 26 个后续事件均停在排序；V2 的 r1/r3 预处理合格后也停在排序，r2 在元数据阶段超过总上限；V3 三次均在序列化/收尾超过 100 ms 墙钟。V3 的三次 CPU/墙钟约为 98.747/102.256、99.529/104.918、99.850/103.208 ms，不以 CPU 单边小于 100 ms 冒充合格。\n','6. FirstCovered 与成本修复必须分开：前者允许第一个合格 covered 候选提前进入收尾，后者保留同一有限搜索顺序。合成测试证明四配置停在同一首个合格候选；正式没有完整候选，故本轮没有测得正式 FirstCovered 收益。探针用 AuditAll，不能把其日志尾部当成 FirstCovered 交付成本，也不能推测若早停就会在 20 ms 内成功。\n','7. 正式没有前缀新增，全部 L2 终点与原生相同。L1 与 L2 在本轮都实际保持原生输出，未发生“前面替代改变后续历史”的分叉；但实现和合成测试已经验证二者历史隔离。旧 +43 及本轮探针 +43 都没有进入正式连续交付曲线。\n','8. real 独立复核 64 个完整原方向域：62 个 {0}、2 个有非零点。完整证书说明是原式 Bool 组合的整数可行域限制，发生在保护筛选前；原子具体作用域和整数边界见独立诊断报告。不是靠 t=±1 的有限测试作此判断，也不等于原公式只有一个模型。\n','9. 预登记 128 个组合请求全部完成：127 个 {0}，1 个非零域。位置 5 的 d9−d117（第 8 条请求，ordinal=7）归一化后不在原池，两个原方向各自确证 {0}，组合域为 {−2500,0}；t=−2500 完整合法。该见证 marginal gain 为 374/385，原生为 308/316，即无保护比较多 66 covered、69 observations，但缺失 13 个 protected 观察，故 B2 通过、B3 失败。没有注入历史。全部其余负结果只限制于这个固定有限集合。\n','10. 历史逐模型 CPU 信用仍未知；没有真实新 oracle 或重新求解成本。整进程 RSS 不是精确缓存净堆用量；stage trace 未单列首候选之前每个子阶段的独立累计截面，不能从整事件汇总反推其精确拆分。完整 CPU/墙钟及最终成本记录的未归属余额下表单列；全部正式输出都是 native，不存在被当作成功的临界资格未知替代。探针多次超过 500 ms 的不可中断日志尾部保留为超支，算法内候选不能据此称作 500 ms 内完整交付。\n','11. A0 正确性通过；正式 A1/A2/A3/A4 均未达到，convert 原预算目标 No-Go。real 达 B1（完整证书）及 B2（有限协调解除单方向阻塞），未达 B3；不能用 B2 替代任务 A 的失败。\n','12. 新真实采样=0、真实 solver check=0、oracle=0、在线实验=0、未登记真实重试=0；4 探针+22 序列+4 诊断均只执行预登记一次。合成隔离沿用现有合成原生 solver 检查来获得实际 CPU 信用，这些不是 benchmark 新采样或真实 oracle；不混入 43 模型。全部失败构建/测试、超时、拒绝和父进程成本保留。\n']
rows=[];residuals=[]
for s in seq:
 rs=raw[s['sequence']];parse=next(r for r in rs if r['kind']=='input');parentcpu=s['terminal']['user_cpu']+s['terminal']['system_cpu'];residual=parentcpu-(s['optional_cpu']+s['mandatory_cpu']+parse['parse_cpu']);r={'sequence':s['sequence'],'process_cpu':parentcpu,'process_wall':s['terminal']['parent_wall'],'optional_cpu_including_summary':s['optional_cpu'],'optional_wall_including_summary':s['optional_wall'],'mandatory_cpu':s['mandatory_cpu'],'mandatory_wall':s['mandatory_wall'],'parse_cpu':parse['parse_cpu'],'parse_wall':parse['parse_wall'],'cpu_unattributed_residual':residual,'summary_tail_cpu':s['summary_tail']['summary_cpu'],'summary_tail_wall':s['summary_tail']['summary_wall'],'scope':'residual includes process startup, unscoped bookkeeping, final cleanup and final record self-tail; not an event-specific bound'};residuals.append(r)
 if s['stage']=='offline':rows.append([s['sequence'],ms(r['mandatory_cpu']),ms(r['mandatory_wall']),ms(r['summary_tail_cpu']),ms(r['summary_tail_wall']),ms(residual)])
text.append(table(['正式序列','必需 CPU ms','必需墙钟 ms','摘要尾部CPU ms','摘要尾部墙钟 ms','进程CPU未归属余额ms'],rows));text.append('进程余额含启动、未分阶段管理开销、最终清理和末条记录自尾部，不能全部归因于某一临界事件。它不是把未知耗时置零的豁免。\n')
text+=['## 8. 下一步的证据约束\n','本轮停止，不追加配置、额度或真实重跑。后续若继续，应首先单因素检验候选专用完整求值的容器/遍历成本：当前首个候选本身已经约 21–23 ms，单靠进一步省排序或预处理无法证明达到 20 ms。可以研究保持两套独立合法性/官方访问校验的稀疏已访问结果表示，但不能借数值缓存替代正式观察，也不能承诺仅这一项就足够。real 的协调方向研究是另一条独立问题，当前见证还需要解决 13 个观察缺失，不能直接加入生产方向池。\n']
with (D/'results.zh.md').open('a') as f:f.write('\n'.join(text))
# Add original-node renderings to the verified certificates' readable explanations.
data=read(ROOT/'results/refinement/offline/inputs_v1/SMT_real.json');ns=data['ast']['nodes'];vs=data['ast']['variables']
def render(i,depth=0):
 n=ns[i];op=n['op']
 if op=='var':return vs[n['variable']]['name']
 if op=='const':return n['value']
 if depth>5:return '#'+str(i)
 return '('+op+' '+' '.join(render(c,depth+1) for c in n['children'])+')'
roles=collections.Counter((b['scope'],role) for c in certs if c['kind']=='original' and c.get('blocked') for b in c['blockers'] for role in b['roles'])
atom_examples=[];seen=set()
for c in certs:
 if c['kind']!='original' or not c.get('blocked'):continue
 for b in c['blockers']:
  for role in b['roles']:
   k=(b['scope'],role)
   if k in seen:continue
   seen.add(k);atom_examples.append({'position':c['position'],'direction':c['direction_id'],'node':b['node'],'formula':render(b['node']),'role':role,**b})
realtext=['\n## 原约束及边界的具体读法\n',table(['位置/方向','原节点与约束','作用域','作用','c+s*t','整数域','floor/ceil'],[[str(b['position'])+'/'+str(b['direction']),str(b['node'])+' '+b['formula'],b['scope'],b['role'],b['constant']+' + ('+b['slope']+')*t',b['before_distinct_complement'],str(b.get('floor'))+'/'+str(b.get('ceil'))] for b in atom_examples]),'## 可动组合仍然违反观察保护\n','位置 5 的 d9−d117 非零见证 t=−2500 使 xH172…xH179、xH180…xH189 各减 2500，xH364 加 2500，xH382 减 2500。它是远处的离散可行点，不是证明邻域连续可动。完整强制等式点积及完整原式验证通过；13 个缺失观察来自节点 1380、1381、1382、1383、3433，具体原表达式如下。\n',table(['原节点','原表达式'],[[i,render(i)] for i in [1380,1381,1382,1383,3433]]),'缺失三元组完整保存在该 worker 的 combination ordinal=7 记录；差集为 [(1380,2,0),(1380,6,0),(1380,9,1),(1381,2,0),(1381,6,0),(1381,9,1),(1382,2,0),(1382,6,0),(1382,9,1),(1383,2,0),(1383,11,0),(1383,9,1),(3433,9,1)]。\n']
with (D/'real_blocking.zh.md').open('a') as f:f.write('\n'.join(realtext))
write(BASE/'analysis/process_accounting.json',residuals);csvwrite(BASE/'analysis/process_accounting.csv',residuals);write(BASE/'analysis/real_atom_examples.json',atom_examples)
print('explicit answers and cost boundaries completed',flush=True)
