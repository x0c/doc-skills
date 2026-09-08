# Operations Validation

This document defines the runtime validation loop and conditional generation rules for `OPERATIONS_GUIDE.md`. Read it only when the project has local run / start / validate / troubleshoot value.

## Core principles

`OPERATIONS_GUIDE.md` is not a project encyclopedia or business API index; it is the Agent’s local dashboard for start-up, environment config, service liveness, and generic validation.

Static scans can only produce runtime hypotheses—never forge them as ops experience. Write only actually executed compile / start / health / minimal request / log troubleshooting and fix paths as high-confidence content; anything not executed or failed without closure must be marked “pending validation / low confidence / blocker”.

Runtime is more than an ops-doc source. Business APIs, real SQL, state changes, permissions, cache, MQ, error codes, and chain side effects seen after start belong in domain KBs or shared Guides; Operations only records start, config, health, log paths, environment blockers, and generic validation patterns.

## Runtime validation loop

Before generating Operations, judge whether it is worth and allowed to execute:

- Worth validating if the project has locally runnable services, processes, CLIs, workers, job runners, or executable test chains.
- Do not execute if the user forbids execution, asks for docs-only / report-only / dry-run / budget-limited, or the environment lacks dependencies—only output runtime hypotheses and pending items.
- Before starting many services, connecting real external systems, writing real business data, or calling test/prod APIs, state the plan and risks; without clear authorization, only do local compile, static command discovery, and side-effect-free health checks.

Execute a minimal closed loop—do not try to boot the whole system at once:

1. Command discovery: find candidate commands from README, scripts, build files, package scripts, Docker/Compose, Makefile, Procfile, CI configs.
2. Build validation: prefer minimal viable build or module-level compile; record failed commands, key errors, and whether they are pre-existing workspace blockers.
3. Start validation: start the most core or cheapest one service/process; record actual command, port, log path, and how profile/env/config take effect.
4. Liveness validation: curl health, API docs, ports, log keywords, or CLI `--help`; record what response means “alive”.
5. Minimal request validation: only side-effect-free or roll-backable minimal requests; business write validations go to domain KBs—Operations only records generic methods and environment blockers.
6. Blocker closure: on missing deps, port conflicts, config not loaded, DNS down, cache not refreshed, stale build artifacts, try one low-risk fix and record “symptom → root-cause judgment → reusable handling → evidence”.
7. Stop and clean up: if local processes were started, unless the user asks to keep them, stop before ending or document still-running processes, ports, and log paths.

Runtime validation record format:

| Item | Command/action | Result | Evidence | Conclusion | Persist to |
|---|---|---|---|---|---|
| [build/start/health/minimal-request/log] | [command] | [success/fail/blocked] | [log/status/error snippet] | [reusable experience or pending] | [OPERATIONS/KB/do not persist] |

## Persistence rules

- Successfully validated start commands, health methods, config effect, log paths → `OPERATIONS_GUIDE.md`.
- Environment blockers actually encountered and fixed → `OPERATIONS_GUIDE.md` start-failure signals or validation decision table.
- Unresolved issues that would block later Agents → `OPERATIONS_GUIDE.md` unconfirmed / blockers.
- Business semantics, business curls, business table checks → corresponding domain KB.
- Cross-domain shared runtime mechanisms (AOP / Middleware chains, cache consistency, MQ retry, sharding routing, permission intercept) → corresponding Guide.
- Historical incidents or one-off troubleshooting are not fabricated by doc-init; later `doc-update` or troubleshooting docs persist them.

Detailed runtime business-evidence routing: `multi-source-evidence.md` “Runtime evidence routing”. Operations keeps only start / environment / health content.

## Conditional OPERATIONS_GUIDE generation

Generate when:

- The runtime validation loop ran and produced at least one reusable runtime experience, validation command, start blocker, or environment difference → create or update `OPERATIONS_GUIDE.md`.
- Runtime validation was not run, but the project clearly has runnable services/processes → only a thin “runtime hypotheses and pending validation list”; all static inferences must be marked low confidence.
- No local runtime surface and no generic validation value → do not generate `OPERATIONS_GUIDE.md`; put validation method in root `AGENTS.md` or the relevant Guide.

Must include:

- `## Document positioning`: covers local start, environment config, service liveness, generic validation, and environment-level troubleshooting; explicitly does not cover concrete business rules, business state machines, or business API semantics.
- `## Validation conclusions summary`: which commands were actually run, which succeeded, which failed, which were skipped; keep static inference and measured conclusions separate.
- `## Site / process start matrix`: only sites, processes, CLIs, job runners, workers that can start or deploy independently; fields include start module/command, start class or entry, port, required external deps, locally disable-able items, confidence.
- `## Pre-start local checks`: runtime versions, package-manager commands, profile/env/config paths, hard deps (DB/MQ/cache/remote services).
- `## Start commands`: per site/process, confirmed or low-confidence-labeled commands; unconfirmable from code → pending confirmation.
- `## Liveness validation`: health endpoints, API docs, key logs, port checks, config-effect checks.
- `## Common start-failure signals`: table of “symptom / primary suspicion / how to verify / next step / evidence source”, preferring issues actually encountered and validated.
- `## Generic change-validation playbook`: cross-domain methods—e.g. how to curl HTTP changes, how to query DB writes, how to watch async jobs in logs/tables, how to distinguish auth failure vs business failure.
- `## Unconfirmed items`: only gaps that block start, validation, or environment judgment.

Must not include:

- Domain-specific API curls, business table/field checks, state-machine validation—those belong in the corresponding KB.
- Full project module/package structure or tech-stack encyclopedia—those belong in root `AGENTS.md`, domain KBs, or specialized Guides.
- Self-routing “when to read / must read” sentences—routing only in root `AGENTS.md`.
- Unevidenced ops history, real incident ledgers, production deploy details.
- Writing static guesses as verified facts; every start command, port, and config-load method not runtime-validated must be marked “pending validation”.

## Self-assessment

Doc coverage self-assessment must include Operations validation coverage:

- Runtime validation: executed [build/start/health/minimal-request/log check]; not executed [reason]
- High-confidence experience persisted: [start commands/config effect/ports/logs/fix paths]
- Low-confidence hypotheses still open: [start commands/deps/external services/env differences] marked pending validation
- Why Operations was not generated: [no runtime surface / user forbade execution / insufficient environment / no reusable ops value]
