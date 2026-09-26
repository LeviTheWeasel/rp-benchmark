"""Structural validation of this increment only; never computes judgments."""
import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent
SESSION = ['S.1_consistency_over_time', 'S.2_degradation_resistance',
           'S.3_narrative_momentum', 'S.4_adaptive_responsiveness',
           'S.5_agency_respect_session', 'S.6_temporal_reasoning']
STANDARD = ['2.1_anti_purple_prose', '2.2_anti_repetition',
            '2.5_show_dont_tell', '2.6_subtext', '2.7_pacing']
TOP = {'session_id', 'session_dimensions', 'standard_dimensions',
       'quality_trajectory', 'overall', 'overall_notes'}
PHASES = {'early_quality', 'mid_quality', 'late_quality'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fingerprint():
    names = ['TASK.md', 'RUBRIC.md'] + [f'sessions_part{i:02}.json' for i in range(1, 11)]
    return {n: hashlib.sha256((SOURCE / n).read_bytes()).hexdigest() for n in names}


def number(value):
    assert type(value) in (int, float) and math.isfinite(value) and 1 <= value <= 5, value


def inputs():
    parts = {i: read(SOURCE / f'sessions_part{i:02}.json') for i in range(1, 11)}
    ids = []
    for part, items in parts.items():
        assert isinstance(items, list) and len(items) == (3 if part == 10 else 10)
        for item in items:
            assert set(item) == {'session_id', 'character_name', 'user_name', 'num_turns', 'transcript'}
            assert re.fullmatch(r'i\d+', item['session_id'])
            assert isinstance(item['transcript'], str)
            ids.append(item['session_id'])
    assert len(ids) == len(set(ids)) == 93
    return parts


def validate(part, source):
    rows = read(OUT / f'external_part{part:02}.json')
    assert isinstance(rows, list) and len(rows) == len(source)
    assert [r['session_id'] for r in rows] == [r['session_id'] for r in source]
    for row in rows:
        assert set(row) == TOP, row['session_id']
        for group, keys in [('session_dimensions', SESSION), ('standard_dimensions', STANDARD)]:
            assert set(row[group]) == set(keys)
            for key in keys:
                item = row[group][key]
                extras = {'violation_count'} if key == SESSION[4] else {'contradictions'} if key == SESSION[5] else set()
                assert set(item) == {'score', 'rationale'} | extras
                number(item['score'])
                assert isinstance(item['rationale'], str) and item['rationale'].strip()
                assert '\n' not in item['rationale']
        count = row['session_dimensions'][SESSION[4]]['violation_count']
        assert type(count) is int and count >= 0
        contradictions = row['session_dimensions'][SESSION[5]]['contradictions']
        assert isinstance(contradictions, list) and all(isinstance(x, str) and x.strip() for x in contradictions)
        trajectory = row['quality_trajectory']
        assert set(trajectory) == PHASES | {'degradation_detected'}
        assert type(trajectory['degradation_detected']) is bool
        for field in PHASES:
            number(trajectory[field])
        number(row['overall'])
        assert isinstance(row['overall_notes'], str) and row['overall_notes'].strip()
    return rows


def validate_ledgers(source):
    assignment = read(OUT / 'assignment.json')['assignments']
    for letter, parts in assignment.items():
        expected = {r['session_id']: len(r['transcript']) for p in parts for r in source[p]}
        ledger = (OUT / f'reading_ledger_{letter}.md').read_text(encoding='utf-8')
        found = {}
        for line in ledger.splitlines():
            ids = re.findall(r'\bi\d{3}\b', line)
            spans = [(int(a), int(b)) for a, b in re.findall(r'[\[(](\d+),\s*(\d+)\)', line)]
            if len(ids) != 1 or not spans:
                continue
            assert ids[0] not in found, ('duplicate ledger entry', ids[0])
            assert spans[0][0] == 0
            assert all(a < b for a, b in spans)
            assert all(spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1))
            found[ids[0]] = spans[-1][1]
        assert found == expected, ('ledger coverage mismatch', letter, found, expected)
        print(f'ledger {letter}: PASS ({len(found)} complete transcript ranges)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', action='store_true')
    parser.add_argument('--parts', type=int, nargs='+')
    args = parser.parse_args()
    source = inputs()
    hashes = fingerprint()
    if args.snapshot:
        with (OUT / 'input_sha256.json').open('x', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2)
            f.write('\n')
        print('Input snapshot: 10 parts, 93 unique opaque IDs; hashes saved.')
    else:
        assert read(OUT / 'input_sha256.json') == hashes, 'INPUTS CHANGED'
        selected = args.parts or list(range(1, 11))
        rows = []
        for part in selected:
            rows.extend(validate(part, source[part]))
            print(f'part {part:02}: PASS')
        values = [r['overall'] for r in rows]
        summary = dict(parts=selected, sessions=len(values), min=min(values),
                       median=statistics.median(values), max=max(values), input_hashes_unchanged=True)
        print(json.dumps(summary))
        if not args.parts:
            validate_ledgers(source)
            summary['ledger_ranges_verified'] = True
            with (OUT / 'validation.json').open('w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
                f.write('\n')
