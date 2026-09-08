# Scan And Boundary Report

This document defines Phase 2 project scanning and the knowledge-boundary report. After Human Intake, read this file, then selectively read language-specific docs under `references/hidden-semantics/` for the project’s languages.

## Contents

- Scan goals
- Project structure scan
- Language stacks and hidden semantics
- Business-domain identification
- Domain language unification
- Multi-source evidence enrichment
- Git history weak signals
- What to collect inside each business domain
- Generic implicit-semantics scan framework
- Knowledge-boundary report template
- Shared Guide candidate template
- Q&A gap identification
- Budget and convergence

## Scan goals

While scanning, prioritize: “Which business modules / domains / lines does this project actually work by?” Do not start by extracting a global tech-resource inventory.

## Project structure scan

- Prefer `scripts/project_inventory.py` for mechanical candidate facts: directory structure, languages, frameworks, build tools, submodules, existing docs, configs, and entry candidates.
- Read the inventory JSON before business judgment; script entry candidates may false-positive or miss—never equate them directly to domain boundaries.
- Existing `*.md` and `README.md`—avoid rebuilding docs that already exist.
- Requirements, API docs, test docs, historical wiki, log/runtime entry points the user provided in Intake.
- If inventory outputs `evidence_sources`, treat it first as a light candidate evidence map—do not deep-dig every candidate immediately.

## Coverage review (continuation / suspected complete)

When root `AGENTS.md` already contains `## 领域地图（doc-init）` (domain map; literal detection key, see SKILL.md), SKILL.md Step 6.5 requires **calibrating the old map against current code before deciding to finish**. A map only reflects the code landscape at generation time; in old projects maps often sit untouched for years while code doubles and grows new domains—yet the old map is treated as “done.” This section closes that blind spot. **Do not exit early because “map exists / all Generated / no backlog.”**

### Mechanical judgment by script (not model self-claim)

Source-fingerprint baseline compare, coverage ratio, and gap detection are done by `scripts/doc_coverage.py`. It reads `project_inventory.py` JSON and the map section, and exits `COMPLETE/STALE/NEEDS_INIT`:

- Prefix-match current `entry_candidates` + `submodules` against map-row entry anchors; compute entry coverage; find **contiguous function areas no anchor lands in** (= domains added after the map or missed at generation).
- Read the map’s “coverage-review baseline” stamp; compare growth in scanned files / submodule count; **no baseline stamp → always STALE**, treat as “possibly severely stale” and do a full review.

Non-`0` exit codes forbid finishing. The script only outputs “which function areas are uncovered”; the model still: (1) judges uncovered areas as real domains vs dead code, and (2) spot-checks drift on already-covered domains.

### Uncovered function areas → product north-star filter

For each uncovered function area listed by the script, filter with this file’s “Business-domain identification” rules: no basis in the product definition and not reachable via nav/routing → dead code / implementation drift → pending discovery, do not promote to a domain; confirmed real features → add as new map rows with status `Deep-write this session` or `To be filled`.

### Drift spot-check on covered domains (find stale docs)

For each `Generated (reuse existing)` domain, sample its KB:

- Do classes/files/tables/flows named in KB “code / table / flow entries” still resolve in current code (symbols/files still present)?
- Has the anchor directory grown many new entries the KB never mentions (new Controllers/Services/Handlers/tables/flow nodes, etc.)?

Judgment:

- Clear mismatch (many dead entries, or contiguous new uncovered entries) → demote that domain from `Generated (reuse existing)` to `Deep-write this session` (refresh), and document drift points in the review report.
- Minor diffs (renamed symbols, a few additions) → do not force refresh; record for incremental `doc-update`.

### Coverage review report (script numbers + model judgment)

```markdown
## Coverage review report

- Source fingerprint: prior baseline [date/fingerprint] → current [fingerprint]; delta: scanned files +N, submodules +M, baseline commit K commits behind HEAD (if no prior baseline, note "full review as possibly severely stale")
- Map registered domains M; current function areas C; covered matches X
- Coverage gaps G:
  - [domain] · anchor [dir] · classification [real feature→deep-write this session/to be filled | candidate dead code/drift→pending confirmation]
- Suspected stale needing refresh R:
  - [domain] · drift [dead entries / contiguous new entries] · disposition [deep-write refresh this session | defer to doc-update]
```

