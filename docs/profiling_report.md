# Source Profiling Report

## 1. Source Inventory
| Source | Type | Rows/Records | Key | Update Pattern | Quality Findings |
|---|---|---:|---|---|---|
| customers.csv | CSV file | 250 | customer_id (not unique) | one-time snapshot | 3 missing emails, 2 missing cities, 2 duplicate rows, C0090 maps to two people |
| orders.json | JSON file | 250 | order_id | one-time snapshot | zero nulls across all fields; nested `shipping` object (region + method) needs flattening or JSONB decision before it fits a flat table |
| products.parquet | Parquet file | 200 | product_id | one-time snapshot | schema preserved on read; `stock_quantity` stored as int32 (vs int64 inferred by CSV/JSON), showing Parquet's stored types are more precise than CSV/JSON's inferred ones |
| events API | REST API | 122 total (10 per page) | event_id | incremental — `updated_after` param and timestamped records imply ongoing change; `has_more=True` on page 1 confirms pagination, not a one-time pull | nested `metadata` object with channel and campaign, same pattern as orders' `shipping` — needs a flattening or JSONB decision too |
| support_tickets | Postgres table | 250 | ticket_id | live/continuously updated — tickets open, get assigned, and resolve in real time | 4 unassigned tickets; `resolved_at` null only for Open/In Progress status (expected, not a defect) |

## 2. Schema Findings

Parquet preserves a precise, stored schema on read, while CSV and JSON have to infer types from raw text. The clearest evidence is `stock_quantity`: Parquet reads it back as `int32`, while CSV and JSON both widen it to `int64`, because they're guessing the safest numeric type rather than reading a type that was actually stored. So this isn't three formats with different type systems, it's one format that knows its types and two that are inferring them, and happening to infer the same thing.

Two sources, `orders.json` and the events API, contain nested objects (`shipping` with region and method; `metadata` with channel and campaign) that a flat table can't hold as-is. Two options exist for handling them: flatten each nested field into its own column (simple, but assumes one value per record and no future sub-structure), or keep the object as a JSONB column in Postgres (preserves flexibility for fields added later, at the cost of weaker enforcement on valid values compared to constrained columns).

## 3. Data Quality Findings

1. `customer_id` C0090 is assigned to two different people, meaning the field isn't actually unique despite being the natural key.
2. Two rows in the customers table are exact duplicates, not just similar, full row matches.
3. `signup_date` arrives as text rather than a parsed date type, so anything downstream needs to cast it before doing date math.
4. `resolved_at` is null only for tickets still Open or In Progress, which is expected and consistent, not a data quality problem.
5. Parquet preserved `stock_quantity` as `int32` while CSV and JSON both widened it to `int64`, showing Parquet's stored schema beats CSV/JSON's inferred one.

## 4. Recommended Acquisition Method

- **customers.csv, orders.json, products.parquet**: read directly from disk as a one-time batch load. They're static snapshots, not live sources, so there's no incremental logic needed beyond re-running the load if a fresh file is dropped.
- **events API**: page through using the API's own pagination, tracking `has_more` until it returns false, and use `updated_after` as a watermark on subsequent runs so each pull only fetches records changed since the last one.
- **support_tickets (Postgres)**: no reliable change-tracking column exists (`opened_at` only marks creation, `resolved_at` only fires on resolution), so a true incremental pull isn't straightforward. In the near term, extract via full table pull on each run, or bound by `opened_at` for new tickets only, accepting that status changes on existing tickets (Open → In Progress → Resolved) would be missed.

## 5. Risks and Assumptions

- The C0090 duplicate can't be resolved from the data alone; it needs to go back to the source owner to determine which record (if either) is correct.
- The three flat files are treated as one-time snapshots, but their real-world update cadence is unknown. If customers.csv is actually refreshed weekly upstream, the "one-time" assumption breaks.
- The events API may add new fields or change its schema over time; the pipeline should tolerate unexpected fields rather than fail on them.
- `support_tickets` has no `updated_at` column, so there's no way to reliably detect that an existing row changed (e.g. a status update) without re-pulling the full table. Incremental extraction would require either a schema change upstream (adding `updated_at`) or accepting the cost of full pulls.
- Row counts and null patterns reflect the data at the time of profiling only; they're not guaranteed to hold on the next pull, especially for the live Postgres source.