# Evidence Pack Format

The evidence pack is an intermediate artifact for `doc-init`, `doc-update`, or day-to-day development. Do not let database mining replace domain knowledge bases.

## JSON top-level structure

```json
{
  "metadata": {
    "generated_at": "YYYY-MM-DDTHH:mm:ssZ",
    "database_type": "postgresql/mysql/sqlite/unknown",
    "connection_source": "config source or connection string; record in full by default, mask only when the user asks",
    "scan_level": "catalog/domain/table/field",
    "sampling_policy": {
      "sample_rows_per_table": 30,
      "mask_sensitive": false,
      "counts_enabled": false
    }
  },
  "domains": [],
  "tables": [],
  "field_findings": [],
  "relationship_findings": [],
  "guide_candidates": [],
  "doc_targets": [],
  "coverage": {}
}
```

## Field findings

```json
{
  "table": "value_balance_detail",
  "column": "expire_time",
  "evidence": {
    "schema": "timestamp nullable",
    "sample": "NULL appears in the sample",
    "code_refs": ["ValueBalanceDetailMapper"]
  },
  "business_interpretation": "NULL means permanently valid",
  "ai_risk": "Writing only expire_time > now() misses permanently valid detail rows",
  "confidence": "high",
  "doc_target": {
    "path": "docs/PAYMENT_KNOWLEDGE_BASE.md",
    "section": "Core business rules and implicit constraints"
  }
}
```

## Table findings

```json
{
  "table": "customer",
  "role": "business primary table",
  "domain": "CUSTOMER",
  "why_critical": ["primary table of the current domain", "has status columns", "read/written by multiple services"],
  "field_analysis_status": {
    "analyzed": ["id", "status", "tenant_id"],
    "not_analyzed": ["remark_ext"]
  },
  "doc_target": "docs/CUSTOMER_KNOWLEDGE_BASE.md"
}
```

## Guide candidates

```json
{
  "topic": "SHARDING",
  "reason": "Multiple domains share shard keys, shard metadata, and routing rules",
  "evidence": ["multiple tables contain prog_id", "a shard metadata table exists", "routing components exist in code"],
  "doc_target": "docs/SHARDING_GUIDE.md",
  "confidence": "medium"
}
```

## Filable Markdown snippets

Each finding may attach a short snippet, but do not turn long-lived docs into raw data dumps:

```md
`value_balance_detail.expire_time` allows `NULL` in the data. Combined with deduction SQL, `NULL` more likely means permanently valid and should not be filtered as dirty data. When changing balance deduction or validity checks, always include an `expire_time IS NULL` branch. Confidence: high.
```

## Coverage

The end of the evidence pack must state:

- Whether the database was connected / not connected.
- Schemas and table counts already cataloged.
- Tables already sample-table’d.
- Fields already analyze-field’d.
- Domains that only got catalog and have not been deep-scanned yet.
- Low-confidence inferences and items needing user confirmation.
