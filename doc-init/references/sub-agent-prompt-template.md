# Sub-agent Deep-Write Prompt Template

This document defines the prompt structure and input contract when the main Agent dispatches sub-agents for deep-write. Deep-write quality is capped by prompt quality from the main Agent—not by sub-agent capability. More structured information and concrete signals mean less re-exploration and deeper output.

---

## Core principles

1. **No re-exploration:** The main Agent finished project-level scanning in Step 8 (inventory + depth_scanner + git_history + DB catalog). Sub-agents must not re-grep known entries. The prompt must pass known signals directly; sub-agents only do **confirming reads** (verify signals are real) and **incremental discovery** (details the main Agent missed).
2. **Input determines depth:** Sub-agent output depth ≈ number of concrete signals in the prompt. “Deep-write the payment domain” yields skeleton docs; five status enums + three concurrency patterns + entry file lists yield usable docs.
3. **Constraints determine consistency:** When multiple sub-agents run in parallel, canonical terms, filename conventions, and quality-gate standards must be issued uniformly in the prompt—or each will diverge.

---

## Prompt structure template

Organize the sub-agent prompt as follows (in order; every item must exist or be explicitly marked “none”):

### 1. Task definition

```
You are a doc-init deep-write Worker. Your task is to produce a complete domain knowledge-base document for the「{domain name}」business domain.

Output file: `docs/{DOMAIN}_KNOWLEDGE_BASE.md`
Template: follow the doc-init KB template (§1–§9); no section may be empty.
```

### 2. Domain business scope

```
Business scope: {one-sentence definition}
Includes: {list of covered capabilities}
Excludes: {explicitly excluded capabilities}
```

**Why “Excludes” matters:** With parallel domains, unclear boundaries cause two sub-agents to duplicate content or both miss pieces.

### 3. Known entry inventory

File paths already determined by the main Agent from Step 8 inventory + manual exploration:

```
Known entries (do not re-search; read to confirm):

Controller:
- {absolute file path} — {responsibility}
- ...

Service/core classes:
- {file path} — {responsibility}
- ...

Entity/Model:
- {file path} — {main table name}
- ...

Repository/Mapper:
- {file path}
- ...
```

### 4. Depth Scanner signals

Signals filtered by domain from `.doc-init-depth-scan.json`:

```
Identified signals (read code to confirm; then write into the matching section):

Status enums (→ §2):
- {enum class path}: {summary of enum values}

Concurrency control (→ §6 AI pitfalls):
- {file:line}: {pattern description, e.g. "@Version optimistic lock"}

Idempotency (→ §6):
- {file:line}: {idempotency key source description}

Events/MQ (→ §5):
- {publisher file} → {topic/event} → {consumer file}

JSON fields (→ §6 format rules):
- {entity.field}: deserialize target {DTO class}

Hot files (→ §7 annotation):
- {file path}: {recent N changes concentrated here}
```

**Handling rule:** Signals are candidates, not conclusions. After confirming in code, write into body text; if false positive, discard and explain in §9.

### 5. Canonical-term table

```
Domain language (body text must use canonical terms; implementation names only in parentheses at first appearance and in entry indexes):

| Business concept | Canonical term | Implementation aliases (code/table/API) |
|---------|--------|------------------------|
| {concept} | {canonical} | {class, table, field} |
```

### 6. User Q&A results (if any)

```
User supplements (high weight; trust directly):
- {Q&A pairs}
- ...

If no user Q&A, mark in §9: “Missing user experience input”.
```

### 7. Known interfaces of related domains

```
Related-domain info (write into §8 related docs + §6 cross-domain constraints):
- {Domain A} interacts with this domain via {API/MQ/event}: {interaction description}
- Shared Guide candidates: {mechanism name} — {list of involved domains}
```

### 8. Quality gates

```
Quality floor (must backfill if unmet; do not ship as “to be filled”):

- §2 Core flows/state machines: real enum values (code + meaning) + state-transition diagram (ASCII or list)
- §3 Code entry index: precise to filenames (not package names only); at least Controller + core Service + Repository
- §4 Table/field entries: main table must list fields one by one (type + business meaning + change notes)
- §6 Hidden constraints: at least 5 items, each with code evidence (filename:line or snippet); AI pitfalls must be tagged
- §7 Validation paths: at least 3 executable validation commands (SQL/curl/grep) with real table names / API paths / field names
```

### 9. Constraints and forbidden behavior

```
Hard constraints:
- Create/modify only `docs/{DOMAIN}_KNOWLEDGE_BASE.md`
- Do not modify AGENTS.md, other domains’ KBs, or shared Guides
- Code paths must be precise to filenames—not package or directory only
- Hidden constraints must cite line numbers or snippets—not “inferred”
- Do not fabricate pitfalls or production incidents
- Comment/log language follows the global AGENTS “Coding” section; this template does not set a separate language default
```

---

## Example: main Agent assembling the prompt (pseudocode)

```
For each deep-write domain D:
  1. Extract D’s business scope and entry inventory from the knowledge-boundary report
  2. filter(domain == D) from .doc-init-depth-scan.json → signal list
  3. Take D’s canonical-term table from Step 8 domain-language normalization
  4. Take Q&A pairs related to D from Step 9
  5. Extract interfaces that interact with D from other domains’ boundary reports
  6. Assemble the full prompt from the template above
  7. Dispatch sub-agent(prompt, model="sonnet")
```

---

## Deep-write rounds (inside each sub-agent)

Each sub-agent deep-write has 3 rounds:

| Round | Goal | Behavior |
|------|------|------|
| 1 | Skeleton | From entry inventory and signals in the prompt, read code and build §1–§5 skeleton |
| 2 | Depth | Trace §2 transition preconditions, code evidence for §6 hidden constraints, full §5 event chains |
| 3 | Gate self-check | Check quality gates item by item; backfill unmet ones; then output the final file |

---

## Output acceptance

After a sub-agent finishes, the main Agent should check:

| Check | If failed |
|--------|-------------|
| §2 has real enum values | Main Agent supplements (grep enum classes) |
| §6 ≥ 5 items with code evidence | Send back to sub-agent or main Agent supplements |
| §7 non-empty with real paths | Main Agent derives from Controller paths |
| Filenames / canonical terms aligned with other domains | Main Agent unifies |
| No cross-domain content intrusion | Main Agent removes out-of-scope content |
