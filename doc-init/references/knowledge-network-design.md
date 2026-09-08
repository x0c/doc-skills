# Knowledge Network Design

This document defines doc-init Phase 2 documentation organization principles. Read it first when entering project doc initialization; use it to judge doc granularity, naming, KB/Guide boundaries, and how to handle non-business projects.

## Core goal

Docs exist to replace tribal knowledge: externalize business boundaries, code entries, table entries, flow entries, hidden constraints, and validation paths that only veterans know into an AI-readable knowledge network—so AI moves from “generally correct” to “correct for this project.”

Phase 2 is not generating a global resource dictionary, nor mashing every table/class/API into a mega-index. It rebuilds an onboarding map for AI coding agents around real work scenarios.

## Organization principles

1. **Entry is the business scenario, not the code module:** When the user says “change payment channels,” “add a push notification,” or “order timeout bug,” AI should route from root `AGENTS.md` to the matching **business-domain** knowledge base. KB filenames must reflect business concepts (`PAYMENT_KNOWLEDGE_BASE.md`, `ORDER_KNOWLEDGE_BASE.md`). **Forbidden:** naming by code modules (`BACKEND_KB`, `SERVICE_LAYER_KB`, `CORE_MODULE_KB`).
2. Domain knowledge bases are the trunk: each **business domain / business line** gets one `*_KNOWLEDGE_BASE.md` covering that domain’s **full chain** from config through execution—business logic, code entries (across modules), table entries, flow entries, hidden knowledge, and validation paths. One KB should answer “what do I need to know to change this business,” not send AI to another “module KB” for the other half. **Path completeness:** code paths cited in a KB must be relative paths reachable from the project root (no ellipsis shortcuts like `core/.../account/`). After reading the doc, an Agent should be able to glob or ls to the target without a second search.
3. Shared Guides are horizontal mechanisms: only complex mechanisms shared by multiple domains get a separate `*_GUIDE.md`, referenced on demand by related KBs.
4. Docs form a knowledge network: `AGENTS.md` routes; domain KBs reference shared Guides and related domain KBs; Guides state mechanism boundaries and applicable domains.
5. Do not default to global mega-indexes: do not make `TABLE_INDEX.md` / `CODE_INDEX.md` default outputs. Only when the project is too small to split domains, or the user explicitly asks for a global index, simplify to a single KB or add a global index.
6. **Business domain ≠ code module (core hard constraint, bidirectional):** In multi-module projects, the same domain’s code usually **spans multiple submodules** (config / execution / entity / API layers). Identify the business domain first, then gather that domain’s entries across modules into one KB. **Forbidden:** 1:1 docs per submodule—that is a code index, not a business knowledge network. **Symmetric constraint:** when one module contains multiple independent business objects, **you must split into separate KBs**—test: if changing one object needs zero knowledge of the other (independent state machines, table families, API entries), you stuffed multiple domains into one doc and must split. Classic anti-pattern: merging “customer management + points account + tier account” into one “execution-layer KB,” so a developer changing tier upgrades hunts 10 relevant lines in 265.
7. Routing lives only in `AGENTS.md`: root `AGENTS.md` tells Agents which doc to read for which task; docs under `docs/` must not self-navigate with “when to read / must read”—use “document positioning / covers / does not cover” instead.
8. Human collaboration is a core capability: code only provides visible structure; real experience comes from users and runtime practice. User supplements must be sourced and cross-checked with code evidence before persistence.
9. Domain language must be unified: one canonical term per business concept in final docs; code class/enum/table/API field names, DB comments, runtime logs, commit messages, and oral user names are alias evidence—do not switch among many names in body text.
10. **Full domain map first, then batched deep-write:** Step one of doc-init is enumerating all business/functional domains into a complete domain map (anchored on `project_inventory.py` `submodules` + top-level dirs + entry candidates), then labeling each as “deep-write this session” or “to be filled.” Undeepened domains must not be silently dropped—register all of them into the root `AGENTS.md` backlog section.
11. **Product truth precedes code topology:** `project_inventory.py` submodule/dir/entry candidates are mechanical candidates reflecting how code is organized—not that the product truly has the feature. Before finalizing the domain map, validate against the product north star (see `references/human-intake.md` “Product north star first”): candidates with no basis in the product definition and not reachable via nav/routing are dead-code or implementation-drift signals—not new domains. List them as pending discoveries first; do not promote them straight onto the map.

