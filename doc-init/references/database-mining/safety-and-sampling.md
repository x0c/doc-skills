# Safety And Sampling

Database mining defaults to local or test environments and prioritizes information completeness; the main safety boundaries are read-only, progressive, limited volume, and reclaimable tool installs.

## Read-only boundary

- Only metadata queries, `SELECT`, read-only explain, or lightweight stats are allowed.
- Forbid `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `ALTER`, `DROP`, `CREATE`, `GRANT`, `LOCK`, manual write transactions, and stored-procedure calls.
- During catalog, forbid full-table `count(*)`, `count(distinct)`, large sorts, large aggregations, or unbounded joins.
- During table/field deep dives, sample by default; stats queries must be explicitly enabled, with an explanation of why field semantics depend on stats.
- On connection failure, insufficient permissions, or suspected high-risk production access, report missing items; do not bypass safety limits.

## Tool installation

When the user authorizes database mining, missing lightweight drivers / CLIs may be prepared directly:

- Prefer tools already in the project or commands already on the system.
- Next, use a skill-local venv or user-level Python packages.
- Do not install large GUI tools.
- Do not make unreclaimable system-level changes.
- Installs must serve only read-only connections and metadata/sample queries.

## Progressive levels

Default levels:

1. catalog: read only table/column/PK/index/comment metadata for domain partitioning.
2. sample-table: sample a few rows from specified tables inside a clear business domain, to see what real values look like.
3. analyze-field: spot-check specific columns to confirm special values, enum candidates, NULL semantics, and unconventional design.

Do not skip catalog and sample the whole database; do not start with whole-database stats.

## Sampling limits

Default recommendations:

- Sample rows per table: 20–100.
- Max tables sampled per run: 10; for large projects, first narrow by domain / critical tables.
- Value summaries are based on the sample and do not represent full-database distribution by default.
- JSON/text columns: analyze only key structure, length, and obvious enums; do not dump large raw payloads.
- Prefer bounded samples for large tables; do not full-scan.

## Data visibility

No masking by default, because this skill aims to mine real business semantics from test data. Enable masking only when:

- The user explicitly requires masking.
- The current connection is clearly not a test environment.
- Output will be submitted to an external system or shared with people without access.

When masking is enabled, scripts use `--mask-sensitive`, then handle phone numbers, emails, tokens, passwords, secrets, and similar by column name and value patterns.

Even without masking, do not export unbounded data; long-lived docs should prioritize business facts, distributions, special values, semantic judgments, and AI pitfalls—not paste large raw rows.

## Confidence

- High: schema, comments, code read/write paths, and data distribution corroborate each other.
- Medium: schema and data distribution agree, but code or user confirmation is missing.
- Low: based only on column names, a small sample, or weak-relationship inference.

Low-confidence content may go into the evidence pack, but must be marked pending confirmation when filed into long-lived docs.
