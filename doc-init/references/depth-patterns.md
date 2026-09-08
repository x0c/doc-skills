# Depth Patterns

This document defines knowledge-extraction patterns for the doc-init deep-scan stage. Read it after Step 8 scanning finishes and before per-domain deep-write.

`scripts/depth_scanner.py` provides mechanical extraction (status transitions, concurrency locks, event publish, DSL formats, and other raw signals). This doc guides the model on turning mechanical results into KB section content—the scanner tells you “where”; this doc tells you “what to write, where to put it, and what goes wrong if missed.”

---

## 7 common extraction patterns

### Shared extraction flow (all patterns)

All patterns share these steps; each pattern section only adds that pattern’s confirmation points:

1. Collect raw signals from the matching `depth_scanner.py` output field (field mapping at the end: “Mapping from depth_scanner.py output to KB”)
2. Read code to confirm signal truth—discard false positives and note in §9
3. Record key attributes (each pattern differs; see “Confirmation points” below)
4. Write into the matching KB section (see end mapping table); each item cites code evidence

### a) State-machine extraction

**KB section:** §2 Core flows / state machines

**Generic recognition signals:**

- An entity field stores current “phase” or “status” with a limited semantic value set
- Conditions like “only in state A can you run operation B”
- Write logic like “after operation C, state necessarily becomes D”
- Terminal states (no natural further change; only special ops intervene)
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Per status value: grep methods that write it (= transition-triggering ops) and precondition check sites that read it (= transition preconditions)
- Output format: `StateA --[op]--precondition--> StateB`, mark terminal states

**AI pitfall:** Without extracting the state machine, AI triggers ops in the wrong state (e.g. freeze an already-cancelled entity), causing consistency bugs that only fire on specific status flows.

---

### b) Concurrency-control recognition

**KB section:** §6 Hidden constraints (**AI pitfall** tag)

**Generic recognition signals:**

- Writes to the same resource use optimistic-lock version fields (`version`) or explicit lock acquisition
- Distributed lock key construction (often `"lock:" + entityId`)
- Retry logic wrapping concurrency-conflict exception catches
- CAS-style updates (`WHERE version = ?` with updated-row checks)
- Idempotent write then lock (double-check: lock then read + write)
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Confirm protected entity/op, lock granularity (object/op/global), lock scope (TTL/tx boundary), lock key construction
- Note failure handling (throw / retry / idempotent return)

**AI pitfall:** Without recognizing concurrency control, AI introduces: ① races after removing locks (negative balances, status overwrites under high concurrency); ② dirty reads of locked variables outside the lock scope; ③ changing lock-key construction so locks silently fail. Concurrency bugs do not reproduce in local single-thread tests.

---

### c) Idempotency recognition

**KB section:** §6 Hidden constraints

**Generic recognition signals:**

- Write inputs include externally supplied business serials (`tradeNo`, `orderId`, `requestId`, `idempotencyKey`)
- Before write, check “already exists” and return the existing result on hit
- Unique constraints (DB / in-memory) as last-line duplicate prevention with conflict catch logic
- After the op, write an idempotency record table or Redis key
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Confirm idempotency key source (input field naming patterns) and whether “read-before-write” returns on hit
- Confirm reliance on DB unique indexes as fallback and whether exception handling is correct

**AI pitfall:** Without recognizing idempotency, AI will: ① drop the read-before-write step and duplicate writes; ② change the idempotency key field so one request runs many times; ③ forget to update the idempotency record after rewriting the op so retries return stale results.

---

### d) Multi-tenant / sharding routing

**KB section:** §6 Hidden constraints + §7 Validation paths

**Generic recognition signals:**

- Table or index names with numeric / tenant-id suffixes (`orders_0`, `user_tenant_123`)
- Context switch points that set “current tenant / shard key” in the request lifecycle
- Interceptors / plugins / middleware that rewrite logical table names to physical ones
- Explicit `tenantId` / `shardKey` / `settingId` params in many places, or implicit ThreadLocal / context injection
- Global (non-sharded) tables coexist with sharded ones, with allowlists or exclude lists
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Find the routing core entry (interceptor/plugin/context set point)
- Enumerate which tables are sharded vs global (must not shard)
- Record shard-key source (input/ThreadLocal/header), switch timing, reset timing

