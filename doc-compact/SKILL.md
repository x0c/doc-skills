---
name: doc-compact
description: Document cleanup and compression. Core job is compressing redundant docs without losing behavioral information—drop restatement, dead links, historical narrative, and duplicate reminders; also fix structure (placement, rebuild root AGENTS.md index, add inline pointers, normalize CLAUDE.md to a single `@*.md` line, decide and split secondary indexes for oversized projects) and check/install global doc-governance rules. Use when docs are bloated, indexes are broken, AGENTS.md is swollen, CLAUDE.md has junk, or you need to confirm global instructions spell out the doc management model.
---

# doc-compact

**Document language:** Follow existing project docs / user language when writing; default English if unclear. Do not set language policy that conflicts with global AGENTS. This skill must NOT inject language/memory/review rules into `insert_doc_governance` managed blocks.

Before running, discover the files that are actually in effect—do not hardcode paths.
`<DOC_INIT_DIR>` defaults to a sibling of this skill: `<directory of this SKILL.md>/../doc-init`

## Flow

**Step 1 validate global rules → Step 2 read-only audit → Step 3 decide secondary indexes → Step 4 fix structure → Step 5 compress (core, non-skippable) → Step 6 verify**

---

## Step 1 — Global rules

**Target files are global AI instruction files only**—never pass a project `AGENTS.md`:

```bash
# Discover the real global AI instruction file (follow symlinks to the real path)
for f in ~/.claude/CLAUDE.md ~/.codex/AGENTS.md ~/.codex/instructions.md ~/.config/opencode/AGENTS.md; do
  [ -f "$f" ] && readlink -f "$f" 2>/dev/null || echo "$f"
done | sort -u
```

For each existing global file, run: `python3 <DOC_INIT_DIR>/scripts/insert_doc_governance.py <global-file-path>`.
`[跳过]` / skip = already current; `[新增/升级]` / added/upgraded = written—scan remaining sections and remove stale local conventions.
If `<DOC_INIT_DIR>` is missing: compare manually against `references/standard.md` item by item, and note “not auto-validated” in the report.

**Do not** pass the current project’s `AGENTS.md` to `insert_doc_governance.py`—project `AGENTS.md` holds project rules, not global AI instructions; writing into it pollutes project docs.

## Step 2 — Read-only audit

**Multi-component monorepo (no root `docs/`; docs live in sub-repos):** first find subdirectories that contain `docs/` or `specs/` and also `AGENTS.md` (skip `worktrees` / `node_modules` / `.git`), and run `audit.py` on **each** doc host; at the root only check CLAUDE/`AGENTS` size and navigation pointers. Do not audit only the repo root and miss `backend/docs`, `client-web/docs`, etc.

Run `python3 scripts/audit.py [project-root or sub-repo root]` to finish machine-checkable items in one pass:

- **A** Every CLAUDE.md is a single `@*.md` line
- **B** No dangling `@AGENTS.md`
- **C** No bare `OVERVIEW.md`/`INDEX.md`; named `<DOMAIN>_INDEX.md` is valid
- **D** AGENTS.md line count (> 500 lines → Step 3)
- **E** No orphan docs (under docs/specs not referenced by root AGENTS.md ∪ README ∪ `*_INDEX.md`)
- **F** File naming compliance (troubleshooting `YYYY-MM-DD-*`, review `*-review.md`)
- **G** Preset fold suggestions (troubleshooting / Review ledgers ≥3 docs, advisory; includes `operations/` incident candidates—see Step 3)
- **H** doc-init linkage: reverse global refs, domain-map section presence → **affects Step 4/5 protection boundaries**
- **I** §2.5 path liveness: for KBs that contain `§2.5 物理路径速查` / physical path quick-lookup, `ls` each listed path; STALE paths go into Step 5 cleanup (see `compression-guide.md` §2.5 path liveness)
- **J** AGENTS.md bloat metrics (chars / estimated tokens / rule count / emphasis density) and managed-block detection: paired `<!-- name:begin/end -->` markers are listed as 🔒 managed blocks (preserve verbatim on Step 4 index rebuild—do not compress or delete); unpaired markers report ❌. Only this markdown HTML-comment convention is recognized; other styles are left to agent judgment

In Step 2 also pass `--save-metrics <baseline-path>` to save the AGENTS.md metrics baseline; Step 6 uses `--compare-metrics` for before/after (estimated token increases get ⚠ and must be explained in the close-out report).

Human follow-ups: misplaced docs, redundant bloat, volatile facts restated across docs (`grep -rn "concrete number" docs/`; >2 hits is suspicious).

