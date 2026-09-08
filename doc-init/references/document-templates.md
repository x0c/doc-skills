# Document Templates

This document defines templates and root-entry rules used when doc-init generates project docs. Read it after the knowledge-boundary report and targeted Q&A.

## Contents

- Domain knowledge-base template
- Guide template
- Root AGENTS.md
- Project-root CLAUDE.md

## Domain knowledge-base template

Generate and write the file immediately after that domain’s Q&A—do not wait for other domains.

Before generating, finish domain-language normalization: pick one canonical term for core concepts and use it stably in body text; keep code class/enum/table/field/API parameter names verbatim in entry indexes or first-appearance parentheses. Do not default a “Glossary” section. Only homonyms, synonyms, or parameter mix-ups that would make AI write wrong code go into §6 `【Disambiguation】`.

```markdown
# [Domain] Knowledge Base

## §0 Contents

| § | Title | When |
|---|------|------|
| §1 | Business background and core concepts | First contact with this domain |
| §1.5 | Architecture overview | Quick layered mental model (mermaid) |
| §2 | Core business flows / state machines | Main flows and status enums |
| §2.5 | Physical path cheat sheet | Locate code dirs directly (glob/ls) |
| §3 | Code entry index | Find entries by task scenario |
| §4 | Table and field entry index | When changing tables/fields/queries |
| §5 | Flow / component / job / MQ entry index | When changing orchestration / cron / messaging |
| §6 | Core business rules and hidden constraints | AI pitfalls to scan before changing code |
| §7 | Validation paths | How to verify correctness after changes |
| §8 | Related docs | Cross-domain reading guides |
| §9 | Coverage and to-be-filled items | Doc confidence and gaps |

## §1 Business background and core concepts
[Business positioning, who it serves, role in the system, core concepts. Use unified canonical terms; on first appearance, parenthesize code entity / enum / main table aliases when needed]

## §1.5 Architecture overview

[1–2 mermaid diagrams for a quick layered call model. Mandatory for core domains; optional for standard domains.]

**Diagram selection guide** (pick the type that most reduces cognitive cost for the domain):

| Domain trait | Recommended diagram | mermaid syntax |
|--------|---------|-------------|
| Clear layered calls (Controller→Service→Repository) | Layered call graph | `graph TD` |
| State transitions are core (order/approval/account) | State machine | `stateDiagram-v2` |
| Event-driven / async (MQ/Event/callbacks) | Sequence | `sequenceDiagram` |
| Complex entity relations (multi-table / aggregate roots) | ER | `erDiagram` |
| Inheritance / strategy (multiple implementations / plugins) | Class hierarchy | `classDiagram` |

- Prefer: choose from the table by domain trait; fill real project class names
- Label nodes with actual class/component names—no abstract placeholders
- Complex domains may combine two types (e.g. layered + state)

## §2 Core business flows / state machines
[Main flows, status enums, transitions, terminal states, idempotency semantics, key branches]

## §2.5 Physical path cheat sheet

| Directory (relative to project root) | Contents | Key classes / file count |
|------|------|--------|
| [full relative path; no `...` ellipsis] | [code kinds in this dir] | [representative class names or file count] |

Paths must start from the project root (e.g. `src/main/java/com/example/payment/service/`); do not omit middle segments with `...`. Agents should glob/Read the target without a second search for physical location.

## §3 This domain’s code entry index
| Scenario | Entry | Class/method/config | Notes |
|---|---|---|---|
| [when doing which task] | [API/service/component/job/MQ] | [path or symbol] | [responsibility] |

## §4 This domain’s table and field entry index
| Table/field | Entity/Mapper | Business meaning | Change notes |
|---|---|---|---|
| [table.field] | [class] | [field meaning] | [sharding/tenant/status/money/time notes] |

## §5 This domain’s flow / component / job / MQ entry index
| Type | Id | Code entry | When used |
|---|---|---|---|
| [Flow/Component/Job/MQ/Cache] | [flow_code/topic/key/id] | [class/method/config] | [when it applies] |

## §6 Core business rules and hidden constraints
- 【Forbidden】[practice] -> must [correct practice] (reason: [why])
- 【Hidden dependency】before [A] must first [B], else [consequence]
- 【Disambiguation】[concept A] vs [concept B]: [difference, interchangeable?, wrong-use consequence]
- 【Naming alignment】[canonical] may also appear as [alias] in code/tables/APIs; body text always uses [canonical]; when changing code, locate implementation names via the entry index (write only when aliases would cause misjudgment)
- 【Implicit semantics】[hidden mechanism] automatically runs [real logic] at [trigger entry]; when changing [scenario] also check [config/context/generated code/external contracts], else [AI pitfall consequence]
- 【Low confidence】[inference] (evidence: [code]; pending: [what user must fill])
- 【Ruling】[YYYY-MM-DD] User confirmed overturning [original authoritative conclusion]: [correct conclusion for this product/domain] (reason: [why source is outdated/inapplicable]). Future doc-init/doc-update that reads this must not reverse it unless the user changes their mind again; recommend syncing the source doc (e.g. backend PRD), but this repo must not edit across repos on its own.

**AI pitfall tag rule:** If a hidden-constraint item is a mistake AI would make without reading docs (forgetting context, forgetting versioned updates, wrong field names), prefix with `**AI pitfall**`. That lets later Agents scan for the most dangerous constraints immediately. Items tagged concurrency_patterns, idempotency_patterns, or soft_delete_patterns in depth_scanner.py output should default to AI pitfall tags.

## §7 Common easy-to-miss conditions and validation paths
- After changing [scenario]: run/call [command or API], check [logs/tables/flow records/cache]
- Note: [effect conditions common in this domain but not directly reminded by code]

**Validation paths must not be empty.** If real commands cannot come from runtime validation, at least generate template validation paths from code scan:

- DB validation (persistence scenarios): `SELECT <key_fields> FROM <main_table> WHERE <condition> -- confirm <field> changed to expected value`
- Log validation (logging scenarios): `grep '<keyword|exception class>' <log_path> | tail -5`
- API validation (HTTP scenarios): `curl -s -X POST http://127.0.0.1:<port>/<path> -H 'Content-Type: application/json' -d '<minimal body>'`
- Cache/state refresh (caching scenarios): `curl -s -X POST http://127.0.0.1:<port>/<refresh_path>`
- Compile validation (compiled languages): `<build_command> && echo "build ok"`
- Unit-test validation (when tests exist): `<test_command> -t <TestClass>#<testMethod>`