## Domain language unification

Multiple data sources bring multiple names: code, DB comments, requirements, user Q&A, runtime logs, and commit messages may describe the same thing differently. `doc-init` must normalize first, then write; otherwise later Agents get derailed by synonyms.

Normalization principles:

- Do not default to a standalone glossary. Domain KBs should stably use the canonical term like natural docs—not dump dictionaries.
- Prefer as canonical: user-confirmed everyday team names, existing core project docs, stable names in current product/API contracts; when the user explicitly says “everyone on the team calls it this,” that name outranks code class names, DB comments, and commit messages.
- Keep code class names, enum values, table/field names, and API parameter names verbatim as implementation entries or first-appearance parentheticals—do not rewrite implementation names to unify business language.
- DB table/field comments and code comments may be historical or local names—evidence only; if they conflict with user names or core docs, do not promote them to canonical.
- Commit messages are historical human-name evidence: weight below user confirmation and core docs, above pure model guesses; only help discover aliases and follow-ups—never decide the canonical term alone.
- Homonyms, synonyms, parameters reused across scenarios with different meanings, or comments conflicting with real semantics must enter Q&A or low-confidence disambiguation.

Presentation:

- Ordinary aliases: light note at first appearance or in entry indexes, e.g. `loyalty program (code entity: LoyaltyProgram; enum: LOYALTY_PROGRAM; main table: d_oc_l_loyalty_program)`.
- High-risk confusion only: write `【Disambiguation】` entries under “Core business rules and hidden constraints,” e.g. `progId` means different IDs in different flows, two status fields must not be interchanged, etc.
- Do not default a “Glossary” section per KB; only add a short “Concept disambiguation” subsection if the user asks, or a domain has many high-frequency confusions with no other clear home.

## Granularity control

During init, prefer coarse usable docs over splitting every class, table, API, annotation, hook, component, or flow node into its own doc.

- **Doc count scales with real domain count:** as many KBs/Guides as real domains—dozens is normal. “Few and precise” constrains **per-domain single-doc granularity**, not a project-wide total cap.
- Domain KB granularity: by business module / domain / line—not by single Controller, Service, table, enum, component, or API.
- Guide granularity: by “same runtime mechanism / same hidden pipeline / same cross-domain work scenario”—not by single annotation, decorator, AOP pointcut, middleware, or config key.
- Hidden-mechanism merge: when multiple annotations, proxies, hooks, contexts, configs serve one runtime pipeline, merge into one Guide.
- Threshold to split a Guide: affects two+ business domains; needs an independent mental model to change; has a fixed validation path; ignoring it causes silent failure / wrong table / unauthorized access / data inconsistency; putting it in one KB would be duplicated across many KBs. Create a Guide when any one holds.
- Do not split: single-domain impact, or knowledge of one table/API/field/ordinary class—write into the corresponding domain KB.
- Historical incidents and real pitfall ledgers are not fabricated by doc-init; leave them to later `doc-update` or troubleshooting docs.

## Domain-map completeness and to-be-filled backlog

The domain map is Step 8’s **primary deliverable**—produce it before any per-domain boundary report.

**Map format** (table or list, one domain per row):

| Domain | Evidence anchors (dir · entry) | Status | Priority reason / why backlog |
|--------|------------------------|------|--------------------------|
| Channel system | src/channels/ · ChannelHandler | Generated (reuse existing) | CHANNEL_GUIDE.md already covers |
| Agent execution loop | src/agents/ · AgentHarness | Deep-write this session | 20+ channels depend on this core; Git hotspot |
| Plugin system | src/plugins/ · PluginRegistry | To be filled | Architecturally independent; not this session’s user priority |
| Storage/state | src/storage/ · SQLite | To be filled | Depends on understanding core domains first |

**Domain-map rules:**

