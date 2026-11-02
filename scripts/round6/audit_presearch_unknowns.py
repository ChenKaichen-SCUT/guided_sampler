"""Review saved construction exceptions; no new replay and no suppression."""
from common6 import *
def main():
    out=BASE/'guard_analysis';cfg=read(ROOT/'configs/round6_guard.json');records=[];pairs=[]
    for j in cfg['G2']:
        d=BASE/'guard_short'/j['id'];qs={q['query']:q for q in rows(d/'queries.jsonl')};receipts=rows(d/'formal_receipts.jsonl')
        for n in rows(d/'ccss_guard.jsonl'):
            if n['exit_reason'] not in ['exception','arith_unknown']:continue
            assert n['exit_reason']=='exception' and n['exception_text']=='Input string is not a valid number'
            assert not n['search_started'] and not n['model_produced'] and n['initialization_count']==0 and n['exit_step_exact'] is None
            q=qs[n['source_query_id']];assert q['result']=='unknown';assert not any(r['query']==q['query'] for r in receipts)
            records.append({'run':j['id'],'instance':j['instance'],'budget':j['budget'],'mode':j['mode'],**{k:n[k] for k in ['call_id','source_query_id','guard_enabled','exit_reason','exception_text','search_started','model_produced','map_sha256','rng_before_sha256','rng_after_sha256','seed']}})
    for inst in ['SMT_random','SMT_real']:
        for budget in ['time120','n20_t120']:
            for mode in ['Ref','Full']:
                left={r['source_query_id']:r for r in records if r['instance']==inst and r['budget']==budget and r['mode']==mode};right={r['source_query_id']:r for r in records if r['instance']==inst and r['budget']==budget and r['mode']==mode+'G'};same=[]
                for q in left.keys()&right.keys():
                    if all(left[q][k]==right[q][k] for k in ['exception_text','map_sha256','rng_before_sha256','rng_after_sha256','seed']):same.append(q)
                assert same,'Each guarded policy needs a matching guard-off construction failure'
                pairs.append({'instance':inst,'budget':budget,'pair':mode+'_vs_'+mode+'G','unguarded_exception_calls':len(left),'guarded_exception_calls':len(right),'same_query_map_RNG_seed_exception_matches':len(same),'first_matched_query':min(same)})
    # The numerical parser preceding the constructor is byte-identical to R5.
    old=(ROOT/'worktrees/round5_release/z3/src/sampler/sampler.cpp').read_text();new=(ROOT/'worktrees/round6_release/z3/src/sampler/sampler.cpp').read_text()
    def parser(s):return s[s.index('__int128_t string_to_int128('):s.index('__int128_t ceil_div(')]
    assert parser(old)==parser(new)
    csvwrite(out/'presearch_exceptions.csv',records);csvwrite(out/'presearch_exception_pairs.csv',pairs)
    write(out/'presearch_exception_review.json',{'passed':True,'calls':len(records),'pairs':pairs,'parser_context_identical_to_R5':True,'guard_reached_in_these_calls':False,'models_from_these_calls':0,'interpretation':'Construction failure exists with guard disabled and matching map/constructor RNG/seed; it is not a new guard-induced state failure. All calls remain exception/Unknown, never yield or SAT.','unknown':'Exact offending numeric token and historical R5 internal cause were not recorded; no claim of reconstructing that token.','new_solver_calls':0,'exception_log_suppression':False})
    print('Reviewed pre-search exceptions',len(records),len(pairs))
if __name__=='__main__':main()
