from common6 import *
import tarfile
from archive_round4 import Joined
BASE_SHA='ae85956068154207a442c0e2c8387c573dc32411'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE_SHA
old=read(ROOT/'configs/round5_diagnosis.json');jobs=[];candidate=[]
for b,(budget,inst) in enumerate((budget,inst) for budget in ['time120','n20_t120'] for inst in ['convert','SMT_random','SMT_real']):
    parent=next(j for j in old['jobs'] if j['instance']==inst)
    for k,mode in enumerate(['Ref','RefG','Full','FullG']):
        jobs.append({'id':inst+'_'+mode+'_'+budget,'batch':b,'instance':inst,'mode':mode,'budget':budget,'cpu':[0,2,4,6][(k+b)%4],'seed':0,'wall_seconds':120,'model_limit':20 if budget=='n20_t120' else None,'input':parent['input'],'input_sha256':parent['input_sha256'],'guard':mode.endswith('G'),'coverage':mode.startswith('Full'),'cdcl_query_cap':None})
    for k,mode in enumerate(['RefG','FullG','Chosen']):candidate.append({'id':inst+'_'+mode+'_'+budget,'batch':b,'instance':inst,'mode':mode,'budget':budget,'cpu':[0,2,4][(k+b)%3],'seed':0,'wall_seconds':120,'model_limit':20 if budget=='n20_t120' else None,'input':parent['input'],'input_sha256':parent['input_sha256']})
g1=[{'id':id,'H':h,'M':m,'cpu':2*i,'cutoff':52,'parent_seconds':65} for i,(id,h,m) in enumerate([('G_rr','ref','ref'),('G_cr','full','ref'),('G_rc','ref','full'),('G_cc','full','full'),('G_r0','ref','empty'),('G_c0','full','empty')])]
gates={'unit_of_coverage':'exact covered/total, percentage points; equal weight per instance','local':'R0-R3 and saved deterministic prefix match; both M_ref cases SAT at step219; all four slow cases yield with best>0 and no candidate','time':'at least one real guard yield; all four captured slow replays use <26 search wall seconds (>=50% below frozen52), plus real calls yield before granted cutoff','useful':'at least one matched time120 instance has more subsequent CDCL checks, more formal distinct legal models, and more covered bits in guarded vs corresponding unguarded mode; also event-linked post-yield model and positive-covered receipt','coverage':'time120 mean FullG-RefG percentage points >0; strict independent n20 completed-pair mean >0; at least two instances strictly better in BOTH endpoints','G3_precedence':['correctness/local failure -> stop','no time saving -> stop','useful supply AND quality loss outside G1 -> candidate A','no formal supply increase AND repeated identical consumed-map stagnation without intervening legal CDCL model -> candidate B','FullG meets promotion -> FullG directly, no new algorithm','otherwise -> No-Go'],'candidate_A':'fixed Full then Ref alternation among CDCL queries after first available coverage history; index advances every such CDCL, not based on actions/hits','candidate_B':'two consecutive yielded CCSS, same consumed map SHA, no intervening legal CDCL raw model; skip exactly next scheduled CCSS then reset; retain original seed draw on skipped slot','promotion':'positive equal-weight time120 mean and positive strict independently completed n20 mean against RefG; at least two instances strictly positive in both endpoints; correctness and useful guard true; completed paired n20 count>=2','disaster':'new correctness/RNG/state anomaly, or >50% coverage reduction vs RefG without a specifically recorded finite-search exit/cause; disclose every per-instance regression','no_tuning':True,'at_most_one_candidate':True,'no_retry':True,'F_slots':list(range(16)),'F_queue':'budgets time900 then n100_t900; immutable input-manifest order; for each instance RefG then Chosen; cpu=(queue_index+budget_index*8)%16; start first16 together, fill freed fixed-slot FIFO only; no unrelated tasks','formal_fullG_comparison':'only matched development-stage ablation, no invented extra fullG 900s runs'}
tests=['pure global-best guard strict-improvement and fixed65536 boundary','restart-local improvement does not reset history','global improvement during initialize resets history','zero-unsat wins at boundary','call reset and exact exit steps','native cutoff/cancel/arithmetic/exception reason priority','disabled native/RNG/initial/model frozen regression','219-step success preserved','guard Unknown leaves m_ls unchanged and next CDCL executes','numeric SHA256 standard vectors and canonical map hash','all inherited R5 correctness groups Release+ASan/UBSan','same exact upstream32-byte leak suppression','no new B/assertion/relevance/decision-variable replacement']
exclusive(ROOT/'configs/round6_guard.json',{'base_commit':BASE_SHA,'limit':65536,'seed':0,'G1':g1,'G2':jobs,'candidate':candidate,'gates':gates,'tests':tests,'G2_parent_seconds':135,'formal_parent_seconds':915,'full_HighDiv_runs':0,'B':False,'exposure_seconds':45,'explicit_seconds':45,'window':64,'quota':4})
exclusive(ROOT/'manifests/round6_plan.json',{'config_sha256':digest(ROOT/'configs/round6_guard.json'),'guide_sha256':digest(ROOT/'docs/round6/execution_guide.zh.md'),'cpu_topology':subprocess.check_output(['lscpu','-p=CPU,CORE,SOCKET,NODE'],text=True),'allowed_cpus':sorted(os.sched_getaffinity(0)),'G1_count':6,'G2_count':24,'candidate_max':18,'conditional_formal_count':32,'tests_frozen_before_implementation':True})
metadata={}
for directory in ['results','archives']:
    for p in (ROOT/directory).rglob('*'):
        if p.is_file() and 'round6' not in p.parts:
            st=p.stat();metadata[str(p.relative_to(ROOT))]={'size':st.st_size,'mtime_ns':st.st_mtime_ns}
protected={}
for pattern in ['worktrees/*/HighDiv/highdiv','deps/*/lib/libz3.so','include/round5/*','src/round5/*']:
    for p in ROOT.glob(pattern):
        if p.is_file():protected[str(p.relative_to(ROOT))]=digest(p)
exclusive(ROOT/'manifests/round6_protected_before.json',{'metadata':metadata,'protected_sha256':protected,'frozen_R5_implementation_sha256':digest(ROOT/'manifests/round5_implementation.json'),'frozen_R5_evidence_sha256':digest(ROOT/'manifests/round5_W_evidence.json')})
manifest=read(ROOT/'archives/round5/manifest.json');parts=[ROOT/'archives/round5'/x['file'] for x in manifest['parts']];count=0
for p,r in zip(parts,manifest['parts']):assert digest(p)==r['sha256']
with tarfile.open(fileobj=Joined(parts),mode='r|gz') as tar:
    for m in tar:
        if not m.isfile():continue
        h=hashlib.sha256();f=tar.extractfile(m)
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
        assert h.hexdigest()==manifest['members'][m.name]['sha256']==digest(ROOT/m.name);count+=1
assert count==2673
for rel,h in read(ROOT/'manifests/round5_W_evidence.json')['files'].items():assert digest(ROOT/rel)==h
write(BASE/'readonly/frozen_evidence_verified.json',{'passed':True,'R5_archive_members':count,'frozen_captures_verified':True,'historical_binary_executions':0,'new_solver_calls':0,'report_sha256':digest(ROOT/'docs/round5_weak_targets_and_ccss_results.zh.md'),'decision_sha256':digest(OLD5/'analysis/next_change_decision.json')})
print('Frozen G0 tests,6 G1,24 G2,conditional18/32, gates; verified2673 R5 archive members')
