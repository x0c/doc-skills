---
name: doc-init
description: Initialize a project documentation system. First check and repair the "Project Documentation Management" standard in global AI instruction files, then build an AI-coding-agent-ready domain knowledge network via collaborative Intake, business-domain scanning, hidden-mechanism discovery, optional database evidence mining, and necessary runtime validation. Use when entering a project with no doc structure, or when the global AGENTS.md lacks the doc-governance standard.
---

# Documentation system init (doc-init)

This skill runs in two phases: **repair the global standard first, then initialize the project's docs**.

**Document language:** When writing project docs, follow the project's existing documentation language and the user's language; if neither is clear, default to English.

**Scope reminder:** the block `insert_doc_governance.py` injects covers **documentation structure only**. Language, memory, and review rules belong to the **non-managed** sections of the global AGENTS file (see `docs/SKILLS_GUIDE.md`); never move them back into the injectable STANDARD.

`<DOC_INIT_DIR>` = directory containing this `SKILL.md` (resolve dynamically; do not hard-code absolute paths).

**Literal detection keys:** a few strings written into a project's root `AGENTS.md` are parsed by the scripts in this skill (and protected by `doc-compact`): the section headings `## 领域地图（doc-init）` (domain map), `## 待补充知识库（doc-init backlog）` (pending knowledge bases), `## 文档导航` (documentation navigation), the `覆盖度复核基线` (coverage-review baseline) stamp, and that map table's two column titles. Reproduce them **verbatim**, including full-width parentheses, whatever language the project's docs are written in—translating them silently breaks the coverage gate and the lint checks. Everything else (domain names, anchors, trigger phrases, body text) follows the project's documentation language.

---

## Built-in scripts cheat sheet

Prefer built-in scripts for mechanical work; keep model context for business judgment:

| Script | Purpose |
|------|------|
| `scripts/project_inventory.py` | Scan language stack, build files, submodules, docs, configs, entry candidates; emits candidate facts only—does not decide business domains |
| `scripts/doc_coverage.py` | Coverage gate: code function entries vs map-anchor match + fingerprint baseline; exit codes `COMPLETE(0)/STALE(2)/NEEDS_INIT(3)` |
| `scripts/upsert_agents_nav.py` | Idempotent add/update of root `AGENTS.md` doc-nav entries |
| `scripts/doc_nav_lint.py` | Check root `AGENTS.md`, `CLAUDE.md`, `docs/` nav consistency |
| `scripts/db_miner.py` | Database catalog and domain-level table/field evidence mining |
| `scripts/git_history_miner.py` | Light Git-history weak-signal mining (hotspots, historical names, Q&A clues) |
| `scripts/depth_scanner.py` | Deep knowledge extraction: state machines, concurrency, idempotency, events, entity fields, etc. |
| `scripts/insert_doc_governance.py` | Version detect + auto insert/upgrade of the "Project Documentation Management" section in global AI instruction files |

Script output is evidence and guardrails—it does not replace model judgment on business boundaries, canonical terms, KB/Guide granularity, or what to persist.

---

## Phase 1: Validate and repair global AI instruction files

### Step 1 — Locate the real global AI instruction files

Probe the following; if symlinks, follow to the real path (`readlink -f`), dedupe real paths, then process that list:

1. `~/.claude/CLAUDE.md`
2. `~/.codex/AGENTS.md`
3. `~/.codex/instructions.md`
4. `~/.config/opencode/AGENTS.md`

If none exist, report and ask the user for paths, then continue.

**Forbidden:** passing the current project's `AGENTS.md` to `insert_doc_governance.py`—only the global files listed above.

### Step 2 — Script validate and auto insert/upgrade

For each real file:

```bash
python3 <DOC_INIT_DIR>/scripts/insert_doc_governance.py "<real path>"
```

| Output prefix | Meaning | Next action |
|----------|------|----------|
| `[skip]` | Already latest | Go to Step 3 |
| `[added]` / `[done]` | First insert succeeded | Go to Step 3 |
| `[upgrade]` / `[done]` | Old version replaced | Clean scattered old rules, then Step 3 |

**Only on `[upgrade]` does the model need extra cleanup** (scan and delete; match literal headings that may still be Chinese in older deployments):