### Branches after review

- **G + R == 0** → truly done: write the updated baseline stamp from the current fingerprint back into the map section; tell the user “docs still cover current code; use doc-compact to tidy, doc-update for incremental fills” and exit.
- **G + R > 0** → not done: add gap domains to the map, demote suspected-stale domains to deep-write this session, return to SKILL.md Step 7a → Step 8/9 for this batch; do not re-scan `Generated` domains confirmed still accurate.

## Language stacks and hidden semantics

Identify language stack and main frameworks from build files, package managers, and source extensions, then read only matching language-specific scan docs:

- Java/Kotlin: `references/hidden-semantics/java-kotlin.md`
- JavaScript/TypeScript: `references/hidden-semantics/javascript-typescript.md`
- Python: `references/hidden-semantics/python.md`
- Go: `references/hidden-semantics/go.md`
- C#/.NET: `references/hidden-semantics/csharp-dotnet.md`

Multi-language projects read multiple references, but final artifacts are still organized by business domain—not by language. For uncovered languages, use the generic implicit-semantics framework and mark “language-specific coverage insufficient” in self-assessment.

If `project_inventory.py` already ran, prefer its `languages` and `recommended_hidden_semantics_refs` to narrow reads; if script results conflict with real project entries, trust source and build-file evidence.

## Business-domain identification

Domain identification happens inside the product north star (product definition already established in `human-intake.md`)—not pure code induction: **product shape—whether this is a real feature—is decided by product docs and user confirmation; code only decides implementation topology (how and where).** After finding candidate boundaries from package/module names, Controllers, Services, Facades, Components, Flows, Jobs, MQ topics, table prefixes, and enum names, check each against the north star:

- Basis in the product definition → list normally on the domain map.
- No basis in the product definition, and the module is not wired into nav/routing / no real reachable callers → mark “candidate dead code / implementation drift” as a pending discovery; **do not create a domain yet**; let the user classify later.
- No basis in the product definition, but it is wired into nav and user/code evidence shows it is in use → possibly stale product docs or internal naming differences; mark “pending confirmation: product docs may be outdated”; you may still create a domain but annotate the conflict.

Output the candidate domain list with evidence per domain.

For multi-module projects, first identify build layers and submodule roles, e.g. `api` / `service` / `domain` / `job` / `flow` / `integration` / `common`. When one business domain spans modules, merge into one domain KB and mark each submodule’s entries inside the doc.

Shared modules (common, framework, starter, plugin, infra, etc.) do not get business KBs by default; if they host complex mechanisms, generate the corresponding `*_GUIDE.md`.

## Domain language unification

Full rules: `knowledge-network-design.md` “Domain language unification”. This section only adds scan-stage output rules:

- Each candidate domain gets a “suggested canonical term” and evidence sources
- Keep code/table/enum/API field names as implementation aliases—do not mix them as body-text canonical terms
- Commit-message names are historical-name evidence, below user confirmation and core docs
- Homonyms, synonyms, cross-scenario parameter meaning differences, or comment vs real-semantics conflicts → “high-risk disambiguation” and enter Q&A
- If you cannot tell whether concepts are the same, do not force-merge; mark “pending confirmation”

## Multi-source evidence enrichment

Read `references/multi-source-evidence.md`. Multi-source evidence reinforces real behavior and hidden constraints—not for generating global resource indexes.

- Step 8 only light discovery: tests, API contracts, frontend, config, CI/CD, logs/metrics, migrations/seeds, external contracts, permission dicts, generated metadata, and runtime entries—list candidates only.
- Before generating a domain KB, dig related evidence for the current domain; do not re-scan the whole project.
- Runtime evidence must be routed: start/health/environment blockers → Operations; business behavior → KB; cross-domain mechanisms → Guide.
- Multi-source evidence can trigger Q&A: e.g. frontend names vs DB comments disagree, test assertions expose special edges, migration scripts show compat fields whose reason is invisible in current code.

## Git history weak signals

If usable Git history exists, read `references/git-history-mining.md`, then run `scripts/git_history_miner.py` for a light scan. Git history is high-noise weak signal only:

