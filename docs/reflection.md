# Engineering Reflection

## 1. Why should source profiling occur before implementation of ingestion?

Building first and discovering C0090 afterward would mean the pipeline was already written assuming `customer_id` was unique, perhaps used as a join key or primary key. Fixing that after the fact means tracing everywhere the bad assumption spread and reworking the schema, not just adding a rule. Profiling first turned it into a design decision: `customer_id` became a candidate key, not a guaranteed unique one, from the start. Profiling is cheap and reversible; fixing a wrong assumption baked into a running pipeline is expensive and often not.

## 2. What is the difference between source event time / updated_at and ingestion time?

`updated_at` is source event time, when the record last changed at the source, controlled by the source. `_ingested_at` is ingestion time, when the pipeline pulled it, controlled by the pipeline. A gap between the two just means the event sat in the source before this pipeline ran. Incremental logic must key off `updated_at`; `_ingested_at` is only useful for debugging and auditing runs.

## 3. Why is event_id alone insufficient to decide which duplicate API record to keep?

The API repeats two event IDs with newer timestamps, meaning the duplicate is an update, not a copy. Keeping whichever record is seen first would keep the stale version. `updated_at` has to be compared, with the newer value winning.

## 4. Why must watermark state advance only after successful persistence?

If the watermark is saved before the write is confirmed and the write then fails, the fetched events are lost silently, since the watermark already claims they're handled and the next run won't ask for them again. The watermark should only advance after the write succeeds, so a failed write leaves it unmoved and the next run safely re-fetches instead of silently skipping data.

## 5. What limitation does updated_after > watermark have when records share the same timestamp?

If a page boundary splits records sharing the same timestamp, the ones left out are never fetched again, since future runs only ask for timestamps strictly greater than the watermark. A single timestamp isn't precise enough to distinguish records within a tie. The fix is a composite watermark like `(updated_at, event_id)`, or using `>=` and relying on the duplicate key to discard repeats.

## 6. How is duplicate prevention related to idempotency?

Without dedup, even a "no-op" rerun could write duplicates if the watermark or pagination overlapped slightly, and a from-scratch rerun would duplicate everything. Idempotency is the goal: running once or many times should leave the same state. Duplicate prevention is what makes that hold whenever re-fetching happens. The watermark limits how much gets re-requested; dedup on `event_id` guarantees re-fetched data doesn't change the outcome.

## 7. Why should the raw area preserve source values instead of applying business transformations?

Raw data is the only version that can be trusted as exactly what the source sent. Cleaning on the way in bakes decisions, like which row is a duplicate, permanently into the only copy kept, with no way back if that decision is wrong. Keeping both C0090 rows untouched means the conflict can be resolved later, correctly, with the raw copy still available to reprocess from. The same logic applies to leaving `signup_date` as text and `shipping`/`metadata` nested: any parsing decision made on ingestion becomes irreversible if it later turns out wrong.

## 8. How could querying a production OLTP source for profiling or extraction degrade the application?

OLTP databases serve many small, fast transactions sharing finite CPU, memory, and I/O. A heavy analytical query competes for those same resources at a much larger scale, holding locks or saturating I/O for longer. That causes transactional queries to queue, connection pools to fill, and in worse cases, locks to block live writes. This is why the profiling queries used here (`COUNT(*)`, `LIMIT 10`, `information_schema`) stayed cheap and bounded rather than scanning full tables.

## 9. What would you change if the API had a rate limit of 60 requests per minute?

At 7 requests for 122 records, this run is nowhere close to the limit, but at scale I'd add a small delay between page requests to stay comfortably under it. I'd also stop treating a 429 as a hard failure: instead of `raise_for_status()` killing the run, the code should catch that status, respect `Retry-After` (or a fallback wait), retry the page, and cap the retries so a persistent limit fails cleanly instead of looping forever.

## 10. How would you extend this pipeline from a local raw area to PostgreSQL while preserving rerun safety?

The mechanism is an upsert, not a plain insert: `INSERT ... ON CONFLICT (event_id) DO UPDATE` or `DO NOTHING`. This mirrors the dictionary-based dedup from the JSONL pipeline, with `event_id` as the table's unique key so a rerun collides instead of duplicating. Since the source sends real updates under repeated `event_id`s, `DO UPDATE`, conditioned on the incoming `updated_at` being newer, is the right choice, carrying the same "newer wins" rule across the boundary from file to database.