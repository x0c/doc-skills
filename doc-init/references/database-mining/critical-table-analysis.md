# Critical Table Analysis

Per-field analysis of critical tables is the core value of this skill. Do not stop at table names, primary keys, and a few obvious columns; subtle field differences often decide whether AI writes wrong code.

## Critical-table criteria

Prefer a table as a critical-table candidate when any of these hold:

- Primary tables, detail tables, relation tables, config tables, or process-instance tables that the current business domain reads and writes directly.
- Columns involving amount, balance, points, inventory, status, type, permission, tenant, shard, validity period, or idempotency keys.
- Code has complex SQL, XML mappers, dynamic conditions, handwritten joins, batch updates, or async compensation.
- From the catalog: many columns, clear history/log/detail traits, sparse comments but high business risk.
- Real value domains disagree with code enums, comments, or naming.
- Dictionary, config, process, sharding, or plugin-metadata tables shared across domains.

## Per-field template

Analyze every critical-table column with the structure below; batch when there are many columns, but always mark columns not yet analyzed.

```md
### Field: [column_name]

- Type / constraints: [type, nullable, default, index/unique/fk]
- Column comment: [db comment or none]
- Code read/write entry points: [Entity/Mapper/SQL/Service/Flow/Job]
- Data facts: [a few sample values; NULL/empty string/special sentinel values in the sample; enum candidates; time formats; obvious extremes]
- Business judgment: [real field semantics; any unconventional design; historical compatibility]
- AI pitfalls: [what code mistakes follow from ignoring this field]
- Confidence: [high/medium/low; evidence sources]
- Doc target: [target KB/Guide section]
```

## Field types that must get attention

- Status / type: whether the sample contains historical, canary, or deprecated values outside code enums; do field-level spot checks when needed.
- Amount / quantity / points: unit, precision, sign, frozen/available/cumulative semantics.
- Time: create time, effective time, expire time, redemption time, business day; whether `NULL` and extreme dates have special meaning.
- Soft delete / validity flags: deleted values, valid values, whether historical data is inverted.
- Tenant / brand / store / plan: isolation keys, shard keys, default tenant or global values.
- Idempotency / external order IDs: uniqueness, duplicate submit, compensation chains.
- JSON/text config: key structure, switches, expressions, process-node parameters.
- Extension columns: record them when they look unused but already hold real business values.

## Unconventional semantics

Prioritize these as AI pitfalls:

- The column name says A, but real data or code semantics say B.
- Sentinel values like `NULL`, `0`, `-1`, empty string, or `9999-12-31` carry business meaning.
- A main-table column is only cache/redundancy; the real validation semantics live on a detail table.
- Code enums may be incomplete; samples or field spot checks show the database keeps historical values.
- Column comments are stale; the real distribution contradicts the comment.
- No FK but a strong business association, or an FK exists but code does not use FK semantics.

## Weak-relationship inference

Weak relationships are candidates only—never write them as FK facts. Evidence includes:

- Name matches: `*_id`, `*_code`, `tenant_id`, `prog_id`.
- Data coverage: column values largely appear as another table’s primary/unique key.
- Index combinations: multiple columns jointly express business uniqueness.
- Code joins: Mapper, SQL, ORM relation, or service query order.
- Table naming: main/detail/log/history/relation/extension tables.

When outputting, always state confidence and evidence sources.
