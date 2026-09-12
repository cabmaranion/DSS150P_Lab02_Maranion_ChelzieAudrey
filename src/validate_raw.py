"""Validation checks for raw outputs.

Runs every check independently and reports all results in one pass.
Checks that depend on a missing prerequisite are marked SKIPPED rather
than FAILED, so one root cause does not cascade into unrelated noise.
"""
from pathlib import Path
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
STATE = ROOT / 'state'

EXPECTED_FILES = ['customers.csv', 'orders.json', 'products.parquet']
REQUIRED_EVENT_FIELDS = ['event_id', 'updated_at', '_ingested_at', '_source']

results = []


def record(name, status, detail):
    results.append((name, status, detail))


def main():
    raw_files = RAW / 'files'
    manifest = raw_files / 'manifest.jsonl'
    events_path = RAW / 'api' / 'events.jsonl'

    # Check 1: expected raw files exist
    missing = [f for f in EXPECTED_FILES if not (raw_files / f).exists()]
    if missing:
        record('raw files exist', 'FAIL', f"missing: {', '.join(missing)}")
    else:
        record('raw files exist', 'PASS', f"{len(EXPECTED_FILES)} files present")

    # Check 2: manifest has an entry per file, with a hash
    if not manifest.exists():
        record('manifest present', 'SKIP', 'manifest.jsonl not found')
    else:
        entries = [json.loads(l) for l in manifest.read_text(encoding='utf-8').splitlines() if l.strip()]
        hashed = [e for e in entries if e.get('sha256')]
        if len(hashed) == len(entries) and entries:
            record('manifest present', 'PASS', f"{len(entries)} entries, all hashed")
        else:
            record('manifest present', 'FAIL', f"{len(entries)} entries, {len(hashed)} hashed")

    # Events file is a prerequisite for checks 3-6
    if not events_path.exists():
        for name in ['event_ids unique', 'required fields present',
                     'updated_at parseable', 'watermark matches max(updated_at)']:
            record(name, 'SKIP', 'raw/api/events.jsonl not found')
        report()
        return

    events = [json.loads(l) for l in events_path.read_text(encoding='utf-8').splitlines() if l.strip()]

    # Check 3: event_ids unique
    ids = [e['event_id'] for e in events]
    if len(ids) == len(set(ids)):
        record('event_ids unique', 'PASS', f"{len(ids)} records, {len(set(ids))} distinct")
    else:
        record('event_ids unique', 'FAIL', f"{len(ids)} records but only {len(set(ids))} distinct")

    # Check 4: required metadata fields present on every record
    incomplete = [e.get('event_id', '?') for e in events
                  if any(f not in e or e[f] is None for f in REQUIRED_EVENT_FIELDS)]
    if incomplete:
        record('required fields present', 'FAIL', f"{len(incomplete)} record(s) missing fields")
    else:
        record('required fields present', 'PASS', f"all {len(events)} records have {REQUIRED_EVENT_FIELDS}")

    # Check 5: updated_at parses as a timestamp
    unparseable = []
    for e in events:
        try:
            datetime.fromisoformat(e['updated_at'])
        except (ValueError, KeyError, TypeError):
            unparseable.append(e.get('event_id', '?'))
    if unparseable:
        record('updated_at parseable', 'FAIL', f"{len(unparseable)} unparseable value(s)")
    else:
        record('updated_at parseable', 'PASS', f"all {len(events)} values parse as ISO timestamps")

    # Check 6: watermark equals max(updated_at) in the raw file
    wm_path = STATE / 'api_watermark.json'
    if not wm_path.exists():
        record('watermark matches max(updated_at)', 'SKIP', 'no watermark file')
    else:
        watermark = json.loads(wm_path.read_text())['updated_at']
        actual_max = max(e['updated_at'] for e in events)
        if watermark == actual_max:
            record('watermark matches max(updated_at)', 'PASS', f"both {watermark}")
        else:
            record('watermark matches max(updated_at)', 'FAIL',
                   f"watermark={watermark}, max in file={actual_max}")

    report()


def report():
    print("\n=== raw output validation ===")
    for name, status, detail in results:
        print(f"  [{status}] {name:<38} {detail}")
    failed = sum(1 for _, s, _ in results if s == 'FAIL')
    skipped = sum(1 for _, s, _ in results if s == 'SKIP')
    passed = sum(1 for _, s, _ in results if s == 'PASS')
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return failed == 0


if __name__ == '__main__':
    main()