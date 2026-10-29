#!/usr/bin/env python3
import csv,statistics
from common import *

def main():
    audit=read(ROOT/'results/audit_summary.json');executed=read(ROOT/'results/QUEUE_FINISHED.json')['runs'];runs=audit['runs'];index={(r['input'],r['mode'],r['config']):r for r in runs};names=sorted({r['input'] for r in runs});configs=['highdiv','a_only','b_only','a_plus_b']
    fields=['input','mode','config','models','complete100','time100','covered','total','percentage','official','first_model','auc_percentage','status','valid']
    with open(ROOT/'results/summary.csv','w') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(runs)
    text=['# Guided Sampler 第一轮结果\n',f"实际启动：{executed}/64；正式会话记录：{len(runs)}/64；独立审计通过：{sum(r['valid'] for r in runs)}/64。全部 seed=0。基线是共同 Release 编译、原变量投影和截止测量适配的完整 HighDiv。\n",
        '## 固定 900 秒\n','单元格为官方覆盖率；精确 covered/total；正式模型数。\n', '| 实例 | HighDiv | A | B | AB |','|---|---|---|---|---|']
    for name in names:
        row=[name]
        for config in configs:
            r=index[name,'time900',config];row.append(f"{r.get('official','NA')}；{r.get('covered','NA')}/{r.get('total','NA')}；n={r.get('models',0)}")
        text.append('| '+' | '.join(row)+' |')
    text+=['\n## 独立 100 模型／最多 900 秒\n','每个单元格为实际模型数、是否完成 100、到达时间、官方终点覆盖。未完成者不作为 C100。\n','| 实例 | HighDiv | A | B | AB |','|---|---|---|---|---|']
    for name in names:
        row=[name]
        for config in configs:
            r=index[name,'n100_t900',config];t=r.get('time100');row.append(f"n={r.get('models',0)}；{'完成' if r.get('complete100') else '未完成'}；{f'{t:.3f}s' if t is not None else 'NA'}；{r.get('official','NA')}")
        text.append('| '+' | '.join(row)+' |')
    text+=['\n## 差值与完成率\n','以各实例原分母归一化后等权平均百分点；不将 bit 数直接合并为总体增益。\n']
    for mode in ['time900','n100_t900']:
        text.append(f'### {mode}\n')
        for ca,cb in [('a_only','highdiv'),('b_only','highdiv'),('a_plus_b','highdiv'),('a_plus_b','a_only'),('a_plus_b','b_only')]:
            pairs=[(index[n,mode,ca],index[n,mode,cb]) for n in names]
            good=[(a,b) for a,b in pairs if a.get('valid') and b.get('valid')]
            if mode=='n100_t900':
                joint=[(a,b) for a,b in good if a.get('complete100') and b.get('complete100')]
                text.append(f"- {ca} − {cb}：双方严格完成100的实例 {len(joint)}/8；"+(f"该子集平均 {statistics.mean(a['percentage']-b['percentage'] for a,b in joint):+.6f} 个百分点。" if joint else '无可比较 C100。'))
            if len(good)==8:text.append(f"- {ca} − {cb}：8例实际终点均值 {statistics.mean(a['percentage']-b['percentage'] for a,b in good):+.6f} 个百分点；退步实例："+'、'.join(a['input'] for a,b in good if a['covered']<b['covered'])+'。')
        if mode=='n100_t900':text.append('完成100实例数：'+'；'.join(f"{c}={sum(index[n,mode,c].get('complete100',False) for n in names)}/8" for c in configs)+'。')
    text+=['\n## 实际机制与成本\n','下表是实际普通决策次数；A 同相位建议也计为机会，实际改相位另列。目标命中不被重复归因为该目标独立造成全部模型收益。\n',
        '| 配置／模式／实例 | A机会／改变 | B尝试 | 不支持后端 | 显式成本秒 | 状态 |','|---|---:|---:|---:|---:|---|']
    for r in runs:
        if r['config']=='highdiv':continue
        g=r.get('guidance',{});text.append(f"| {r['config']}/{r['mode']}/{r['input']} | {g.get('a_used',0)}/{g.get('a_changed',0)} | {g.get('b_used',0)} | {g.get('unsupported',0)} | {r.get('costs',{}).get('explicit_seconds','NA')} | {r.get('status')} |")
    text+=['\n## 正确性、限制与证据\n',
        '- Release、ASan/UBSan 测试、逐节点观察器差分和关闭行为证据位于 `results/correctness/`。',
        '- 每个正式样本经过原式快照验证，离线再以官方 Manual 求值和原式精确代入交叉核对；在线增量与官方逐模型增量核对。',
        '- `queries.jsonl` 的求解统计为累计快照，未冒充查询差分；阶段时间可能包含彼此，不能重复相加。',
        '- 默认 combined solver 的 tactic 路径不支持指导；元数据安装本身不改变路由。CCSS 及原 HighDiv 随机流保留，指导不使用随机数。',
        '- B 的历史定义可被原生队列再选择；撤销优先权不删除学习历史。窗口、内部化与实际决策分阶段记录。',
        '- 初始16项同步释放，固定队列空槽补位；100模型提前完成会改变瞬时并发，因此不声称各配置负载完全相同。',
        '- 只有一个seed、8个开发观察实例；不能推断显著性、稳定性或跨LIA泛化。零收益、未完成、Unknown和失败均保留。',
        '- 完整差值、时间前缀、模型前缀、首模型时间、AUC、来源、路由、额度和资源信息保存在每项 `audit.json` 及 `results/summary.csv`。',
        '- 原输入未额外公开；其哈希和已公开上游对应路径在 `manifests/inputs.json`。',
        '\n如存在性能退步，本轮不追加seed、不改额度、不重跑唯一基线。下一轮应依据实际接入率、映射覆盖面与完整求解成本分别定位问题。\n']
    (ROOT/'docs/round1_results.zh.md').write_text('\n'.join(text)+'\n')
    print(ROOT/'docs/round1_results.zh.md')
if __name__=='__main__':main()