- Entire `## AGENTS.md 优先级` / `## AGENTS.md priority` section
- Under `知识持久化` / `Knowledge persistence`, the `### 检索在先、存储在后` / `### Retrieve first, store later` subsection
- Other scattered paragraphs themed around doc placement, doc index, AGENTS.md navigation, or the docs/ directory

Keep: the rest of the knowledge-persistence section (rules that disable memory) and all non-doc-related sections.

### Step 3 — Phase 1 report

State which files were processed, each script’s output, and which scattered old content was cleaned (if any).

---

## Phase 2: Initialize the current project’s documentation system

**Before Phase 2 starts, read** `references/knowledge-network-design.md` and use it to control doc granularity, naming, KB/Guide boundaries, and budget-limited behavior.

### Step 6 — Decide: init / continue / review

The sole completion anchor is the root `AGENTS.md` section `## 领域地图（doc-init）` (domain map; literal detection key):

1. **Map section present** → read it, enter Step 6.5 coverage review; **forbidden** to exit just because “already exists / all Generated / no backlog.”
2. **Map section absent** → whether or not `docs/` is non-empty, treat as **init incomplete**, enter Step 7/8; when building the map, reuse existing docs—do not rewrite.

If root already has `AGENTS.md`, you may run an auxiliary check (reference only):

```bash
python3 <DOC_INIT_DIR>/scripts/doc_nav_lint.py --root .
```

### Step 6.5 — Coverage review (mandatory when map exists)

Whether to finish is decided by `doc_coverage.py` exit codes—models must not self-claim “coverage is roughly fine”:

```bash
python3 <DOC_INIT_DIR>/scripts/project_inventory.py --root . --output .doc-init-project-inventory.json
python3 <DOC_INIT_DIR>/scripts/doc_coverage.py --root . --inventory .doc-init-project-inventory.json
```

| Exit code | Meaning | Action |
|--------|------|------|
| `3 NEEDS_INIT` | No real map section | Back to Step 6 judgment 2; full init |
| `0 COMPLETE` | Anchor coverage OK, no significant growth | Write the script-suggested baseline stamp back into the map section; tell the user “docs cover current code; use doc-update for incremental fills” and exit |
| `2 STALE` | Under-covered / new function areas / large code growth / no baseline stamp | **Not complete**; enter follow-up below |

**After STALE** (details in `references/scan-and-boundary-report.md` “Coverage review”):

1. Uncovered function areas → filter via product north star (Step 7a): real features join the map; dead code / implementation drift → pending discoveries.
2. Large code growth / no baseline stamp → drift spot-check on `Generated` domains; clear drift demotes to `Deep-write this session`; minor diffs → doc-update.
3. Return to Step 7a → Step 8/9 deep-write this batch; do not re-scan `Generated` domains confirmed still accurate.

Default thresholds: `--min-coverage 0.85`, `--max-uncovered-area-entries 3`, `--max-growth-pct 0.25`. When entry-sparse pure libraries/scaffolding are judged STALE, manually read the uncovered list to confirm—do not lower thresholds to bypass the gate.

### Step 7 — Product north star first + collaborative Intake

Read `references/human-intake.md`.

**Step 7a: Establish product north star first**—follow `human-intake.md` “Product north star first” (① project AGENTS.md product pointers → ② PRD/roadmap → ③ ask the user → ④ hard stop).

**After confirming truth, fix conflicting docs in-place:** if truth established at any stage conflicts with existing `docs/`, correct them in the same session—do not leave two contradictory conclusions. Adjudication, anti-thrashing, and propagation: `references/conflict-resolution.md`.

**Step 7b: Collaborative Intake.** Unless the user explicitly forbids questions, do light Intake (material entry points, business naming, runtime validation entry points, veteran experience). If questions are forbidden, skip and mark “Missing user experience input” in self-assessment.

**Step 7c: Cross-project tech-standard reference check.** Read the real global AI instruction files (located in Step 1) for a declared location of “cross-project tech standard docs” (a public standards directory organized by language/stack; location and directory name vary by user—do not assume a fixed path; if undeclared, skip this step and do not invent paths). When declared:

1. Under the declared location, find matching standard docs for this project’s primary language/stack.
2. If found and project-root `AGENTS.md` does not yet reference them → add a reference near the top (after product intro, before body sections), matching the usage style already used at the declared location (e.g. `Shared engineering standards: [Go standards](<relative path>/go.md)`), adjusting relative paths to this project’s directory depth.
3. If the project spans multiple stacks (e.g. backend + mobile) → one link per matched standard doc, separated by `·` on the same line.