Replace `<placeholder>` with this domain’s real entries. Low-confidence validation paths note “pending runtime validation”.

## §8 Related docs
- [GUIDE doc]: covers [shared/specialized mechanism] details; read together when that mechanism is involved
- [Other domain KB]: read together for [cross-domain scenarios]

## §9 Coverage and to-be-filled items
- Code-inference coverage: [entities/status/entries/tables/flows coverage]
- Domain-language unification: [canonical confirmed?; aliases / conflicting names still pending]
- User / materials: [requirements, API docs, test cases, log entry points, veteran experience]
- Multi-source evidence enrichment: [tests/API contracts/frontend/config/migrations/logs/external contracts/permission dicts/generated metadata/runtime evidence actually read; only list evidence that truly reinforced this domain]
- Q&A supplements: [N hidden constraints / M disambiguations / K validation paths]
- To be filled: [business experience neither code nor current Q&A covers; unread test assertions, unverified runtime SQL, unconfirmed frontend menu names, unconnected config center, and other high-value gaps]

<!-- Generated by doc-init on YYYY-MM-DD; positioning: quick reference before AI changes this business domain -->
```

Do not fabricate historical incidents or real pitfalls. If the user volunteers past issues in Q&A, you may write “common easy-to-miss conditions” or “pending doc-update persistence”; without evidence, mark low confidence or to be filled.

Immediately after generating a doc, add a nav entry in root `AGENTS.md`. The nav section should declare the trigger pattern once in the header or group title (e.g. “Read the following docs first when developing, reviewing, or troubleshooting the matching domain”), and each item only lists that doc’s **business-scope keywords**—do not repeat “must read before…”. Agents route by keywords without drowning in repeated formulas.

Good (header declares the shared trigger; each item only has distinguishing info):
```md
> Read the following docs first when developing, reviewing, or troubleshooting the matching domain.

