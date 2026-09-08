# Database Mining Workflow

This document is `doc-init`’s internal database-evidence subflow, not a standalone skill. The goal is not to export a database dictionary, and not to profile the whole database up front, but to progressively distill “how real database facts affect AI-written code.”

`<DOC_INIT_DIR>` in this document means the directory that contains `doc-init/SKILL.md`. Resolve that directory before running scripts; do not write a maintainer’s local machine path into project docs or command examples.

## Core rules

- Read-only end to end: only metadata queries and `SELECT` are allowed; forbid write SQL, DDL, table locks, and destructive operations.
- When the user has authorized database mining, missing local drivers or lightweight clients may be installed into the skill-local environment; do not install large GUI tools or make unreclaimable system-level changes.
- Treat the environment as test by default; keep connection config and value samples fully visible. Enable the script’s `--mask-sensitive` only when the user explicitly requires masking, or the current context is clearly not test data.
- Dialect differences are handled on the spot by scripts, drivers, and the model; do not build encyclopedic references for common databases.
- Default to catalog only: table list, column list, coarse PK/index info, comments; do not scan data by default, and do not default to `count(*)` / `count(distinct)` / whole-database profile.
- Call `sample-table` / `analyze-field` for deep scans only after a concrete domain, table, or field is identified.
- If the user goal is “directory-level,” “catalog-only,” “table/column catalog only,” or “help partition domains,” stop after catalog / classify-catalog / plan-domain-scan / summarize-catalog; do not sample automatically.
- Scripts must be cross-platform first: implement core capability in Python; do not depend on bash, grep, sed, awk, rsync, timeout, or Unix-only paths.
- Critical tables must get per-field analysis during domain deep scans; non-critical tables get catalog only.

## Reading order

Read selectively by task stage; do not dump every reference into context at once:

- Before discovering connection sources, read `references/database-mining/config-discovery.md`.
- Before connecting and sampling, read `references/database-mining/safety-and-sampling.md`.
- Before domain deep scans and per-field analysis, read `references/database-mining/critical-table-analysis.md`.
- When an evidence pack is needed, read `references/database-mining/evidence-pack-format.md`.

## Step 1 — Discover connection sources

Identify the project ecosystem first, then scan config, env-var templates, container/deploy files, ORM/data-source init code, and secret references.

```bash
python3 <DOC_INIT_DIR>/scripts/db_miner.py discover-config --root .
```

If no connection is found and the task needs database facts, explain the read-only purpose to the user and request a connection string or local connection name. If the user explicitly asks not to be questioned, emit a low-confidence note that database evidence is missing.

## Step 2 — Establish read-only and sampling boundaries

Before connecting, confirm:

- Query limits, sample caps, and timeout policy are set.
- Whether masking is needed; default is no masking—add `--mask-sensitive` to the script only when clearly required.
- Whether the current task allows installing lightweight dependencies; if so, prefer a local venv or user-level packages, and do not install GUIs.

## Step 3 — Lightweight catalog

Use project-existing tools, system clients, or `scripts/db_miner.py`. The script supports native SQLite; for other databases prefer a SQLAlchemy URL and installed drivers. On Windows, `py -3` may replace `python3`.

```bash
python3 <DOC_INIT_DIR>/scripts/db_miner.py test-connection --url '<readonly-url>'
python3 <DOC_INIT_DIR>/scripts/db_miner.py catalog --url '<readonly-url>' --output db-catalog.json
```

You may write the test-environment connection source into the evidence pack for reuse; if the user requires masking, keep only the masked source.

Catalog is only for building a database map that helps domain partitioning and critical-table candidates; forbid whole-database data profiling at this step.

## Step 4 — Catalog semantics and domain deep-scan plan

```bash
python3 <DOC_INIT_DIR>/scripts/db_miner.py classify-catalog --catalog db-catalog.json --output db-domain-hints.json
python3 <DOC_INIT_DIR>/scripts/db_miner.py plan-domain-scan --catalog db-catalog.json --domain customer --keywords user,member,customer --output db-domain-plan.json
python3 <DOC_INIT_DIR>/scripts/db_miner.py summarize-catalog --catalog db-catalog.json --domain-hints db-domain-hints.json --domain-plan db-domain-plan.json --output db-catalog-summary.json
```

This step is mainly model semantic understanding of table names, column names, comments, and code entry points: judge domains, critical-table candidates, and which tables need later deep scans. Scripts only supply candidate hints; they do not replace model judgment.

For directory-level / catalog-only tasks, close with `summarize-catalog`: it only reads already-generated catalog / domain hints / domain plan JSON—no DB connection, no row-level data, no stats. Do not write large ad-hoc parsing scripts just to produce a report; if the summary is insufficient, list gaps as deep-scan items before later domain KB generation.

## Step 5 — Domain / table / field deep dive

Decide critical tables first, then analyze critical tables field by field:

- Field structure: type, comment, default, nullable, index participation.
- Code entry points: how Entity/Mapper/SQL/Service/Flow/Job read and write.
- Data facts: a few real sample values; NULL/empty string/special sentinel values in the sample; enum candidates in the sample; obvious extremes and time formats.
- Business judgment: real field semantics, unconventional design, consistency with code enums.
- AI pitfalls: what goes wrong if the field is ignored.
- Doc target: target KB/Guide section.

```bash
python3 <DOC_INIT_DIR>/scripts/db_miner.py sample-table --url '<readonly-url>' --catalog db-catalog.json --tables table_a,table_b --sample-rows 30 --output db-samples.json
python3 <DOC_INIT_DIR>/scripts/db_miner.py analyze-field --url '<readonly-url>' --catalog db-catalog.json --field table_a.status --sample-rows 50 --output db-field-status.json
```

Default to sample-first; do not run full-table stats. Add explicit stats options only when the user clearly requires stats, or field semantics must depend on stats; do not make count the default path.

Even when a critical table has many columns, do not only pick the obvious ones; batching is fine, but the evidence pack must mark which fields are analyzed and which are not.

## Step 6 — Export the evidence pack

```bash
python3 <DOC_INIT_DIR>/scripts/db_miner.py export-evidence \
  --catalog db-catalog.json \
  --domain-plan db-domain-plan.json \
  --samples db-samples.json \
  --output db-evidence-pack.json
```

The evidence pack must answer:

- Which domains were reinforced by database facts.
- Which domains used catalog only, and which got table/field deep dives.
- Which fields have special semantics, historical-compatibility values, or unconventional design.
- Which findings should enter domain KBs, and which should become shared Guide candidates.
- Which conclusions are low-confidence and need further user or runtime confirmation.

## Working with project docs

When used for `doc-init`, database evidence only reinforces the domain knowledge network: table and field entry points go into the matching domain KB; cross-domain sharding/dictionary/config/process mechanisms go into Guides; missing connection or access failure goes into the self-assessment as “missing real data semantics.”

For later doc sync or day-to-day development, generate a small evidence pack around the current module, table, field, or bug; keep only reusable business facts, and do not turn one-off query results into long-lived docs.
