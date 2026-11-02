"""Chinese tables from audited summaries; no solver calls or new interpretation."""
from common6 import *
def main():
    summary=read(BASE/'formal_analysis/summary.json');assert read(BASE/'formal_analysis/independent_audit.json')['passed'];lines=['# 第六轮正式结果表\n','Chosen 即 FullG；完整 HighDiv 为历史冻结记录。覆盖均为官方精确 covered/total。\n']
    for budget in ['time900','n100_t900']:
        lines+=['## '+budget+'\n','| 实例 | RefG 模型 / covered | FullG 模型 / covered | 冻结 HighDiv 模型 / covered | FullG−RefG bit / 百分点 | FullG−HighDiv bit / 百分点 | 严格100可比（RefG / HighDiv） |','|---|---:|---:|---:|---:|---:|---|']
        for i in range(8):
            ref=next(r for r in summary['sessions'] if r['input_index']==i and r['budget']==budget and r['mode']=='RefG');cov=next(r for r in summary['sessions'] if r['input_index']==i and r['budget']==budget and r['mode']=='Chosen');old=next(r for r in summary['historical'] if r['input_index']==i and r['budget']==budget);a=next(r for r in summary['comparisons'] if r['input_index']==i and r['budget']==budget and r['pair']=='RefG_vs_Chosen');b=next(r for r in summary['comparisons'] if r['input_index']==i and r['budget']==budget and r['pair']=='HighDiv_vs_Chosen')
            strict='不适用' if budget=='time900' else ('是' if a['strict100_eligible'] else 'NA')+' / '+('是' if b['strict100_eligible'] else 'NA')
            lines.append(f"| {cov['instance']} | {ref['formal']} / {ref['covered']} | {cov['formal']} / {cov['covered']} | {old['formal']} / {old['covered']} | {a['covered_delta']:+d} / {a['coverage_pp_delta']:+.6f} | {b['covered_delta']:+d} / {b['coverage_pp_delta']:+.6f} | {strict} |")
        lines.append('')
        for pair in ['RefG_vs_Chosen','HighDiv_vs_Chosen']:
            r=next(r for r in summary['aggregate'] if r['pair']==pair and r['budget']==budget);lines.append(f"{pair}：八实例等权预算终点均值 {r['equal_weight_endpoint_mean_pp']:+.6f} 个百分点；正收益 {len(r['positive_instances'])}/8。")
            if budget=='n100_t900':lines.append(f"严格100模型可比 {r['strict100_completed_pairs']}/8，完成配对均值 {r['strict100_mean_pp'] if r['strict100_mean_pp'] is not None else 'NA'} 个百分点；未完成：{r['incomplete_not_scored_as_tie']}。")
        lines.append('')
    lines+=['模型不足的预算终点差仍完整展示，但不能据此宣称严格100模型胜负。各模型前缀、AUC、来源、重复率、CPU/RSS及退出原因见正式分析 CSV 和完整归档。','历史 HighDiv 与本轮的构建、资源占用与日志开销不完全配对；这里是单 seed 描述性比较。']
    (ROOT/'docs/round6/formal_tables.zh.md').write_text('\n'.join(lines)+'\n');print('Wrote formal Chinese tables')
if __name__=='__main__':main()
