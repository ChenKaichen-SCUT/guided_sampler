from common_cr import *
from runner import stream_rows
sets={n:set() for n in ['convert','SMT_random','SMT_real']};counts={n:0 for n in sets}
for stage in ['probes/legacy_v1','probes/new_v1','offline/frozen_v1']:
 for p in (BASE/stage).glob('*/attempt.json'):
  name=read(p)['instance'];rs,truncated=stream_rows(p.parent/'stream.jsonl');assert not truncated
  for r in rs:
   if r['kind']!='event':continue
   for assignment in [r['native_assignment'],r['output_assignment']]+[c['assignment'] for c in r['candidates'] if c['kind']=='candidate' and 'assignment' in c]:sets[name].add(tuple(assignment));counts[name]+=1
exclusive(BASE/'analysis/distinct_assignments.json',{'by_formula':{n:len(s) for n,s in sets.items()},'total_distinct_formula_assignment_pairs':sum(map(len,sets.values())),'assignment_records_including_repetitions':counts,'audit_summary_field_unique_official_assignments_checked_means_cache_miss_checks_not_global_unique':'The independent checker uses an LRU cache of 32 assignments; eviction can trigger repeated official checks. Distinct counts are computed here from complete formula/assignment identities, not from cache misses.'})
print('distinct assignments',sum(map(len,sets.values())),{n:len(s) for n,s in sets.items()})