### Step 8 — Scan the project and output the full domain map + knowledge-boundary report

Read `references/scan-and-boundary-report.md`.

**Deliverable order: product north-star summary → complete domain map → per-domain detailed reports.**

**Before building the map, inventory existing docs:** cross-check `docs/` and existing root `AGENTS.md` nav; domains already covered mark “Generated (reuse existing)”—do not rewrite; update only when content is clearly stale or conflicts with current code/product truth.

**Hard constraints on domain partitioning** (see `references/knowledge-network-design.md` “Business domain ≠ code module”):

- Domain = business concept, not submodule/directory name
- One KB covers that business domain’s entries across modules (config/execution/entity/API)
- When one module holds multiple independent business objects, split into separate KBs

**Scripts (in order):**

```bash
# At Step 8 start, run in parallel
python3 <DOC_INIT_DIR>/scripts/project_inventory.py --root . --output .doc-init-project-inventory.json
python3 <DOC_INIT_DIR>/scripts/git_history_miner.py --root . --output .doc-init-git-history.json

# After inventory completes
python3 <DOC_INIT_DIR>/scripts/depth_scanner.py --root . --inventory .doc-init-project-inventory.json --output .doc-init-depth-scan.json
```

Read `references/depth-patterns.md` and turn depth_scanner mechanical signals into per-domain knowledge candidates (see that file’s signal→KB section mapping). Discard false positives—do not copy mechanically.

If the environment supports parallelism and the user has not restricted it, **explore in parallel aggressively**: candidate-domain code-entry exploration can run concurrently; assign each sub-agent boundaries by business domain (not by module).

After identifying the language stack, read matching docs under `references/hidden-semantics/` as needed (language list in `references/scan-and-boundary-report.md` “Language stacks and hidden semantics”).

Read `references/multi-source-evidence.md` and, with inventory `evidence_sources`, do light multi-source discovery; deep digs center on candidate business domains—not a full deep dig in this step.

### Step 8.5 — Database evidence mining (optional enrichment)

If the project has DB config, or candidate domains clearly depend on DB facts (status, money, balances, sharding, flows, dicts, etc.), read `references/database-mining/workflow.md` and use `scripts/db_miner.py` for a light catalog.

This stage only: table list, field list, PK/indexes and comments—no full-DB count/distinct/profile/sample-table. Afterward you may call `db_miner.py summarize-catalog` for a directory-level summary (local JSON only; no DB connection).

If connection is missing or the user forbids it, mark “Missing real data semantics” in the knowledge-boundary report and self-assessment.

### Step 8.7 — Domain-map confirmation and deep-write priority negotiation (interaction gate)

**Unless the user explicitly forbids questions**, after the knowledge-boundary report and before Step 9, confirm the domain map with the user. **Prefer the environment’s built-in choice tool** (e.g. `AskUserQuestion`); fall back to open text questions only when needed.

**Stepwise choices:**

**Step 1: Show the whole domain map at once, then confirm the boundaries**

First print the full domain map in plain text, short enough to read on one screen, grouped in three segments: `Covered by existing docs (A)` → `Deep-write this session (M, with reasons)` → `Backlog (K, with anchors)`.

Then ask with a structured choice tool:

| Question | Options |
|------|------|
| Does domain partitioning need adjustment? | ① Partitioning looks good, continue (recommended) / ② Need to split a domain / ③ Need to merge domains / ④ Need to delete a domain (abandoned code) |

**Step 2: Confirm deep-write priority** (only after Step 1 chose “partitioning looks good”)

| Question | Options |
|------|------|
| Does deep-write priority need adjustment? | ① Current order is fine (recommended) / ② I often change a certain area lately—move it up / ③ Something in backlog should be deep-written earlier |

**Design principles:**

- Put the recommended option first and label it “recommended”; in most cases the user confirms and proceeds
- No thrashing across steps: if Step 1 needs boundary changes, after adjusting go straight to Step 9—do not ask Step 2 (changed boundaries imply priority must be re-ranked anyway)

**Behavior after user choice:**

| User choice | Behavior |
|---------|------|
| Both steps choose recommended | Enter Step 9 with current map and priority |
| Ask to split/merge/delete | Adjust map, **no second confirmation**, enter Step 9 |
| Adjust priority | Reorder as specified, enter Step 9 |
| Tool unsupported / timeout / no reply | Continue with model judgment |