### Protected sections

When H shows `domain_map_present=True`, keep the root AGENTS.md sections `## 领域地图（doc-init）` / Domain map (doc-init) and `## 待补充知识库（doc-init backlog）` / Knowledge-base backlog (doc-init) **verbatim**—do not compress, fold, or delete them.

## Step 3 — Decide secondary indexes

Default is a single flat layer. **Prefer not to add levels**—each extra hop multiplies miss-read risk.

Two independent triggers (either one justifies folding):

**① Size-driven:** navigation occupies ≳ 1/2 of AGENTS.md, or rules are pushed into the second half of the file (primary criterion); fallback: > 500 lines with substantial navigation.
How to split: root keeps only “task-domain index entry” lines (one per domain); details move to named `<DOMAIN>_INDEX.md`.

**② Type-driven:**
- Troubleshooting records ≥3 → fold into `docs/troubleshooting/TROUBLESHOOTING_INDEX.md`
- Review ledgers ≥3 → fold into `docs/reviews/REVIEW_INDEX.md`
- Strong routes must include “when to skip / whether this is the authority”—not just bare filenames

**Incident docs outside `troubleshooting/` still count toward the ledger (AlphaForge 2026-09-05):** many repos put incidents under `docs/operations/` (`*incident*` / `*outage*` / `YYYY-MM-DD-*.md`). `audit.py` check G sums operations incident candidates with troubleshooting against the threshold—**humans still fold by type**. Prefer a **pointer-style** `TROUBLESHOOTING_INDEX.md` (symptom → authoritative original path); **do not relocate files by default** (relocation = high-risk whole-repo reference sync). Leave originals in `operations/`; the index must state “authority is the original; when the index may be skipped.”

## Step 4 — Fix structure

- **CLAUDE.md:** not a single line → restore `@AGENTS.md`; only an injection block with no content → delete the dangling CLAUDE.md too
- **Doc naming/placement:** align with rules (knowledge bases/guides `SCREAMING_SNAKE_CASE`, design/review `kebab-case`, troubleshooting `YYYY-MM-DD-*`); list moves/renames for confirmation first, then sync whole-repo references
- **Navigation blurbs:** check each line is “when to read” vs “what it is about”—the latter routes poorly; rewrite to the former; triggers must cover all task types (change / create / review / troubleshoot / optimize)
- **Index rebuild:** list only real docs, cluster by domain, high-frequency first; drop dead links/empty placeholders; skip protected sections; preserve 🔒 managed blocks from J verbatim
- **Injection blocks / bare indexes:** ① read the block and identify rules; ② check coverage against AGENTS.md item by item; ③ merge uncovered items after distillation; ④ delete the whole injection block
- **`managed:inherited-agents` (Codes + local `sync-agent-files`):** **do not** delete as “leftover tool injection”—`pre-commit` will reinject the whole block on the next commit. Fix dead links by changing the **product-root** navigation to absolute paths (see global `docs/WORKSPACE_ORGANIZATION_GUIDE.md`), not by clearing the block. If audit C lists this block, treat it as expected (C already exempts the marker; J lists it as a 🔒 managed block).
- **`managed:inherited-agents` (repos without reinjection hooks):** delete the injection only when child-repo-specific rules already supersede parent rulings; before delete, confirm hard rulings remain reachable from the child’s required-read entry points. Do not leave parent paths (`backend/docs/...`) verbatim in child body text as dead links.

## Step 5 — Compress (core deliverable, non-skippable)

Full compression criteria and playbook: [`references/compression-guide.md`](references/compression-guide.md)—required reading before execution (main agent reads once; pass as injection material to subagents).

**Non-negotiable constraints:**

- Every docs/specs document must pass the criteria; silent skips are forbidden; the close-out report must give a per-doc ledger (was N lines → now M lines, or “reviewed, nothing compressible, reason: xxx”)
- By default the main agent does not compress doc bodies directly—per-doc compression is dispatched to subagents in parallel; main-agent context holds only “shard plan + criteria checklist + returned ledgers”. Fallback when sharding fails: see “Subagent model and quota-failure fallback” below
- Subagents must be injected with three things: ① full compression-guide.md (criteria baseline); ② this project’s protected-section list (root AGENTS.md domain-map and KB-backlog sections; KB `§0` TOC / `§1.5` architecture mermaid / `§2.5` physical path quick-lookup; method-name anchors; 🔒 managed blocks from J—do not delete or compress); ③ high-risk list (the five “list first, confirm” items below—subagents must not execute them unilaterally; return to main agent for ruling). Without these three, criteria drift across parallel subagents is worse than serial single-agent runs
- Subagents only touch docs assigned to them under `docs/` (and this repo’s `specs/`); they must not touch root AGENTS.md / navigation / indexes—index rebuild and whole-repo reference sync are a global view, done serially by the main agent in Step 4
- After ledgers return, the main agent runs the guide’s “Drift protection for parallel subagent compression” chapter for cross-shard consistency (criteria divergence, cross-shard volatile facts, protected-section mishaps); unify high-risk rulings, then send back for landing

