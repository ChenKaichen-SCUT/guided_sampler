"""Standalone F figures, with unchanged historical HighDiv shown separately."""
from common6 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
    out=BASE/'formal_analysis';summary=read(out/'summary.json');assert summary['passed'];curves=collections.defaultdict(list)
    with (out/'curves.csv').open() as f:
        for r in csv.DictReader(f):
            key=(int(r['input_index']),r['budget'],r['mode']);point=(float(r['commit_complete']),int(r['index'])+1,int(r['covered']),int(r['total']))
            if not curves[key] or curves[key][-1][2]!=point[2]:curves[key].append(point)
    names=['Bromberger','CAV2009','SMT_random','SMT_real','convert','dillig','pb2010','prime_cone']
    for budget in ['time900','n100_t900']:
        fig,axes=plt.subplots(2,4,figsize=(15,7.3))
        for i,ax in enumerate(axes.flat):
            for mode,color in [('RefG','#1765ad'),('Chosen','#b82c35')]:
                p=curves[(i,budget,mode)];r=next(r for r in summary['sessions'] if r['input_index']==i and r['budget']==budget and r['mode']==mode);end=900 if budget=='time900' else r['formal'];t=[0]+[z[0] if budget=='time900' else z[1] for z in p]+[end];y=[0]+[100*z[2]/z[3] for z in p]+[r['coverage_percent']];ax.step(t,y,where='post',color=color,label='FullG' if mode=='Chosen' else mode,linewidth=1.4)
            x=read(ROOT/'results/baseline_seed0_v1/highdiv'/budget/f'{i:02}'/'exact.json');p=x['prefixes'];end=900 if budget=='time900' else x['models'];kept=[]
            for k,z in enumerate(p):
                if not kept or kept[-1][2]!=z['covered']:kept.append((z['commit_complete'],k+1,z['covered']))
            ax.step([0]+[z[0] if budget=='time900' else z[1] for z in kept]+[end],[0]+[100*z[2]/x['total'] for z in kept]+[100*x['covered']/x['total']],where='post',color='#777777',linestyle='--',label='Frozen HighDiv',linewidth=1.2)
            ax.set_title(names[i]);ax.set_xlabel('Wall time (s)' if budget=='time900' else 'Distinct formal models');ax.set_ylabel('Exact coverage (%)');ax.set_xlim(0,900 if budget=='time900' else 100);ax.grid(alpha=.2)
        axes[0,0].legend(fontsize=8);fig.suptitle(budget+'; seed = 0. Historical HighDiv resources are not matched.');fig.tight_layout();fig.savefig(out/(budget+'_coverage.svg'));fig.savefig(out/(budget+'_coverage.png'),dpi=160);plt.close(fig)
    print('Saved F coverage figures')
if __name__=='__main__':main()