**AI pitfall:** Without recognizing sharding routing, AI will: ① query the base/template table and think there is no data; ② call Services without setting context and mis-route or error; ③ ALTER only the base table and miss physical shards; ④ wrongly add global config tables into shard init and scramble routing.

---

### e) Event-driven recognition

**KB section:** §5 Flow / MQ entry index + cross-domain linkage candidates

**Generic recognition signals:**

- Message-queue producer/consumer pairs
- Async events (`ApplicationEventPublisher.publishEvent`, `@EventListener`, `EventEmitter.emit`)
- Webhook callback handlers (external events)
- Cron jobs that trigger subsequent business flows
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Per producer: topic/event type, payload structure, trigger timing
- Per consumer: subscribed topic/event type, handler entry, failure policy
- Identify cross-domain linkage: producer in domain A, consumer in domain B

**AI pitfall:** Without recognizing event-driven flows, AI will: ① think deleting an A-domain entity only affects A and miss B-domain consumer cascades; ② think the op finishes synchronously when results only land after message consumption; ③ treat producers and consumers in different services as unrelated and change one side’s interface without the other.

---

### f) Config / DSL format extraction

**KB section:** §6 Hidden constraints (format rules)

**Generic recognition signals:**

- A field stores JSON / YAML / custom strings that business code parses before use
- Dedicated DSL parser / converter classes (`*Parser`, `*Converter`, `*Resolver`, `*Deserializer`)
- Enum-driven format branches (`switch(type)` decides how to parse the same field)
- Rule-engine / flow-engine conditions and params stored as structured data in the DB
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Find the parser entry; reverse-trace the DB or input field it handles
- List all `type` enum values; for each, state format requirements (required fields, value domains, nesting)
- If format versions (v1/v2) exist, state the version discriminator and compatibility logic
- Extract typical valid samples (JSON/YAML snippets); note which fields may be null and which nulls silently break

**AI pitfall:** Without extracting DSL formats, AI will: ① generate ill-formed data whose parse errors surface deep in business logic rather than as format errors; ② omit required fields without `@NotNull` and hit runtime NPEs; ③ store old format versions in new features and trigger compatibility issues.

---

### g) Soft-delete patterns

**KB section:** §6 Hidden constraints (query constraints)

**Generic recognition signals:**

- Entities use `deleted_at`, `is_deleted`, `biz_status`, `status` to mark deletion instead of physical delete
- Queries default-filter deleted rows (framework `@Where`, plugin intercept, manual `.ne("status", DELETED)`)
- Some query scenarios must see “deleted” rows (audit, cascade cleanup, history)
- Same FK can have many rows with only one “active” (soft-delete + create replaces old version)
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Find soft-delete fields and framework/global filters
- Search “bypass default filter” scenarios (`Unscoped()`, `withDeleted()`, manual `includeDeleted`)
- Sort which query scenarios must include deleted rows (cascade cleanup, idempotent dedupe, audit)

**AI pitfall:** Without recognizing soft-delete, AI will: ① miss already soft-deleted same-key rows during idempotent dedupe and create duplicates; ② forget soft-deleted children during cascade cleanup and leave orphans; ③ `DELETE FROM` physically and bypass business status flows.

---

### h) Entity field semantic traps

**KB section:** §4 Table/field entries + §6 Hidden constraints (**AI pitfall** tag)

**Generic recognition signals:**

- Entity fields whose “guess by name” usage would write bugs
- Same-named fields mean different concepts across entities/tables
- NULL has special business meaning (not “unset” but “forever / unlimited / default”)
- Field types that defy intuition (`Integer` stores enum codes not numbers; `String` stores JSON not text)
- Fields with implicit framework behavior: `logic_id` / `version` / `biz_status`
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Per field check: ① same name across entities with different meaning? ② NULL has business semantics? ③ implicit framework behavior (optimistic lock / auto-fill / logical delete)? ④ FK naming implies a different target than reality?
- Especially multi-table same-named fields with different semantics (easy to mix via autocomplete)

