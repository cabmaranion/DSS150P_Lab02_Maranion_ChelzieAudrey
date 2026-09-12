# Logical Schema

## customers

| Field | Source Representation | Logical Type | Nullable | Key Role | Definition |
|---|---|---|---|---|---|
| customer_id | string | string | no | candidate key (not currently unique) | Identifier assigned to a customer, formatted C####. |
| first_name | string | string | no | — | Customer's given name. |
| last_name | string | string | no | — | Customer's family name. |
| email | string | string | yes | — | Customer's contact email address; missing in 3 of 250 rows. |
| city | string | string | yes | — | City associated with the customer's address; missing in 2 of 250 rows. |
| signup_date | string (text in CSV) | date | no | — | Date the customer registered. |
| customer_segment | string | string (constrained enum: Professional, Retail, SME, Student) | no | — | Business segment the customer is classified under. |

## events (API)

| Field | Source Representation | Logical Type | Nullable | Key Role | Definition |
|---|---|---|---|---|---|
| event_id | string | string | no | candidate key | Identifier assigned to an individual event. |
| customer_id | string | string | no | foreign key (references customers.customer_id) | Identifier of the customer the event is attributed to. |
| event_type | string | string | no | — | Category or label describing what kind of event occurred. |
| amount | number | float64 | no | — | Numeric value associated with the event. |
| updated_at | string (text in JSON) | timestamp | no | — | Point in time the event record was last updated; used as the incremental watermark. |
| metadata | object | object (composite; not directly storable in a flat table) | no | — | Nested attribution data describing the event's source, decomposed into the two fields below. |
| metadata.channel | string (nested) | string | no | — | Channel through which the event originated. |
| metadata.campaign | string (nested) | string | no | — | Campaign the event is attributed to; absence is represented by the literal string "none" rather than a null. |

**Nullability note:** these nullable/not-nullable calls are based on what we actually saw in the data, not on any rule the source has committed to. For customers, that's the full 250 rows, so the pattern is at least reliable across the whole set we have. For events, it's only 50 of 122, less than half, so "no nulls observed" there is a weaker claim; it just hasn't happened yet in this sample, not that it can't happen. The real risk is a field like `amount` or `metadata.campaign` looking safe now and then showing up null the first time an edge case hits, a refund event with no amount, a direct visit with no campaign, once we see more data or a schema definition from the source owner. Until then, treat every "no" here as "not null so far," not "guaranteed not null."