# doc-skills

A set of [Claude Code](https://claude.ai/code) skills for bootstrapping and maintaining AI-readable project documentation systems.

## Skills

### `doc-init` — Documentation System Initialization

Bootstraps a full documentation system for a project from scratch. Conducts a human-assisted intake, scans business domains, identifies hidden mechanics (framework conventions, implicit invariants), optionally mines database schema and git history as evidence, and produces a navigable knowledge base usable by AI coding agents.

Use when entering a project with no doc structure, or when the global `AGENTS.md` lacks the documentation-management standard.

### `doc-compact` — Documentation Compaction & Governance

Audits and compresses project documentation without losing behavioral information. Removes redundancy (duplicate reminders, dead links, historical changelog), rebuilds the root `AGENTS.md` index, enforces single-line `CLAUDE.md` convention, and installs/upgrades the global documentation-management standard.

Use when docs are bloated, indexes break, `AGENTS.md` bloats, or `CLAUDE.md` gets polluted.

### `doc-update` — End-of-Session Documentation Debrief

Distills reusable findings from a completed session into the right destination: skill files (cross-project patterns), project `AGENTS.md` (behavioral rules), or `docs/` (domain knowledge). Runs a relevance check first — no-ops cleanly when nothing worth persisting was found.

Use at the end of a session to persist discoveries so the next agent can hit the ground running.

## How to install

Copy the skill directories into your Claude Code skills folder (typically `~/.claude/skills/` or configured via `CLAUDE_SKILLS_DIR`), then restart Claude Code.

Each skill's entry point is its `SKILL.md`. The skills reference each other where applicable (`doc-compact` delegates installs to `doc-init`'s scripts), so keeping them together is recommended.

## Design principles

- **Behavior-preserving compression** — the core test is: *does this sentence change a reader's action or judgment?* If not, delete it.
- **Single source of truth** — volatile facts (version numbers, thresholds) are maintained in one place; other docs express time-stable conclusions.
- **Two-hop navigation** — any document is reachable from root `AGENTS.md` in at most two clicks; three-level nesting is forbidden.
- **Environment-agnostic** — scripts detect actual instruction files in use rather than hardcoding paths.

## License

MIT