- Anchor on `project_inventory.py` `submodules` + top-level dirs + `entry_candidates`; decide one by one whether each is an independent domain or a submodule of another.
- Before building the map, cross-check existing `docs/` `*_KNOWLEDGE_BASE.md` / `*_GUIDE.md` and root `AGENTS.md` nav; domains already covered mark “Generated (reuse existing)”—do not regenerate/rewrite unless content is clearly stale or conflicts with code (then update and explain).
- Each domain gets evidence anchors (most important dir or entry symbol); if evidence is thin, mark “pending scan”.
- Status is one of: `Generated (reuse existing)` / `Deep-write this session` / `To be filled`—no “ignore” or “skip”.
- Map total = generated (reuse + this session) + backlog count; Step 11 self-assessment must state these numbers and verify they equal the total.

**Selecting this session’s deep-write batch:**

- Domains on the project’s core runtime path (without them other domains cannot be understood);
- Domains concentrated in Git hotspots (high change frequency = high bug risk);
- Modules the user named in Intake as “most often changed / most error-prone”;
- No fixed upper or lower page count—driven by domain importance.

**Backlog write rules:**

- Use `upsert_agents_nav.py --backlog` to register each to-be-filled domain into root `AGENTS.md` section `## 待补充知识库（doc-init backlog）` (pending knowledge bases; literal detection key created by the script).
- Each item comes out as `- [待补充] <domain> KB/Guide —— 入口锚点：<dir>；触发场景：<before changing/troubleshooting feature X>`; you supply only the domain name, anchor, and trigger.
- On the next doc-init run, Step 6 recognizes the backlog section and continues deep-write—does not retreat to doc-compact.

**The domain-map section is the completion anchor, but not sufficient alone:**

- After the main deep-write batch (even with no backlog / full coverage), persist the full domain map into root `AGENTS.md` `## 领域地图（doc-init）` (domain map; literal detection key), with a leading `覆盖度复核基线` (coverage-review baseline) stamp of the current source fingerprint—this step is mandatory.
- Whether “the project is initialized” may be judged **only** by this map section—**never** by “is `docs/` non-empty,” “how many scattered docs exist,” or “nav entry count.”
- But “map section exists” only proves init once happened—**not** that the map still covers current code. Old maps may be years stale while code doubled and grew new domains. After detecting the map section, must first run `scripts/doc_coverage.py` coverage gate (SKILL.md Step 6.5): mechanically match current code function entries to map anchors + compare source fingerprint baseline; only exit code `COMPLETE` counts as truly done; `STALE` must continue writing or refresh. Completion = map section exists **and** coverage gate passes—both required.
- Scattered existing docs (old doc-init, hand-written, or other tools) ≠ init complete. Without a domain-map section, however many docs sit under `docs/`, treat as “init incomplete” and continue scan/generate (reuse existing docs; do not rewrite).
- `doc_nav_lint.py` orphan-doc warnings, coverage ratios, etc. are reference signals only—not excuses to finish or retreat claiming “coverage is already a reasonable starting point.” Authoritative coverage judgment is `doc_coverage.py` exit codes—not model self-claim.

## File naming

Filenames express “business domain / mechanism entry,” not analysis process or internal implementation details. Avoid overly narrow words like `HIDDEN`, `GUARDS`, `RUNTIME_SEMANTICS`, `ANNOTATION`, `AOP` in filenames; put those details in the body.

Example: LiteFlow component runtime mechanism → `LITEFLOW_COMPONENT_GUIDE.md`, not `LITEFLOW_COMPONENT_HIDDEN_GUARDS_GUIDE.md`.

Only when a tech/framework has one main work entry in the project and no short-term split task surface is visible, use a blanket `<TECH>_GUIDE.md`. If the parent mechanism already has multiple stable work entries, name by task surface, e.g.:

- `LITEFLOW_COMPONENT_GUIDE.md`: before changing components, base classes, or component runtime constraints.
- `LITEFLOW_NODES.md`: before looking up node IDs / inputs / outputs / source paths.
- `BUSINESS_ACTION_GUIDE.md`: before changing business-action enablement checks.

## Depth vs breadth decision tree

doc-init time and token budget are limited. Do not spread effort evenly—invest depth by domain importance:

| Tier | Criteria | Deep-write depth |
|---------|---------|---------|
| Core | Git hotspot Top 5 + user-named + product core loop | Full deep-write: §2–§7 complete; §6 ≥ 5 hidden constraints; §7 must have executable validation commands |
| Standard | Real entries (Controller/Handler/CLI command); changed in daily work | Standard write: §2–§4 + §6 ≥ 3 hidden constraints + §7 at least template-level validation paths |
| Edge | Entries exist but low change frequency, or auxiliary (utils/config/scaffolding) | Register backlog only: entry anchors + one-line product positioning |