- High-churn paths hint hotspots and risk—not automatically business core.
- fix / revert / compatibility / migration / deprecation commits hint historical constraints—must enter Q&A or low-confidence pending confirmation.
- Co-changing file groups can aid domain judgment, but final closure is two-layered: **implementation entries** (code structure, APIs, tables, runtime) close on code itself; **product semantics** (is this a real feature) close on product north star and user confirmation—not decided by code or Git alone.
- Business names in commit messages may be domain-language candidates but must not outrank user confirmation, core docs, or current API wording.

## What to collect inside each business domain

- Code entries: Controller / API / Service / Facade / Component / Resolver / Handler / Job / Listener.
- Table entries: Entity / Mapper / XML SQL / table names / key fields / sharding or tenant fields.
- Flow entries: flow_code / trigger_code / node_mapping / flow components / node params.
- Event entries: MQ topic / consumers / producers / scheduled jobs / async compensation.
- Config entries: config keys, switches, cache keys, external service config.
- Status and types: enums, state machines, type fields, terminal states, idempotency checks.
- Domain-visible constraints: inheritance, annotation patterns, exception handling, transaction boundaries, locking, context propagation, cross-module call order.

## Generic implicit-semantics scan framework

Do not scan only explicit call chains. Focus where “surface source behavior” diverges from “real runtime behavior”:

- Proxy / wrap / intercept: proxies, middleware, interceptors, hooks, decorators, attributes, macros, filters.
- Declarative metadata: annotations, decorators, attributes, schemas, YAML/JSON, naming conventions, directory conventions that trigger behavior.
- Lifecycle hooks: init, start, shutdown, before/after save, after commit, mount/unmount, observer/listener/signal.
- Runtime context: tenant, user, permission, trace, locale, session, request, transaction—contexts that must exist without explicit parameters.
- External contracts: MQ, cache, search, remote APIs, third-party SDKs, DB triggers, rule engines, filesystems, async jobs.
- Generated code / compile-time rewrite: codegen, ORM, protobuf/OpenAPI/GraphQL clients, macros, source generators, compiler plugins.
- Config overrides and env differences: profiles, env, feature flags, canaries, tenant config, deploy config.

Each finding must output:

| Hidden mechanism | Trigger entry | Real effect logic | Evidence location | Affected domains | AI pitfalls | Persist to |
|---|---|---|---|---|---|---|
| [name] | [code/config/framework entry] | [what runtime actually does] | [file/symbol/config] | [domain/module] | [what goes wrong if ignored] | [KB or GUIDE] |

If a deep mechanism only affects one business domain, write it into that domain KB’s hidden constraints; if reused across domains or high change risk, generate a shared/specialized Guide candidate.

## Domain map template

**After scanning, output the complete domain map first—this is Step 8’s primary deliverable, before any per-domain detailed report.**

Enumerate all business/functional domains, one per row (table or status-annotated list):

```markdown
## Domain map (N domains total)

| Domain | Evidence anchors (dir · entry) | Status | Reason / priority |
|--------|------------------------|------|-----------------|
| Channel system | src/channels/ · ChannelHandler | Generated (reuse existing) | CHANNEL_GUIDE.md already covers |
| Agent execution loop | src/agents/ · AgentHarness | Generated (reuse existing) | AGENT_LOOP_KNOWLEDGE_BASE.md exists |
| LLM Provider system | packages/llm-runtime/ · providers/ | Deep-write this session | Core dependency; no existing docs |
| Plugin system | src/plugins/ · PluginRegistry | To be filled | Architecturally independent; not this session’s priority |
| Storage / state | src/storage/ · SQLite | To be filled | Fill after core domains are understood |
| memory-core | extensions/memory-core/ | To be filled | Git hotspot but not this session’s target |
| CLI tools | src/cli/ · commands/ | To be filled | Tooling; can fill separately |
| iOS / Android App | ios/ · android/ | To be filled | Native layer; fill separately |
| Review feedback (remembered / unsure / forgot) | Feed/ReviewInbox · ReviewFeedbackView | Candidate dead code / implementation drift | Product north star never mentions "exam-style feedback"; code is wired into nav; pending user confirmation whether it is still a real feature |
```

Map rules:

- Anchor on `project_inventory.py` `submodules` + top-level directory structure + `entry_candidates`.
- Before building the map, cross-check existing `docs/` `*_KNOWLEDGE_BASE.md` / `*_GUIDE.md` and root `AGENTS.md` nav; domains already covered mark “Generated (reuse existing)”—do not regenerate/rewrite.
- Each domain status: `Generated (reuse existing)` / `Deep-write this session` / `To be filled` / `Candidate dead code / implementation drift`—no “ignore” or “skip”. `Candidate dead code / implementation drift` is for candidates with no basis in the product north star (see “Business-domain identification”); do not generate a KB; move to the knowledge-boundary report’s “Pending discoveries” for user classification; after confirmed as a real feature, next run converts to “Deep-write this session / To be filled”.
- Thin evidence → mark “pending scan” but still list on the map.
- After map output, tell the user: reused X, deep-write main batch N, candidate dead code/drift D pending confirmation, remaining M domains will register into backlog.
- **This map must eventually be persisted into root `AGENTS.md` `## 领域地图（doc-init）`** (full rewrite at Step 9 wrap-up), with a leading `覆盖度复核基线` (coverage-review baseline) stamp of the current source fingerprint. That is doc-init’s completion anchor—`docs/` non-emptiness or scattered doc count cannot replace it. On the next doc-init run, if the section is missing, treat as “init incomplete” and re-run the flow; if present, still do not finish immediately—first coverage-review against current code (see “Coverage review” in this file); the baseline stamp exists for that review’s code-volume compare.

## Knowledge-boundary report template

After scanning, **after the domain map**, output a detailed knowledge-boundary report per **deep-write this session** domain as “business domain → generatable Knowledge Base,” and separately list shared Guide candidates. To-be-filled domains get no detailed report (scan again on continuation)—only register on the map and backlog section.