**Forbidden anti-patterns:** asking “is this KB correct?” after every KB; asking “is this important?” after every pattern found; “I’m about to scan—confirm?”; second-guessing “are you sure?” after the user already confirmed.

### Step 9 — Targeted Q&A and doc generation

Read precise Q&A rules in `references/human-intake.md`; read `references/document-templates.md`.

**Timing constraints (strict order):**

1. **Q&A before sub-agent dispatch:** The main Agent does one concentrated Q&A round for all domains in this deep-write main batch (unless the user forbids questions). Focus on what code cannot see but that affects whether AI can change code correctly (business peaks, which channels fail most, approval flows, historical conventions).
2. **Prompt assembly:** Read `references/sub-agent-prompt-template.md`; for each deep-write domain assemble a structured prompt (domain definition + entry inventory + depth_scanner signals + canonical terms + Q&A results + quality gates). **Forbidden:** giving sub-agents only a vague “deep-write domain X”—vague prompts yield skeleton docs; structured prompts yield usable docs.
3. **Dispatch sub-agents** (if supported and main batch ≥ 2 domains): weakly coupled domains may run in parallel; if domain A depends on domain B’s shared mechanism, serialize.
4. **Aggregation** (main Agent must run after all sub-agents return):
   - Shared-mechanism extraction check: same mechanism described in ≥ 2 KBs → decide whether to extract a `*_GUIDE.md`
   - Cross-reference alignment: each KB §8 references cross-domain relations
   - Canonical-term consistency: same concept uses the same canonical term across KBs
   - Ops cheat-sheet merge: multi-host module projects enumerate ports one by one

**Forbidden during parallelism:** sub-agents must not modify root `AGENTS.md`, other domains’ KBs, or shared Guides—the main Agent does those in aggregation.

**Generate docs** (per domain in this deep-write main batch):

- `docs/<DOMAIN>_KNOWLEDGE_BASE.md` (DOMAIN must be a business concept name—not a module name)
- `docs/<TOPIC>_GUIDE.md` (only extract shared horizontal mechanisms; threshold in `knowledge-network-design.md`)
- Project-root `AGENTS.md`
- Project-root `CLAUDE.md` (single line `@AGENTS.md` only)

**Deep-write standards and quality gates:** `references/document-templates.md` “Deep-write standards”; after each KB, immediately self-check against quality gates and backfill if unmet.

**Write root `AGENTS.md` nav** (immediately after each doc):

```bash
python3 <DOC_INIT_DIR>/scripts/upsert_agents_nav.py --root . --path docs/<DOMAIN>_KNOWLEDGE_BASE.md --when-to-read "<task trigger phrase>"
```

`--when-to-read` only lists business-scope keywords covered by that doc (e.g. “customer profile changes, status transitions, batch tags”)—do not repeat “must read before changing, reviewing, or troubleshooting…” on every line; declare the shared trigger pattern once in the nav section header.

**Register backlog** (after the main batch, register all pending domains—never silently drop):

```bash
python3 <DOC_INIT_DIR>/scripts/upsert_agents_nav.py \
  --root . --backlog \
  --name "<domain> KB" \
  --anchor "<entry dir>" \
  --when-to-read "<trigger scenario>"
```

**Persist the domain map** (**mandatory**, even when this session fully covered everything):

Write the complete domain map into root `AGENTS.md` `## 领域地图（doc-init）`. This section **only serves the `doc_coverage.py` coverage gate**—do not duplicate paths and trigger phrases already in doc nav.

Format: baseline stamp + two-column table (domain | entry anchors); **forbidden** process-metadata columns like “Status” or “Notes”—“Generated / Deep-write this session / To be filled” has no value for later work models; doc paths are already registered in doc nav.

The heading, the baseline-stamp comment, and the two column titles are literal detection keys (see “Literal detection keys” above): copy them exactly as shown. Domain names and anchors are free text in the project’s doc language.

```markdown
## 领域地图（doc-init）

<!-- 覆盖度复核基线：2026-06-21 · 源码指纹 扫描 1573 文件 / Go 412 · TS 88 / 11 子模块 · 基线提交 a1b2c3d -->

| 领域 | 入口锚点 |
|------|---------|
| Channel system | src/channels/ |
| Agent execution loop | src/agents/ |
| Plugin system | src/plugins/ |
```

