#!/usr/bin/env python3
"""Post-sampling analysis; does not modify samplers, frozen plan or run evidence."""
import collections,csv,json,pathlib,statistics
from common import ROOT,read,write

def main():
    runs=read(ROOT/'results/audit_summary.json')['runs'];plan=read(ROOT/'manifests/plan.json');paths={r['id']:ROOT/r['output'] for r in plan['runs']}
    out=ROOT/'results/analysis';out.mkdir(exist_ok=True);index={(r['input'],r['mode'],r['config']):r for r in runs};details=[]
    for run in runs:
        d=paths[run['id']];attempts={};reasons=collections.Counter();reason_seconds=collections.Counter()
        with (d/'queries.jsonl').open() as f:
            for line in f:
                q=json.loads(line)
                if q['result']=='unknown':reasons[(q['source'],q['reason_unknown'])]+=1;reason_seconds[(q['source'],q['reason_unknown'])]+=q['check_seconds']
                active={}
                for e in q.get('guidance',{}).get('events',[]):
                    for target in e['targets']:active[target]=e['source']
                if active:attempts[q['query']]=active
        counts=collections.Counter();formal_queries=set()
        with (d/'formal_receipts.jsonl').open() as f:
            for line in f:
                row=json.loads(line)
                if row['source']!='CDCL' or row['query'] not in attempts:continue
                formal_queries.add(row['query']);outcomes={o['target_id']:o for o in row.get('target_outcomes',[])}
                for target,channel in attempts[row['query']].items():
                    counts[channel+'_attempt_with_formal_model']+=1;o=outcomes.get(target,{})
                    counts[channel+'_reach']+=bool(o.get('reach'));counts[channel+'_hit']+=bool(o.get('hit'));counts[channel+'_new_target_observation']+=bool(o.get('new_observation'))
        for q,targets in attempts.items():
            for target,channel in targets.items():
                counts[channel+'_target_attempts']+=1
                counts[channel+'_without_formal_model']+=q not in formal_queries
        disabled=[]
        with (d/'guidance_events.jsonl').open() as f:
            for line in f:
                e=json.loads(line)
                if e.get('kind')=='cost_disabled':disabled.append(e)
        details.append({'id':run['id'],'input':run['input'],'config':run['config'],'mode':run['mode'],'target_attribution':dict(counts),'cost_disabled':disabled,
            'unknown_reasons':[{'source':k[0],'reason':k[1],'count':v,'check_seconds':reason_seconds[k]} for k,v in sorted(reasons.items())]})
    write(out/'mechanism_details.json',details)
    for mode in ['time900','n100_t900']:
        fields=['input','config','official_percent','covered','total','formal_models','complete100','time100_seconds','first_model_seconds','auc_percent','CDCL_models','CCSS_models','status','valid','delta_bits_vs_highdiv','delta_pp_vs_highdiv','strict_C100_comparison']
        with open(out/(mode+'_main.csv'),'w') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for r in runs:
                if r['mode']!=mode:continue
                base=index[r['input'],mode,'highdiv']
                w.writerow(dict(zip(fields,[r['input'],r['config'],r['official'],r['covered'],r['total'],r['models'],r['complete100'],r['time100'],r['first_model'],r['auc_percentage'],r['source_models'].get('CDCL',0),r['source_models'].get('CCSS',0),r['status'],r['valid'],r['covered']-base['covered'],r['percentage']-base['percentage'],mode=='n100_t900' and r['complete100'] and base['complete100']])))
    report=ROOT/'docs/round1_results.zh.md';text=report.read_text();intro='''
## 对五个研究问题的直接回答

1. **固定900秒没有总体净收益。** 八例等权平均相对完整HighDiv：A −0.069364、B −0.326116、AB −0.391081 个百分点。convert退步最明显；B/AB只在pb2010分别增加62/66个covered bit，原脚本两位小数仍显示4.13%。
2. **严格100模型均完成，但收益小且耗时增加。** 32个独立数量任务均达到100，各配置均为8/8；平均覆盖差分别为 A +0.058810、B +0.114757、AB +0.078102 个百分点。不存在本轮未完成100的配置。prime-cone从基线0.917秒增至B的113.528秒、AB的157.049秒；不能只报告小幅覆盖差而忽略吞吐。
3. **A-only没有实际相位介入。** A-only全部16项的A机会为0，其终点差异不能作为A软相位有效的证据。AB中A只有30次机会、28次实际改相位。B-only有9,466次显式目标尝试，AB有6,540次；B机制确实进入了搜索，但不代表具有净性能收益。AB的严格100模型均值还低于B-only，本轮没有证据证明组合成本值得。
4. **主要失败包括接入面不足、算术Unknown和持续搜索成本。** SMT_random与SMT_real两个实例的CDCL一直走不支持指导的tactic分支，A/B实际介入均为0。其端到端差异不能归因为目标决策。其他若干实例在B后反复返回`(incomplete (theory arithmetic))`；例如B-only的Bromberger有254次、CAV有1,503次、dillig有1,651次、prime-cone有238次，相关check分别累计约883、753、858、890秒。B-only/AB的已注册目标相关literal被原生队列取作候选累计约524万/615万次（随后仍可能由broker仲裁），远多于显式B尝试；5%的显式准备额度不能限制整个后续搜索成本。
5. **受控正确性与正式模型审计通过，适用范围仍有限。** 默认路由未被注册操作强制切换；原生CCSS、随机调用和变量固定主流程保留，关闭模式决策与模型轨迹一致。小有限问题投影保解、不可行目标回溯、取消/pop/reset等测试通过。全部正式模型再次通过官方Manual求值和原式精确代入，在线/离线覆盖增量一致；这些是工程证据，不是对所有LIA公式的形式化证明。

A-only及不支持后端运行中的差异只作为端到端观测保留。目录/表达式构造、墙钟限制与并发负载可能影响后续执行；本轮没有独立隔离这些因素，不能把差异解释为未发生的相位/目标干预。

完整逐实例主表另见 `results/analysis/time900_main.csv` 和 `results/analysis/n100_t900_main.csv`，包含首模型时间、AUC、CDCL/CCSS来源、状态、精确bit差和百分点差。`results/analysis/mechanism_details.json` 将实际目标尝试连接到同一查询的正式CDCL模型，分别记录Reach、目标命中、新目标观察、无正式模型和Unknown原因；不重复分配整个模型的gain。

**检测限制：** ASan/UBSan通过时保留一个已独立复现的上游32字节泄漏精确例外，详见 `sanitizer_exception.zh.md`。未关闭一般泄漏检查。成本停用后的原定义和学习历史仍存在；部分累计成本超过45秒，包含不可分操作超额和继续保留的观察/被动诊断，不表示重新开启指导额度。

**下一轮建议：** 先定位已有原子绑定/遇到率与SMT_random/SMT_real的后端覆盖，再对大模数目标触发的算术不完整性和历史代理成本做专门正确性与机制诊断。本轮不自动改参数、追加seed或重跑HighDiv。

'''
    marker = '## 对五个研究问题的直接回答'
    if marker in text:
        start = text.index(marker)
        end = text.index('## 固定 900 秒', start)
        text = text[:start] + text[end:]
    text=text.replace('## 固定 900 秒',intro+'## 固定 900 秒',1)
    report.write_text(text)
    print('Enriched report with explicit negative results, mechanism attribution and full comparison CSVs.')
if __name__=='__main__':main()