**AI pitfall:** Without extracting field semantics, AI will: ① write `WHERE expire_time > NOW()` and miss NULL=forever-valid rows; ② pass same-named fields between Services with wrong meaning (e.g. a “customer TID” into an API expecting a “transaction TID”); ③ delete or change fields with implicit framework behavior (e.g. remove `@Version` and lose concurrency control).

---

### i) JSON field format extraction

**KB section:** §6 Hidden constraints (format rules)

**Generic recognition signals:**

- Entity fields typed `String`/`Text`/`JSONB` that actually store structured JSON with dedicated deserialize logic
- TypeHandler / ValueConverter / custom serializers mapping DB fields to DTO objects
- Legal structure routed by an enum `type` field into different sub-formats
- Parse logic that “silently fails on bad format” (try-catch swallows and returns null/empty)
- Language-specific signals: see end “Language-variant signal summary”

**Confirmation points:**

- Trace deserialize target types (DTO/record/struct); list all field meanings and value domains
- Confirm: ① which subfields are required (missing → NPE)? ② all legal `type` enum values? ③ is NULL legal? ④ format-version compatibility?
- Give a “minimal valid sample” JSON + “what error looks like when a key field is missing”
- Highlight fields where “frontend omits → deserializes to null, but code uses without checking”

**AI pitfall:** Without extracting JSON field formats, AI will: ① generate ill-formed data (e.g. omit required `type` and fall into default/null branches); ② UPDATE JSON in DB and break structure (array written as object); ③ add JSON fields in new features without updating deserialize DTOs so fields are silently dropped.

---

## Language-variant signal summary

| Pattern | Java/Kotlin | Python | TypeScript/JS | Go | C#/.NET |
|------|-------------|--------|---------------|-----|---------|
| State machine | `enum` + `Assert` prechecks | `choices=` + validation | union type + `switch` | `const iota` + error returns | `enum` + `switch` throw |
| Concurrency | `@Version` / `SELECT FOR UPDATE` / Redis NX | `select_for_update()` / Redis NX | `$transaction` / Redis NX | `sync.Mutex` / `WHERE version=` | `[Timestamp]` / `IsolationLevel` |
| Idempotency | `DuplicateKeyException` + `insertOrIgnore` | `get_or_create()` / `IntegrityError` | `upsert` / `findOrCreate` | `ON CONFLICT DO NOTHING` | `AddOrUpdate` / `ON CONFLICT` |
| Sharding routing | `@TableName` + interceptor / `BusinessContextHolder` | DB router / schema switch | middleware / `Table()` | `Table(name)` / context inject | EF dynamic schema / ABP multi-tenant |
| Event-driven | `@RabbitListener` / `@EventListener` | Celery / Django signal | Bull / `@EventPattern` | channel / NATS client | MassTransit / MediatR |
| DSL format | `ObjectMapper` / TypeHandler | `json.loads` / pydantic | `JSON.parse` / zod | `json.Unmarshal` / custom UnmarshalJSON | `JsonSerializer` / EF value converter |
| Soft-delete | `@TableLogic` / `@Where` | `paranoid` / `SoftDeleteQuerySet` | Prisma `deletedAt` / `paranoid: true` | GORM `soft_delete` / `WHERE deleted_at IS NULL` | EF `HasQueryFilter` |
| Field semantic traps | multi-place same-name `tid` / `@Version` / `NULL=forever` | `default=None` with meaning / mismatched `ForeignKey` names | `nullable: true` + null has meaning | same-name tags differ / `json:"-"` | `[NotMapped]` + computed logic / different column map names |
| JSON fields | `JacksonTypeHandler` / `JSON.parseObject` | `JSONField()` / `json.loads` | `JSON.parse` → typed / Prisma `Json` | `json.Unmarshal` / `type:jsonb` | `jsonb` Column + ValueConverter |

