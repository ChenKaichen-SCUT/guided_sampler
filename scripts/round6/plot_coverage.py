"""Standalone figures from frozen score CSVs; no sampling or solver checks."""
from common6 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
    stage=sys.argv[1];assert stage in ['G2','candidate'];name='guard' if stage=='G2' else 'candidate';out=BASE/(name+'_analysis');data=read(out/'summary.json')
    with (out/'curves.csv').open() as f:curves=list(csv.DictReader(f))
    colors={'Ref':'#777777','RefG':'#1765ad','Full':'#dc8242','FullG':'#b82c35','Chosen':'#227745'}
    fig,axes=plt.subplots(1,3,figsize=(13,3.7),sharex=True)
    for ax,inst in zip(axes,['convert','SMT_random','SMT_real']):
        for r in [r for r in data['sessions'] if r['instance']==inst and r['budget']=='time120']:
            cc=[c for c in curves if c['run']==r['run']];t=[0]+[float(c['commit_complete']) for c in cc]+[120];y=[0]+[100*int(c['covered'])/r['total'] for c in cc]+[r['coverage_percent']]
            ax.step(t,y,where='post',label=r['mode'],color=colors[r['mode']],linewidth=1.5)
        ax.set_title(inst);ax.set_xlabel('Wall time (s)');ax.grid(alpha=.2);ax.set_xlim(0,120)
    axes[0].set_ylabel('Exact covered / total (%)');axes[-1].legend(fontsize=8)
    fig.suptitle(stage+' independent time120 sessions, seed = 0');fig.tight_layout();fig.savefig(out/'coverage_time.svg');fig.savefig(out/'coverage_time.png',dpi=160);plt.close(fig)
    with (out/'matched_comparisons.csv').open() as f:matched=list(csv.DictReader(f))
    fig,axes=plt.subplots(1,2,figsize=(10,3.6));pairs=['Ref_vs_RefG','Full_vs_FullG','RefG_vs_FullG'] if stage=='G2' else ['RefG_vs_FullG','RefG_vs_Chosen','FullG_vs_Chosen']
    for ax,budget in zip(axes,['time120','n20_t120']):
        for k,pair in enumerate(pairs):
            for i,inst in enumerate(['convert','SMT_random','SMT_real']):
                r=next(r for r in matched if r['budget']==budget and r['pair']==pair and r['instance']==inst)
                eligible=budget=='time120' or r['strict20_eligible']=='True'
                if eligible:ax.bar(i+(k-1)*.25,float(r['coverage_pp_delta']),width=.23,color=['#1765ad','#dc8242','#227745'][k],label=pair.replace('_vs_',' -> ') if i==0 else None)
                else:ax.text(i+(k-1)*.25,0,'NA',fontsize=7,rotation=90,ha='center',va='bottom')
        ax.set_xticks([0,1,2],['convert','random','real']);ax.axhline(0,color='black',linewidth=.7);ax.set_title(budget);ax.set_ylabel('Coverage difference (percentage points)');ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(out/'matched_coverage.svg');plt.close(fig)
    print('Saved standalone coverage figures',stage)
if __name__=='__main__':main()