**Order:** confirm core domains from `depth_scanner.py` `hot_files` and user Intake first, then split standard vs edge by entry density and framework-component count.

**Budget:** core 60% of deep-write time, standard 30%, edge 10% (register only, no deep-write).

## From skeleton to flesh: progressive deep-write guidance

doc-init output targets a “usable first draft”—enough for an Agent to finish medium-complexity tasks alone. Deep-write quality gates and round rules: `document-templates.md` “Deep-write standards”.

**doc-init vs doc-update split:**

| Content type | doc-init owns | doc-update owns |
|---------|--------------|----------------|
| Code entry index | ✓ initial build | incremental update |
| State machines / core flows | ✓ derive from code | edge cases |
| Hidden constraints | ✓ candidate extraction from patterns | real pitfall experience |
| Validation paths | ✓ template-level | real commands and parameters |
| Troubleshooting records | ✗ do not fabricate | ✓ daily persistence |
| Ops SOP | ✓ skeleton (ports/start/logs) | env differences and known traps |

**§9 confidence levels:**

| Level | Source | Examples |
|------|------|------|
| High | Directly from code/tests/config | Status enum values, schema, API paths |
| Medium | Inferred from code patterns; not runtime-validated | Transition directions, config-effect conditions |
| Low / to be filled | Needs user experience or runtime validation | “Why this field,” exception-handling strategy |

**Never fabricate experience:** mark unseen items “to be filled”; do not invent “common issues.” `depth_scanner.py` patterns are candidate signals only—write into KB body only after the model confirms them.

## Non-business projects

Not every project has “customer / payment / flow” style domains. If the project is essentially a starter, SDK, plugin, framework library, CLI tool, scaffolding, or internal platform component, do not force business-domain KBs.

- Starter / SDK / plugin / framework library: prefer `*_GUIDE.md` organized around “before integrating / before changing the mechanism / before troubleshooting effect”; add `*_KNOWLEDGE_BASE.md` only when there are stable in-repo business example domains.
- CLI / tool projects: split knowledge entries by user workflow or command capability, e.g. `CLI_USAGE_GUIDE.md`, `REPOSITORY_ANALYSIS_GUIDE.md`.
- Code scaffolding / demos: example domains may be KBs but must state they are template examples, not real business domains; template engineering constraints, site structure, generation rules may go into a Guide or conditionally generated `OPERATIONS_GUIDE.md`.

## Non-interactive / budget-limited mode

When the user explicitly says “don’t ask,” “test mode,” “dry run,” “report only,” “don’t write files,” or “limit scanned files / docs / budget,” enter convergent mode and strictly respect those bounds.

**Distinguish two kinds of restraint:**

- **Budget-limited** (user explicitly limits files/docs/time/forbids parallelism): compress **deep-write count** to the user cap; the domain map must still fully enumerate; domains beyond budget go to backlog—never silently drop.
- **Large-project default (user did not limit):** full map + main-batch deep-write + full backlog; do not list fewer domains or backlog less because the project is large.

Other convergent rules:

- If the user forbids modifying global instruction files, Phase 1 only does integrity check and report.
- If the user forbids writing files, only output the knowledge-boundary report (with full domain map) and suggested doc list—do not create `AGENTS.md`, `CLAUDE.md`, or `docs/`.
- If the user limits scanned file count, list candidates and rank by entry value first, then only read within the limit; unread content goes to “uncovered / to be filled.”
- If the user limits doc count, prioritize root `AGENTS.md` and project root `CLAUDE.md`, then the most core KB or Guide; register all remaining candidates into the backlog section (not just a self-assessment mention).
- With cost / token / time budget, do not start uncontrolled full scans; prioritize a complete domain map and knowledge-boundary report, then decide whether to generate docs.
- If the user forbids questions, skip Intake and Q&A; write what code cannot see as “low confidence / to be filled” and list risk gaps in self-assessment.
- If the user forbids questions and multiple business names exist, pick the strongest-evidence canonical term and mark low confidence; do not mix multiple names into body text.