- `docs/CUSTOMER_KB.md`: customer profile changes, status transitions, batch tags, customer query semantics
- `docs/TIER_KB.md`: tier system, upgrade/downgrade rules, retention expiry, tier validity calculation
- `docs/VERSION_MANAGEMENT.md`: sub-config CRUD, DRAFT/RELEASE lifecycle, "opens as draft" issue
```

Bad: “explains customer-module business logic” (content dump, no trigger signals); every item writes “must read before changing, reviewing, or troubleshooting X” (shared factor not extracted—pure noise).

Prefer `scripts/upsert_agents_nav.py` for nav writes to avoid duplicates and format drift:

```bash
python3 <DOC_INIT_DIR>/scripts/upsert_agents_nav.py --root . --path docs/<DOMAIN>_KNOWLEDGE_BASE.md --when-to-read "<when to read>"
```

## Guide template

When a cross-domain shared mechanism or complex specialized mechanism is identified, generate `docs/<TOPIC>_GUIDE.md`. Guides extract complex mechanisms only—they do not replace domain KBs; related domain KBs must keep this domain’s entries and usage.

Granularity judgment before generating:

- If the mechanism affects multiple business domains and AI needs an independent runtime pipeline / real-effect model before changing code → Guide.
- If it only serves one business domain → write into that domain KB’s “Core business rules and hidden constraints”.
- If multiple hidden points belong to one pipeline → merge into one Guide; do not split by annotation, field, hook, or single config key into many tiny docs.
- Historical accidents or one-off failures → do not generate during doc-init.

```markdown
# [Mechanism] Guide

## Document positioning
[Mechanism boundaries this Guide covers, applicable modules/domains, main entries, and what it does not cover. Do not repeat root AGENTS.md “when to read” routing sentences.]

## Mechanism positioning
[What problem it solves; which business domains depend on it]

## Core entries
| Scenario | Entry | Code/config | Notes |
|---|---|---|---|

## Usage constraints
- 【Must】[mechanism rules that must be followed]
- 【Forbidden】[approaches that look reasonable but are not allowed in this project]
- 【Hidden dependency】[actions that must sync before/after using the mechanism]

## Domain references
- [DOMAIN_A_KNOWLEDGE_BASE.md]: [how this domain uses the mechanism]
- [DOMAIN_B_KNOWLEDGE_BASE.md]: [how this domain uses the mechanism]

## To be filled
- [Content code cannot reconstruct; needs user or later doc-update]
```

After generating a Guide, sync the “Related docs” sections of related domain KBs, and add task-triggered nav in root `AGENTS.md`.

Guide root nav also uses `scripts/upsert_agents_nav.py`.

## Root AGENTS.md

Prefer creating/updating the root `AGENTS.md` frame first, then generating `docs/`; after each long-lived doc, immediately write nav so a mid-run failure does not leave orphan docs undiscoverable from the root entry.

Root `AGENTS.md` includes:

- Project intro: 2–3 sentences—what it is, whom it serves, core tech traits.
- Coding conventions: framework choices, must/forbidden coding patterns.
- Validation: how to start, how to validate typical changes.
- Doc navigation: route to domain KBs and Guides by task trigger.

### Ops cheat sheet (runnable projects only)

When `depth_scanner.py` `runnable_project.type` is not `library`/`cli`/`unknown`, generate this section in root AGENTS.md:

```markdown
## Ops cheat sheet

| Service | Port | Start command | Log path |
|------|------|---------|---------|
| [fill from depth_scanner output] | | | |

### Build commands
- [derive from inventory build_system]