---

## Mapping from depth_scanner.py output to KB

`depth_scanner.py` JSON fields → this doc’s patterns → KB landing sections:

| Output field | Pattern | KB section |
|----------|----------|-----------------|
| `status_patterns` | State-machine extraction (a) | §2 Core flows / state machines |
| `concurrency_patterns` | Concurrency-control recognition (b) | §6 Hidden constraints |
| `idempotent_patterns` | Idempotency recognition (c) | §6 Hidden constraints |
| `sharding_patterns` | Multi-tenant / sharding routing (d) | §6 Hidden constraints + §7 Validation paths |
| `event_patterns` | Event-driven recognition (e) | §5 Flow index + cross-domain linkage candidates |
| `dsl_patterns` | Config / DSL format extraction (f) | §6 Hidden constraints |
| `soft_delete_patterns` | Soft-delete patterns (g) | §6 Hidden constraints |
| `entity_fields` | Entity field semantic traps (h) | §4 Table/field entries + §6 Hidden constraints |
| `json_field_patterns` | JSON field format extraction (i) | §6 Hidden constraints (format rules) |
| `framework_components` | — | §3 Code entries + §5 Flow index (by component type into the matching domain) |
| `runnable_project.type` | — | Root `AGENTS.md` ops cheat sheet (see next section) |

**Handling rules:**

- `depth_scanner.py` outputs raw signals, not final KB content. The model must interpret with business semantics (e.g. a `version` field may be an optimistic lock or a config version number).
- One signal may hit multiple patterns (idempotency often also depends on concurrency control); KB items for both patterns should cross-reference—do not expand twice.
- Components listed in `framework_components` go into the matching domain KB by business domain—do not generate a standalone “tech component index” doc.

---

## Conditional ops cheat-sheet generation

`runnable_project.type` decides whether and how root `AGENTS.md` gets an ops cheat sheet. Generate only when confirmed as a runnable service (not a pure library or CLI tool).

### spring-boot

- **Port:** from `server.port` in `application*.properties` / `application*.yml`; read per module in multi-module projects
- **Module and start aliases:** find `spring-boot-maven-plugin` `<configuration>` in each submodule `pom.xml`, or read `spring-boot:run` `mainClass`
- **Ops cheat-sheet content:**
  - Each module alias → port → Maven module path
  - `mvn -pl <module> spring-boot:run` start commands
  - Log paths (`logging.file.name` or convention `logs/{APP_NAME}.log`)
  - Health endpoints (`/actuator/health` if actuator is present)

### django

- **Port:** from `settings.py` `PORT` / `ALLOWED_HOSTS`, or `Procfile` / `docker-compose.yml`
- **Ops cheat-sheet content:**
  - `python manage.py runserver [port]` start command
  - `settings.py` path + `DATABASES` location
  - Logging config location (`LOGGING` dict)

### express / nestjs

- **Port:** from `.env` `PORT`, or `app.listen(PORT)`, or `package.json` `scripts.start`
- **Ops cheat-sheet content:**
  - `npm run start` / `npm run start:dev` commands
  - Env vars that must be configured (from `.env.example`)
  - Logging frameworks (`winston`, `pino`, etc.) and log paths

### docker / docker-compose

- **Port:** from Dockerfile `EXPOSE` or `docker-compose.yml` `ports` mappings
- **Ops cheat-sheet content:**
  - `docker-compose up` / `docker build` start commands
  - Required env vars (`environment` section + `.env.example`)
  - Healthcheck config (`healthcheck`)

### library / cli / unknown

Skip the ops cheat sheet. Note in root `AGENTS.md`: “This project is a library / CLI tool with no standalone runnable service; no ops cheat sheet generated.”

---

## Budget control

- Per pattern: at most 2 grep / script calls; stop digging once signals suffice to judge
- When the same pattern hits multiple business domains, write a shared Guide candidate first, then reference the Guide from each KB §6—avoid duplicate expansion
- Empty `depth_scanner.py` fields get no extra search; note “pattern not found” in the matching KB section