**Shard plan** (deterministic arithmetic, scripted; default budget 90k tokens/shard = measured net budget for a 128K window; other windows scale with `--budget`):

```bash
# Must exclude .worktrees / build caches; do not count worktree copies as product docs (script already prunes)
python3 scripts/plan_shards.py <project-root>                          # per-doc token estimate + large-KB list + directory draft groups
python3 scripts/plan_shards.py <project-root> --domain-map <map.json> # final packing: main agent clusters by domain, writes map, passes it in
```

- Cluster by domain, not physical directory: same-domain docs share terms, state machines, and constraints—one subagent keeps criteria most consistent and finds cross-doc dedup easiest. Do not split a domain (except over budget); when budget allows, the main agent may merge several small domains into one map entry to avoid spinning a subagent for a tiny domain
- Large KBs (single doc > 20k tokens) are auto-detected by the script and each get their own subagent
- On a new project’s first run, sample 3–5 docs to calibrate chars→token coefficient (script defaults adaptively pick 0.40/0.47/0.55 by content mix; override with `--coef` when far off)

**Coefficient source (measured, not guessed):** sample of 14 docs from the mc-mdcrm repo, `tiktoken cl100k_base` weighted average = **0.47** (narrative-dense 0.55–0.60; code/table-dense 0.29–0.45). Details in the `plan_shards.py` header comment.

**Budget accounting (measured on a 128K window):**

| Item | 128K-window subagent |
|------|----------------------|
| Total window | 128k |
| Minus: compression-guide.md injection | ~5k |
| Minus: protected sections + high-risk list + domain context | ~7k |
| Minus: thinking + per-doc ledger output reserve | ~18k |
| **Net budget per shard (original docs + compressed output)** | **≈ 90k tokens** |

**Execution tiers:**
- **Low risk, do directly:** restatement / dead links / historical narrative / empty placeholders / duplicate reminders / line-number refs (“line N” / “Line N” → Read first to confirm method name, then replace with `ClassName.method()` anchors) / form conversion (narrative → call chains / tables / decision tables; information unchanged, form only) (list in the report)
- **High risk, list first then confirm:** delete whole docs, rewrite large sections, split/merge index structure, edit body text that contains numbers/boundary conditions, delete §0/§1.5/§2.5 sections
- **On anomaly, fix now (no deferral):** doc anomalies found during compression—skipped/duplicated chapter numbers, duplicate subsection titles, broken tables, dangling § refs, disordered subsections, table/class/path names that look wrong vs code, unrepaired cross-doc duplication—must be fixed this round; do not defer with “hand to doc-update” or “handle next time.” Tiers: single-file fixes that do not renumber other sections (duplicate titles, broken tables, in-doc dangling refs) → subagent fixes directly; fixes that affect external refs (renumbering, subsection reorder, renames) → return to main agent, who greps whole-repo refs and fixes+syncs on the spot; factual doubts → verify against source (entity classes / @TableName / directory layout) then fix. Criteria and disposition table: guide chapter “Fix anomalies on discovery.”

**Subagent model and quota-failure fallback (2026-09-05):** when dispatching Task, **default `model` inherits the parent session**; do not hardcode quota-hungry slugs for speed (specifying `composer-2.5` once caused a whole batch of `Increase limits` failures). If every parallel Task fails to start: ① immediately retry a small smoke shard on the default model; ② if still failing, main agent **degrades to serial**, prioritizing incidents/troubleshooting → research/evals → already-dense KBs/specs marked “reviewed, nothing compressible”; ③ close-out report must say “sharding failed; degraded,” and must not pretend parallel completed.

**Second-pass compression is normal:** for architecture KBs / specs / playbooks last compressed >30 days ago, many “reviewed, nothing compressible” results are a **valid conclusion**, not laziness. Do not delete field tables, curls, or thresholds just to inflate a compression ratio. Incident docs still use the troubleshooting intensity scale—not the same scale as KBs.

