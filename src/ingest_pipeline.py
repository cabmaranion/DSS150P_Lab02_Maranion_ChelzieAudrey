"""Week 3 starter: rerunnable ingestion to a raw area.
Students implement file ingestion + paginated REST API ingestion + watermark + duplicate prevention.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; RAW=ROOT/'raw'; STATE=ROOT/'state'
API_URL='http://127.0.0.1:8000/api/events'

def utc_now(): return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def load_watermark():
    p=STATE/'api_watermark.json'
    if not p.exists(): return None
    return json.loads(p.read_text())['updated_at']

def save_watermark(value):
    STATE.mkdir(exist_ok=True)
    (STATE/'api_watermark.json').write_text(json.dumps({'updated_at':value},indent=2))

def ingest_files():
    """Task 3.1: copy source files to raw/files/ with a content-hash manifest.
    Reruns with unchanged content skip the copy instead of duplicating it.
    """
    raw_files = RAW / 'files'
    raw_files.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_files / 'manifest.jsonl'

    # Load hashes we have already ingested
    seen_hashes = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                seen_hashes.add(json.loads(line)['sha256'])

    sources = ['customers.csv', 'orders.json', 'products.parquet']
    copied = 0
    skipped = 0

    for name in sources:
        src = DATA / name
        if not src.exists():
            print(f"  MISSING: {name}")
            continue

        digest = sha256_file(src)

        if digest in seen_hashes:
            print(f"  skip   {name} (hash already ingested: {digest[:12]}...)")
            skipped += 1
            continue

        dest = raw_files / name
        shutil.copy2(src, dest)

        entry = {
            'source_file': name,
            'ingested_at': utc_now(),
            'bytes': src.stat().st_size,
            'sha256': digest,
        }
        with manifest_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')

        seen_hashes.add(digest)
        print(f"  copy   {name} ({entry['bytes']} bytes, {digest[:12]}...)")
        copied += 1

    print(f"files: {copied} copied, {skipped} skipped")
    return {'read': len(sources), 'written': copied, 'skipped': skipped}

def fetch_api_page(page, per_page=20, updated_after=None):
    params={'page':page,'per_page':per_page}
    if updated_after: params['updated_after']=updated_after
    r=requests.get(API_URL,params=params,timeout=30); r.raise_for_status(); return r.json()

def ingest_api():
    """Tasks 3.2-3.4: paginated fetch, dedupe by event_id, atomic write, watermark.
    The watermark only advances after the raw write succeeds.
    """
    raw_api = RAW / 'api'
    raw_api.mkdir(parents=True, exist_ok=True)
    out_path = raw_api / 'events.jsonl'

    watermark_before = load_watermark()
    print(f"  watermark before: {watermark_before}")

    fetched = []
    page = 1
    while True:
        payload = fetch_api_page(page, per_page=20, updated_after=watermark_before)
        items = payload['items']
        fetched.extend(items)
        print(f"  page {page}: {len(items)} records (total={payload['total']}, has_more={payload['has_more']})")
        if not payload['has_more']:
            break
        page += 1

    records_read = len(fetched)

    ingested_at = utc_now()
    for record in fetched:
        record['_ingested_at'] = ingested_at
        record['_source'] = API_URL

    by_id = {}
    for record in fetched:
        key = record['event_id']
        existing = by_id.get(key)
        if existing is None or record['updated_at'] > existing['updated_at']:
            by_id[key] = record

    deduped = list(by_id.values())
    duplicates_removed = records_read - len(deduped)
    print(f"  read {records_read}, kept {len(deduped)}, removed {duplicates_removed} duplicate event_id(s)")

    existing_records = {}
    if out_path.exists():
        for line in out_path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                rec = json.loads(line)
                existing_records[rec['event_id']] = rec

    for key, record in by_id.items():
        prior = existing_records.get(key)
        if prior is None or record['updated_at'] > prior['updated_at']:
            existing_records[key] = record

    final_records = sorted(existing_records.values(), key=lambda r: (r['updated_at'], r['event_id']))

    tmp_path = out_path.with_suffix('.jsonl.tmp')
    with tmp_path.open('w', encoding='utf-8') as f:
        for record in final_records:
            f.write(json.dumps(record) + '\n')
    tmp_path.replace(out_path)
    print(f"  wrote {len(final_records)} records to {out_path.name}")

    watermark_after = watermark_before
    if deduped:
        watermark_after = max(r['updated_at'] for r in deduped)
        save_watermark(watermark_after)
    print(f"  watermark after: {watermark_after}")

    return {
        'read': records_read,
        'written': len(final_records),
        'duplicates_removed': duplicates_removed,
        'watermark_before': watermark_before,
        'watermark_after': watermark_after,
    }

if __name__=='__main__':
    RAW.mkdir(exist_ok=True); STATE.mkdir(exist_ok=True)
    ingest_files(); ingest_api()
