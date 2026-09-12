# Ingestion Design

## Design Table

| Source | Method | Raw destination | Duplicate key | Incremental state |
|---|---|---|---|---|
| CSV / JSON / Parquet | File copy + manifest | `raw/files/` | File SHA-256 | N/A |
| REST API | Paginated GET | `raw/api/events.jsonl` | `event_id` | `max(updated_at)` |
| PostgreSQL | Inspection only in this lab | N/A | `ticket_id` | No change-tracking column; see CDC discussion below |

## How the file SHA-256 prevents duplicates on rerun

When the pipeline copies a file into `raw/files/`, it computes a SHA-256 hash of the file's contents and records that hash somewhere durable, a manifest, a metadata table, whatever the ingestion job checks against before copying. On the next run, before copying `customers.csv` again, the pipeline hashes it fresh and compares that hash against what's already recorded.

Two things can happen:

- **Same hash** means the file's contents haven't changed at all since the last run. The pipeline skips the copy entirely, since ingesting it again would just produce an identical duplicate landing in raw storage.
- **Different hash** means something in the file changed, even a single row, and the pipeline treats it as a new version worth landing, typically under a new path or partition (e.g., a new timestamped folder), rather than overwriting the old one.

The key thing this catches that filename or file size alone wouldn't: a file can be re-saved, re-exported, or re-delivered with the exact same name and even the same byte count, but hashing looks at the actual content, so it's a much stronger duplicate check than "have I seen this filename before." What it does not do is detect a duplicate at the row level; if `customers.csv` gets one new row added and 249 unchanged ones, the hash changes and the whole file is treated as new, since a whole-file hash can't tell you which specific rows inside changed.

## PostgreSQL incremental / CDC strategy

I'd argue for adding an `updated_at` column upstream, maintained by a trigger that sets it to `now()` on every `UPDATE` to the row. It's the most direct fix because it solves the actual root cause: the table has no field that says "this row changed," so incremental extraction has no watermark to filter on. Once that column exists, the same watermark pattern already used for the events API, filtering on `updated_at` since the last successful run, works here too, so the pipeline logic doesn't need a second, different incremental strategy just for Postgres.

The cost is real but bounded: it requires a schema migration and a trigger on a live production table, which means coordinating with whoever owns that database, testing the trigger doesn't slow down writes at any meaningful scale, and backfilling the column for existing rows, probably defaulting to `opened_at` for tickets that have never been updated. It's a one-time engineering cost, not an ongoing one.

The two alternatives are worth naming, since each has its own place:

- **Database-level CDC** (e.g., Postgres logical replication, Debezium reading the WAL) captures every row change automatically without touching the schema, and gives you the full change history, not just current state. It's the more powerful option, but it's meaningfully more infrastructure to stand up and operate — a replication slot, a CDC tool, a downstream consumer for the change stream — which is a lot of machinery for a 250-row ticket table.
- **Full snapshot comparison** (diffing today's full pull against yesterday's) needs no schema change and no new infrastructure at all, just a pull-and-diff job. But it scales badly: it's doing full-table work on every run to detect small changes, and it only tells you that a row changed, not when, which matters less here but would if the table grew.

Given the table's current size, I'd lean toward the `updated_at` column as the right long-term fix, with full snapshot diffing as an acceptable short-term stopgap if a schema change can't happen right away, and CDC being overkill until this table (or others like it) grow enough to justify that infrastructure.

