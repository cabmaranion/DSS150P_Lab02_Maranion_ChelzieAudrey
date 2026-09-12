# Watermark Semantics

For this laboratory, the API watermark is the greatest successfully persisted `updated_at` value. On the next run, the pipeline requests only records with `updated_at` greater than the saved watermark. The watermark is operational state, not source data.

## 1. What could go wrong if the watermark is saved before the raw file is successfully written?

If the write fails after the watermark is saved, the fetched events are lost. The watermark already says "handled up to here," so the next run never asks for them again. Fix: only save the watermark after the write is confirmed successful.

## 2. What could go wrong if the source allows multiple records with exactly the same timestamp?

If a page boundary splits records that share the same timestamp, the ones left out are never fetched again, since the next run only asks for timestamps strictly greater than the watermark. Fix: break ties using a composite watermark of `(updated_at, event_id)`, or use `>=` and rely on the duplicate key to drop repeats.

## 3. One limitation of this simplified watermark

It can't handle late-arriving records — ones whose `updated_at` is earlier than the current watermark but which only become visible after the watermark has already moved past that point. These get silently skipped forever.

## 4. One production-grade mitigation

Use a lookback window: request records from `watermark - N minutes` instead of a hard cutoff, and rely on the duplicate key (`event_id`) to safely drop anything already ingested. This trades a little redundant fetching for not missing late data.