Simplest way to get the stamp right: `doc_coverage.py` prints a ready-to-paste `suggested_stamp` for the current tree—copy that line instead of hand-writing it. Its values come from inventory (`scan.scanned_files`, each `languages[].file_count`, `submodules` count) plus `git rev-parse --short HEAD`. Domains registered in the map section must match domains covered by doc nav (the map section does not register backlog—backlog is managed via `upsert_agents_nav.py --backlog`).

**Conditional ops cheat sheet:** If depth_scanner `runnable_project.type` is not `library/cli/unknown`, generate an “Ops cheat sheet” section in root AGENTS.md (format in `document-templates.md`). Multi-host module projects must list every submodule with `spring-boot-maven-plugin`/`mainClass` and its port.

### Step 10 — Runtime validation and conditional Operations generation

Only when the project has local-run value, read `references/operations-validation.md`.

Route runtime-validation evidence by semantics: start commands / health / config / log paths → `OPERATIONS_GUIDE.md`; real business API behavior / state changes / error codes → corresponding domain KB; cross-domain shared mechanisms → `*_GUIDE.md`.

Generation conditions:

- At least one reusable runtime experience or start blocker → create or update `docs/OPERATIONS_GUIDE.md`
- Validation not executed but the project has a runtime surface → only a thin “runtime hypotheses and pending validation list”
- No local runtime surface → do not generate; put validation method in root `AGENTS.md`

### Step 11 — Self-assessment report

First run doc-nav consistency check:

```bash
python3 <DOC_INIT_DIR>/scripts/doc_nav_lint.py --root .
```

Include lint errors/warnings in self-assessment. Fix errors before reporting complete.

**Coverage ledger (must give numbers):**

- Domain-map total N = Generated (reuse) A + Deep-write this session M + Candidate dead code/drift D + backlog B
- Assert: A + M + D + B = N ✓ (if not, silent domain drop—must backfill backlog)
- Assert: root `AGENTS.md` `## 领域地图（doc-init）` is written and matches the ledger ✓
- Assert: map section has a “coverage-review baseline” stamp ✓

**If Step 6.5 ran**, also output the coverage-review ledger (G gaps + R stale needing refresh; only G + R == 0 may be judged truly complete).

Self-assessment must also cover (item by item—not one vague paragraph):

- Per-KB deep-write quality-gate pass/fail (§2/§3/§4/§6/§7 meet minima; if not, reason and remediation)
- depth_scanner signal utilization (how many signals out, how many written into KBs, how many discarded and why)
- Domain-language coverage (canonical terms unified? unresolved homonyms?)
- Git weak-signal coverage (available? hotspots and fix/revert clues only as pending candidates?)
- Database evidence coverage (connected? which domains catalogued? which key tables unanalyzed?)
- Multi-source evidence coverage (which sources available, which dug, which high-value missing)
- High-risk uncovered items (concepts undisambiguated, status flows unclear, mechanism effect conditions unclear, validation paths missing)
- Operations validation coverage (which steps executed; which remain low-confidence hypotheses)
- Follow-up persistence suggestions (what doc-update should fill; what suits doc-compact)

### Step 12 — Deeper-investigation proposals (mandatory; do not skip)

After self-assessment, **must** propose at least 3 directions for further investigation. **Use a structured multi-select tool** (e.g. `AskUserQuestion multiSelect: true`); each option format: `[domain/mechanism] — [current state] — [what can continue]`.

Proposal sources (must be based on this session’s real findings—do not invent):

- Quality-gate items marked “remediate” or “template-level”
- depth_scanner signals “discarded / unconfirmed”
- §6 items marked “low confidence”
- 1–2 backlog domains most tightly coupled to already deep-written domains
- Cross-domain event/MQ linkages not expanded
- §7 validation paths that are only templates, missing real parameters

**After user selection:**

- ≥ 2 independent directions → dispatch sub-agents in parallel; serialize dependent preambles first
- 1 direction → main Agent executes directly
- After each round, propose again (keep using multi-select) until the user stops

**After each deeper round, mandatory updates:** domain-map section status, backlog section, doc nav, plus a 1–2 line incremental summary (e.g. “map 8 domains: deep-written 4 → 5”).