```markdown
## Knowledge-boundary report

### [Domain]
**Suggested output**: docs/[DOMAIN]_KNOWLEDGE_BASE.md

**Layering**:
- Submodules: [module/path or "single-module project"]
- Business domain: [domain]

**Business scope**:
- [Responsibilities, boundaries, main operations inferred from code]

**Domain language**:
- Suggested canonical term: [business name final body text should use]
- Implementation aliases: [code classes / enums / tables / API fields / DB comments—only aliases that help locate]
- High-risk disambiguation: [homonyms / synonyms / parameter mix-ups / comment conflicts; else "none"]

**Inferred from code in this domain**:
- Code entries: [submodule -> Controller / Service / Component / Job / Listener]
- Table entries: [table -> Entity / Mapper / key fields]
- Flow entries: [flow_code / trigger_code / component IDs / node mappings]
- Status and types: [enums / state machines / type fields]
- Domain constraints (code-visible): [inheritance, annotation constraints, tx/locks/context, etc.]
- Deep mechanisms / implicit semantics: [hidden mechanism -> trigger entry -> AI pitfalls -> persist location]

**Database evidence (if built-in database-mining subflow enabled)**:
- Connection: [connected / not connected / user forbade / no config]
- Catalog coverage: [schema count / table count / table-name prefixes or domain candidates]
- Candidate key tables: [table -> why candidate -> whether sample-table/analyze-field needed before this domain KB]
- Already deep-dug tables/fields: [only tables/fields already sample-table/analyze-field'd for this domain]
- Special field semantics: [table.column -> sample facts/field probe -> business judgment -> AI pitfalls -> confidence]
- Weak relationship candidates: [from_table.column -> to_table.column -> evidence -> confidence]
- Pending data semantics: [where DB facts conflict with or lack code/comments/user experience]

**Multi-source evidence candidates (light discovery; do not default into KB body rules)**:
- Tests / fixtures / mocks: [path -> rules/validation paths that may reinforce / why dig]
- API contracts: [OpenAPI/GraphQL/Proto/Postman/API client -> domain entries / I/O / domain-language candidates]
- Frontend / pages / menus: [path -> product names / form fields / permission buttons / business entries]
- Config / env / config center: [config key or file -> effect conditions / switches / tenants / external deps]
- CI/CD / deploy / start scripts: [path -> build/start clues / dependent services / Operations candidates]
- Logs / metrics / alerts: [path or key -> validation signals / high-risk points / pending]
- Migrations / DDL / seeds: [path -> field semantics / init data / compat fields / dict-menu candidates]
- MQ / Webhooks / third-party contracts: [topic/API/SDK -> external constraints / callbacks / signing / retries]
- Permission / menu / dict / enum config: [source -> status meaning / permission boundaries / domain-language candidates]
- Generated code / metadata / flow config: [source -> runtime effect logic / Guide candidates]
- Needs domain deep-dig: [evidence sources that must be read further before this KB; else "none"]

**User / materials**:
- Materials provided: [requirements / API docs / test cases / wiki / log entry points]
- User experience: [business names / common traps / runtime validation methods / veteran judgment]
- Conflicts with code or pending confirmation: [conflict points]

**Git weak signals (if available)**:
- Scan status: [scanned / unavailable / shallow clone / empty history / user forbade]
- Hot paths: [path -> high-churn reason candidates; only parts related to this domain]
- Historical name candidates: [business names in commit messages -> current implementation aliases or pending relation]
- fix/revert/compat/migration clues: [commit subject -> possibly affected current constraints -> evidence to verify]
- Conflicts with current evidence: [where historical names/constraints disagree with current code/docs/DB]
- Should confirm with user: [questions triggered by Git weak signals]

**Invisible in code; needs Q&A**:
- Domain-language confirmation: [inconsistent names across sources; need final canonical term or same-concept check]
- Git history confirmation: [whether historical names/compat/migration/deprecation or high-frequency fix clues still affect current implementation]
- Hidden dependencies: [what must sync before/after this domain’s operations, but code cannot prove why]
- Concept disambiguation: [semantic differences among similar IDs / statuses / types / table fields in this domain]
- Multi-source evidence confirmation: [where frontend/API/tests/DDL/logs disagree with code or user]
- Constraint origin: [non-intuitive code practices without known reasons against the intuitive approach]
- Deep-mechanism reasons: [hidden mechanisms found without knowing why they must be used that way or wrong-use consequences]
- Validation paths: [what to curl, which logs/tables/flow records to check after changing this domain]

**Existing docs**: [parts already covered in existing *.md]

**Inventory evidence**:
- Inventory file used: [.doc-init-project-inventory.json / unused]
- Helpful candidates for this domain: [key items from entry_candidates / submodules / config_candidates]
- Script false positives or gaps: [false positives, misses, places needing human judgment]

**Related Guide candidates**: [FLOWGRAM_GUIDE.md / SHARDING_GUIDE.md / ...]

### Shared / specialized Guide candidates
- [GUIDE_NAME.md]: which domains will reference it; which task scenarios should read it; what code evidence exists; why it should be an independent Guide rather than folded into a KB

### Candidate dead code / implementation drift (pending user confirmation)
- [module]: code evidence (dir/class/view) -> specific north-star wording with no basis found -> whether reachable via nav/routing -> suggested classification (suspected dead code / suspected stale product docs) -> one-sentence question for the user
```

After the report, tell the user: next questions are per business domain, only for knowledge invisible in code but affecting whether AI can change code correctly, **and prioritize confirming the candidate dead-code / drift list**—those questions decide whether modules enter the map or are excluded, ahead of general experiential Q&A; once a domain has enough info, generate its KB immediately.

## To-be-filled backlog registration format

After the main deep-write batch, write all to-be-filled domains into a dedicated root `AGENTS.md` section with the following command (once per domain):

```bash
python3 <DOC_INIT_DIR>/scripts/upsert_agents_nav.py \
  --root . \
  --backlog \
  --name "<domain> KB" \
  --anchor "<entry dir or file>" \
  --when-to-read "<before changing/troubleshooting this feature>"
```

The script creates the section and the entries itself; its heading and the `[待补充]` (pending) item prefix are literal detection keys, so do not hand-translate or hand-write them:

```
## 待补充知识库（doc-init backlog）

- [待补充] Channel system KB —— 入口锚点：src/channels/；触发场景：before changing/troubleshooting any channel integration.
- [待补充] Plugin system KB —— 入口锚点：src/plugins/；触发场景：before developing or troubleshooting plugin registration and lifecycle.
```

Only `--name` / `--anchor` / `--when-to-read` are yours to write, in the project’s doc language.

Step 11 self-assessment must report: map total / generated this session / backlog count, and assert the sum is correct (generated + backlog = total).