**Docs compressed within the last 30 days** (trailing compact marker < 30 days old) are skipped by default; report as “recently compressed.” Drift protection when re-compressing is still needed (new content from code changes): see the guide.

**Compact marker:** after each doc is processed, append `<!-- 该文档整理/压缩于 YYYY-MM-DD -->` at the true end of the file; batch script is in the guide.

## Step 6 — Verify

```bash
# Step 2 baseline: audit.py <project-root> --save-metrics /tmp/dc-metrics.json
# Step 6 verify:
python3 scripts/audit.py <project-root> --compact-date <today YYYY-MM-DD> --compare-metrics /tmp/dc-metrics.json
```

Check I (compact-marker hard gate) **must show `压缩缺标识=0` / missing-marker count = 0** before close-out. Any unmarked doc = missed this round—finish marking and re-run. If the last full compact was < 30 days ago (most docs skipped in Step 5), the script’s “today’s marker” reading can false-alarm—the real gate is: every doc either has today’s marker or a marker from the last 30 days (i.e. “today’s markers ∪ last-30-day markers = full set”; main agent checks this), and only docs with neither are misses (established 2026-08-28 on mc-mdcrm).
If check J comparison shows AGENTS.md estimated tokens above baseline, explain why in the close-out report (e.g. user explicitly asked to add content this round)—silent growth is not allowed.
The 🔒 managed-block list must be confirmed still present verbatim in the close-out report, one by one.
H’s `domain_map_present` / `backlog_present` must not flip True → False because of this audit.
If STALE paths from audit I were cleaned in Step 5, verify should show 0; otherwise something was missed.

**§0 TOC completeness:** docs using the KB template (`*_KNOWLEDGE_BASE.md`) should have `§0 目录索引` / TOC. Missing ones are **filled this round** (mechanically from headings—low risk, do directly); list them in the close-out report; do not defer.

## Step 6.5 — Promote cross-project lessons to global (non-skippable)

After compression and audit pass, **scan this product’s `docs/` (and cross-cutting sections in root AGENTS)** for lessons that still hold in other product repos:

| Type | Typical landing (agentsync source of truth) |
|------|-----------------------------------------------|
| macOS menu bar / login silence / hide icon | `docs/MACOS_APP_DEVELOPMENT_GUIDE.md` |
| System permissions / Automation / Apple Events | `_standards/.../macos-system-permissions.md` or a registered global-index specialty |
| Distribution / notarization / Sparkle / Developer ID | `docs/APP_STORE_CHINA_LISTING_GUIDE.md` or an existing distribution guide |
| Local proxy / Claude entry | `docs/MAC_PROXY_AGENT_GUIDE.md` |
| Workspace / inherited injection / no `.git` | `docs/WORKSPACE_ORGANIZATION_GUIDE.md` |
| Leak gate | `docs/LEAK_GATE_GUIDE.md` |
| Other cross-product mechanisms | Create or extend matching `docs/*_GUIDE.md`, and add trigger words to the global `AGENTS.md` rule index |

**Actions:** compare against global authority—if global is missing, write/extend; in the product repo, turn generic sections into “authority: global …; product-specific: …” pointers. Do not merely shorten reusable passages and leave them product-only. If they contradict global, do not rule unilaterally—list under close-out “pending user confirmation.”

**This step is not optional:** user ruling 2026-09-05 requires doc governance to promote actively. Close-out reports must have a separate “promote to global” ledger (which docs written / skipped because already present / pending confirmation).

## Safety boundaries

- **Do not adjudicate content truth:** when two docs contradict and code evidence cannot decide, do not pick a winner—record in the report and ask the user. This is the only allowed “leave unfixed for the close-out report.” Difference from “fix on discovery”: anomalies verifiable via code/refs get fixed; contradictions that need a human call go upstairs
- **Do not touch:** third-party/vendored projects, build artifacts, backup dirs, git worktrees

## Reference files

| File | When to read |
|------|----------------|
| [`references/compression-guide.md`](references/compression-guide.md) | Before Step 5: compression criteria, per-doc-type intensity table, common traps and fix scripts |
| [`references/standard.md`](references/standard.md) | When Step 2 criteria are unclear: full eleven-standard explanation and volatile-fact handling |
| [`scripts/audit.py`](scripts/audit.py) | Step 2 / Step 6 automated audit (includes check J and metrics baseline compare) |
| [`scripts/plan_shards.py`](scripts/plan_shards.py) | Step 5 shard planning: per-doc token estimate, large-KB detection, budget packing (coefficients and budget constants in script header) |
