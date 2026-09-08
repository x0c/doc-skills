# Multi Source Evidence

This document defines `doc-init` multi-source evidence enrichment rules. The goal is not to expand the default scan scope, but to reinforce real behavior, domain language, and hidden constraints that static code scans miss—using low-cost evidence candidates into domain KBs and shared Guides.

## Core principles

- Discover lightly first, then dig deep by domain; do not immediately read all tests, API contracts, frontend, configs, logs, and migration scripts.
- Evidence sources only provide candidate facts and enrichment directions; they alone do not decide business conclusions.
- Persist by semantics: business behavior → domain KB; cross-domain mechanisms → Guide; start / health / environment blockers → Operations.
- Multi-source evidence participates in domain-language unification, but must not override user confirmation, core docs, or current product/API wording.
- Record only what helps AI change code, avoid traps, or validate; do not generate global `TEST_INDEX.md`, `API_INDEX.md`, or `DDL_INDEX.md`.

## Light discovery

Prefer `scripts/project_inventory.py` `evidence_sources`. It only lists candidate paths and hit reasons; the Agent reads them and then judges which evidence relates to candidate business domains.

Light discovery only answers:

- Which evidence sources exist.
- Which business domains or shared mechanisms they may reinforce.
- Which domain KB generation is worth reading further before writing.
- Which candidates are clearly tool dirs, build artifacts, historical reports, or generated caches and should be ignored.

## Evidence sources and persistence

| Evidence source | What it can reinforce | When to dig deep | Default persistence |
|---|---|---|---|
| Tests / fixtures / mocks / test SQL | Business rules, edge cases, error codes, validation paths, historical compat scenarios | Domain already has related tests, or code rules lack reasons | Domain KB business rules, validation paths, to-be-filled |
| API contracts: OpenAPI / GraphQL / Proto / AsyncAPI / Postman / API client | Product entry points, request/response, error codes, call scenarios, domain labels | Before generating API-heavy domain KBs | Domain KB code entries, domain language, validation paths |
| Frontend routes / menus / forms / button permissions / localStorage | Product-view domains, field names, permission boundaries, page workflows | Backend module names diverge from product names, or requirements start from pages | Domain KB business background, domain language, permission constraints |
| Config / env / config-center refs / K8s / Compose | Profiles, flags, tenants, canaries, external deps, timeouts and degradation | Code behavior depends on config, or runtime validation needs environment facts | KB hidden constraints; cross-domain config mechanisms → Guide; start deps → Operations |
| CI/CD / Dockerfile / Helm / Jenkins / Actions / start scripts | Real build order, start entry points, deploy topology, required deps | Generating Operations, or code entry ≠ deploy entry | Operations; necessary runtime mechanisms → Guide |
| Logs / metrics / alert rules / tracing config | High-risk points the system cares about, validation signals, chain boundaries | Need validation paths or to identify high-risk mechanisms | KB validation paths; cross-domain observability → Guide |
| DDL / migrations / seeds / init scripts / ORM metadata | Real schema, historical compat fields, special defaults, dict/menu/permission config | Domain depends on data semantics, or field meaning is unusual | KB table/field entries, hidden constraints; shared data mechanisms → Guide |
| MQ / Webhooks / third-party SDKs / external API contracts | Business boundaries decided by external systems, signing, retries, callback states | Domain includes async, callbacks, outward services, or payment/notification external chains | KB event entries; cross-domain external contracts → Guide |
| Permission / menu / dict / enum config | Button visibility, API permissions, status meaning, domain-language alignment | Requirements involve admin pages, role permissions, dict statuses, or tenant config | KB permission constraints, status notes, domain language |
| Generated code / low-code config / form schema / BPMN / flow config / rule engines | Flows, nodes, fields, rules that take effect at runtime but are invisible in source | Finding codegen, flow orchestration, rule engines, or metadata-driven behavior | Shared Guide; single-domain use → KB hidden constraints |

## Runtime evidence routing

After the system is running, the most valuable evidence is not only “how to start.” Operations keeps only the runtime dashboard—not business rules.

| Runtime evidence | Persist to |
|---|---|
| Start commands, profile/env effect, ports, health checks, log paths, environment blockers | `OPERATIONS_GUIDE.md` |
| Actual routes / API lists, Swagger/Actuator/urls/endpoints | Corresponding domain KB entry index |
| Actually effective config, feature flags, tenant config, canary switches | Domain KB hidden constraints; cross-domain → Guide |
| DI / Bean / Middleware / AOP / Filter chains | Shared Guide; single-domain impact → KB |
| Real SQL, sharding routing, field conditions, sorting | Domain KB table/field entries and validation paths |
| MQ / Job registration, consumer groups, topics, retry policy | Domain KB event entries; shared mechanisms → Guide |
| Redis keys, TTL, cache-penetration conditions, consistency boundaries | Domain KB or cache Guide |
| Real permission behavior, frontend hide vs backend intercept differences | Domain KB permission constraints; permission mechanisms → Guide |
| State transitions, table changes, logs, messages, side effects after API calls | Domain KB flows/state machines and validation paths |
| Illegal-parameter error codes, validation rules, exception wrapping | Domain KB edge cases and validation paths |
| Core call chains inferred from tracing / logs | Domain KB or cross-domain chain Guide |

## Domain language unification

Full rules: `knowledge-network-design.md` “Domain language unification”. Multi-source evidence can supply naming evidence (frontend menus, API tag/summary, test names, DDL comments, dict values, log copy, commit messages, etc.). On conflict, do not default to generating a glossary.

## When to dig deep

Only move from candidate evidence to deep dig when one of these holds:

- A domain KB is being generated and the evidence path clearly belongs to that domain.
- Business rules, field semantics, state transitions, or validation paths cannot be judged from code alone.
- Evidence shows a shared cross-domain mechanism that may need a Guide.
- The user pointed to material / runtime / veteran experience in Intake/Q&A.
- Self-assessment shows high-risk gaps in that domain that need evidence reinforcement.

Deep-dig output should answer:

- Where is the evidence.
- Which business domain or shared mechanism it reinforced.
- What it proved, and what remains low confidence.
- What AI would get wrong if it ignored it.
- Whether it should land in KB, Guide, Operations, or only Q&A.

## Noise control

Old projects have lots of evidence and lots of noise. By default ignore:

- Agent/skill dirs: `.claude/skills/`, `.agents/skills/`.
- Historical generated reports, batch check results, temporary exports, and large machine artifacts unless the user explicitly asks to audit them.
- Process words in Git commits: `feat`, `fix`, `refactor`, `merge`, `into`, `origin`, `dev_*`, `feature_*`—never treat as business nouns.

If a path ignored by default is truly a business material source in this project, the Agent may read it manually but must explain in the report why the default filter was overridden.
