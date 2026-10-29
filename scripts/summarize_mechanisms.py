#!/usr/bin/env python3
"""Read sealed audits; add reviewable mechanism and paired-comparison tables."""
import csv
from common import ROOT, read


def save(name, rows):
    with (ROOT / 'results/analysis' / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    runs = read(ROOT / 'results/audit_summary.json')['runs']
    details = {r['id']: r for r in read(ROOT / 'results/analysis/mechanism_details.json')}
    rows = []
    for r in runs:
        if r['config'] == 'highdiv':
            continue
        w, g, d = r['window'], r['guidance'], details[r['id']]
        row = {k: r[k] for k in ('id', 'input', 'config', 'mode')}
        # Every covered bit contributes two observed values; every one-sided bit one.
        row['final_one_sided_bits_including_constants'] = r['new_observed'] - 2 * r['covered']
        row['distinct_selected_targets'] = r['distinct_targets']
        for key in ('Bool', 'Int', 'low', 'mid', 'high', 'a_static_match', 'created',
                    'reused', 'slice_incomplete', 'encoding_incomplete', 'registry_cap'):
            row['window_' + key] = w.get(key, 0)
        for key in ('a_live', 'a_used', 'a_same', 'a_changed', 'b_internalized',
                    'b_relevant', 'b_used', 'propagated', 'deferred', 'cap',
                    'unsupported', 'fallback', 'native_registered_targets'):
            row[key] = g.get(key, 0)
        for channel in ('A', 'B'):
            for metric in ('target_attempts', 'attempt_with_formal_model', 'reach',
                           'hit', 'new_target_observation', 'without_formal_model'):
                key = channel + '_' + metric
                row[key] = d['target_attribution'].get(key, 0)
        row['cost_disabled_events'] = len(d['cost_disabled'])
        for key in ('prepare_seconds', 'broker_seconds', 'explicit_seconds',
                    'CDCL_check_seconds', 'CCSS_check_seconds'):
            row[key] = r['costs'].get(key, 0)
        row['new_observed'] = r['new_observed']
        row['new_covered'] = r['new_covered']
        row['formal_models'] = r['models']
        row['models_per_process_wall_second'] = r['models'] / r['terminal']['process_wall_seconds']
        # These were not separately instrumented; never infer them from unknown/hit.
        row['per_target_backtrack_abandonments'] = 'not_recorded'
        row['fixed_assumption_target_conflicts'] = 'not_recorded'
        rows.append(row)
    save('mechanism_main.csv', rows)
    index = {(r['input'], r['mode'], r['config']): r for r in runs}
    pairs = [('a_only', 'highdiv'), ('b_only', 'highdiv'), ('a_plus_b', 'highdiv'),
             ('a_plus_b', 'a_only'), ('a_plus_b', 'b_only')]
    comparisons = []
    for mode in ('time900', 'n100_t900'):
        for name in sorted({r['input'] for r in runs}):
            for left, right in pairs:
                a, b = index[name, mode, left], index[name, mode, right]
                comparisons.append(dict(input=name, mode=mode, comparison=left+' - '+right,
                    delta_covered_bits=a['covered']-b['covered'],
                    delta_percentage_points=a['percentage']-b['percentage'],
                    both_complete100=a['complete100'] and b['complete100'],
                    strict_C100=mode=='n100_t900' and a['complete100'] and b['complete100']))
    save('paired_comparisons.csv', comparisons)
    print(f'Wrote {len(rows)} mechanism rows and {len(comparisons)} paired comparisons.')


if __name__ == '__main__':
    main()