### Common compile issues
- [extract from Git fix/revert history and code scan; may start empty]
```

Pure library/SDK/CLI tool projects skip this section; put “how to validate” into root AGENTS.md project behavior rules or the relevant Guide.

Project-root `AGENTS.md` must not reference user-level or global instruction files, e.g. do not write `@~/.claude/CLAUDE.md`. Global rules are loaded by the client automatically; project-root `AGENTS.md` only carries this project’s rules, validation methods, and doc nav.

Nav rules:

- Domain KBs first: cluster by business module / domain / line; high-frequency domains earlier.
- Shared Guides next: flow orchestration, sharding routing, permissions, plugin components, ops validation, and other horizontal mechanisms after domain KBs.
- Each item only business-scope keywords (e.g. “payment callbacks, refunds, reconciliation”); declare the shared trigger pattern once in the section header.
- Do not flatten by tech resource: do not make tables/classes/APIs the main root-nav structure; those indexes live in the corresponding domain KB.

After generate/update, run:

```bash
python3 <DOC_INIT_DIR>/scripts/doc_nav_lint.py --root .
```

Fix errors before finishing; for warnings, either fix or explain in self-assessment why they are temporarily accepted.

## Root CLAUDE.md

Write or normalize to a single line:

```markdown
@AGENTS.md
```

`CLAUDE.md` is only Claude Code’s pointer into project-root `AGENTS.md`—no project rules, doc nav, or global rules.

## .gitignore

Check for `DRAFT_*.md` and `*-draft.md`; if missing, suggest adding them.

---

## Deep-write standards

### Deep-write rounds (required for every domain KB)

Each domain KB is not “scan once, write once”—complete at least 2 rounds (core domains mandatory 3):

**Round 1 — Vertical trace:** From “user trigger entry” (Controller/API/CLI) along the call chain to “data persistence” (Repository/Mapper/table); record key class names, method signatures, and status-transition logic at each layer. Do not stop across modules. **Also record each layer’s full physical path** (from project root, no ellipsis); after the round, summarize into §2.5.

**Round 2 — Horizontal scan:** In already-traced entries, find concurrency control (@Version/locks/CAS), idempotency (unique keys/dedupe), event publish (Event/MQ), cron triggers, exception fallback strategies—write each into §6. If §6 has fewer than 3 items, keep scanning.

**Round 3 (mandatory for core; optional for standard):**
1. **Entity field semantics scan:** Open main entity classes; per field check: whether NULL has special business meaning, whether same-named fields differ across tables, whether FK targets disagree with naming hints, implicit framework fields like `version`/`biz_status`.
2. **JSON/DSL field format extraction:** If depth_scanner `json_field_patterns` hits this domain, trace deserialize DTOs and extract format rules into §6.
3. **Complete table/field index:** Core-domain §4 must list key fields of the main table and key related tables (PK, status, shard keys, FKs, money/balance, time fields) with types and business meaning.

**After Round 2 (mandatory for core):** From Round 1’s layered structure, draw §1.5 mermaid diagrams. Pick the best type from the diagram selection guide; use real class names—no abstract placeholders.

**§2.5 physical-path data source:** Prefer directories from `depth_scanner.py` `framework_components[].file_path` and `entity_fields[].file_path`; dedupe and fill the §2.5 table. Sub-agents need not re-walk the tree—the scanner already did.

**Forbidden:** using only a sub-agent’s module-level summary as generation basis—sub-agent scan is “candidate discovery”; deep-write must return to code to verify key assertions.

**Anchoring rule (hard):** When citing code locations, **do not use line numbers** (e.g. “line 535”, “Line 42”); use `ClassName.methodName()` or `ClassName.methodName() → CalledMethod()`. Method names are stable; line numbers drift and invalidate docs.

**Line-number replacement ops guide** (for doc-compact): when seeing line-number citations, Read that file at the line to confirm the current method name, then replace with `ClassName.methodName()`. Do not guess.

**Line-count reference per KB:** core domains ≥ 300 lines (including tables and code blocks); standard ≥ 150. Below that watermark means thin §3 entries, insufficient §6 hidden constraints, or missing §7 validation paths—backfill against quality gates.

### Deep-write quality gates (self-check immediately after each KB)

| section | Minimum | If unmet |
|---------|---------|---------|
| §2 Core flows/state machines | At least one state diagram or core-flow description | Supplement from `status_patterns`; pure CRUD domains use request-handling flow instead |
| §3 Code entry index | ≥ 3 entries (Controller/Service/Handler/CLI command) | Supplement from `framework_components` |
| §4 Table/field entries | Core: key fields of main + related tables (type+meaning); standard: at least main table and shard key/PK | Supplement from `entity_fields` + db_miner catalog |
| §6 Hidden constraints | ≥ 3 items, ≥ 1 tagged **AI pitfall** | Supplement from `concurrency_patterns`/`idempotency_patterns`/`soft_delete_patterns` |
| §7 Validation paths | Must not be empty | At least template-level paths (see validation path patterns above) |
| §0 Contents | Mandatory for all KBs (10-row § table) | Copy from template; adjust to sections actually generated |
| §1.5 Architecture overview | Core: ≥ 1 mermaid diagram (type by domain trait); standard: optional | Draw from Round 1 trace using the diagram selection guide |
| §2.5 Physical path cheat sheet | Core: ≥ 4 directory rows; standard: ≥ 2 | Summarize full physical paths recorded in Round 1 vertical trace |

**Extra for core domains** (Git hotspots + user-named): §6 ≥ 5 items (≥ 2 from Round 3 field-semantics scan), §7 ≥ 2 executable commands, §4 must include a key-field semantics table.
