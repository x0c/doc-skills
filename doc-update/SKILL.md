---
name: doc-update
description: Session retrospective — persist reusable findings into skills or project docs, and sync docs that code changes invalidated. Use at end of session to persist reusable findings to docs.
---

**Document language:** When writing or updating project docs, follow the documentation language the project already uses and the language the user writes in; if neither is clear, default to English. Never adopt a language policy that conflicts with the global AGENTS rules.

## Core goal

The next brand-new Agent that joins should be able to understand the context, take over, and finish the work by reading the existing docs alone.

Apply this as the acceptance test for every update: *if we swapped in a new Agent right now, and it never saw this session — only these docs — could it work smoothly?*

## Boundary with memory

- This skill only updates the relevant skill file(s) or the current project's docs. It never reads or writes memory.
- If project rules disable memory, this skill still runs normally. Never read "memory is disabled" as "retrospectives and doc updates are disabled."

## Step 0: Decide whether to run

Skip conditions — if any one matches, tell the user "No updates needed this time" and stop:

- Pure Q&A or chat, with no change to code, config, process, or rules
- Every finding already exists in the current docs (search first, then decide)
- The information is useful only for this session and will not come up again
- Project rules explicitly forbid modifying skills or docs

## Step 1: Review the session and extract reusable findings

**Recall — scan everything first.** Treat this session as about to be permanently deleted: anything not written into the docs disappears with it. With that premise, scan the whole session, focusing on the two sources that leave no artifact behind (code changes survive in the diff; these live only in the conversation and are the easiest to miss):

- **Replay every user interjection, one by one** (corrections, requirements, vetoes, suggestions). Check each one against the "User correction signals" checklist below so none slip through.
- **Replay your own trial-and-error detours, section by section:** paths that only worked after several rounds, and approaches that were vetoed or that failed along the way. The finished work shows only the right answer, never what was ruled out, so record "which paths failed + root cause + final fix" — not just the symptom, and not just the conclusion.

**Distill — synthesize it yourself; never hand this decision to the user.** After recalling, judge actively: did this session produce a reusable working method, checklist, troubleshooting path, naming or placement convention, or verification bar? If so, write it up as executable items and move on to the write-down steps.

- **Never** ask the user things like "shall we distill some best practices from this session?" or "want me to capture the lessons learned?" Whether something is worth persisting is this skill's call; the user only needs to see the update result, or "No updates needed this time," in Step 4.
- **Never** dress up a one-off play-by-play as "best practices." Persist only stable conventions that future sessions will still use.
- Write each item in imperative or checklist voice (what to do, when to do it, what is forbidden), not as a session diary.

**Criteria — then filter precisely.** The core question is: *can a brand-new Agent take over smoothly by reading the docs alone?* Anything that spares it a pitfall or a re-discovery → record it; anything it can get straight from the code, git, or existing docs → skip it. Common hits of this criterion:

- Newly discovered business rules, design mechanisms, architecture constraints
- Pitfalls hit, including root cause and fix
- **Validated patterns, workflows, and checklists**, including stable practices distilled in this session. Apply the non-obvious element test: does the pattern contain non-obvious elements that would save the next Agent some digging (key decisions, pitfall workarounds, ordering choices, verification bars)? A polished play-by-play of nothing but obvious steps → skip.
- User preferences, feedback, and corrections — **tell one-off apart from long-term**: if the wording contains "from now on / every time / always / don't do that again," or it corrects, vetoes, or demands rework of something you already did, treat it as a long-term preference by default and write it down. Only a plain scoping statement about this task (for example, "this time only change X") counts as session-only.
- **User correction signals** — scan the session against this list item by item to avoid missed recall; a generic notion of "user correction" most often misses these:
  - **Redirect:** the user steers the plan or topic in another direction. This is not criticism; count it as its own signal.
  - **Dissatisfaction, confusion, friction:** the user never said "you're wrong," but expressed confusion, vague dissatisfaction, or got tangled up.
  - **Repeated request or follow-up:** the user had to ask for the same thing twice. This is the strongest "last time wasn't persisted well" signal, and it must be recorded.
  - **Better default:** the user implied the agent should already have had a better default behavior (an unstated expectation).
  - **Surface-only handling:** the request was satisfied on the surface, but the real intent was never dug out.
  - **Available resource left unused:** docs, methods, or tools were there to consult, but the agent dove in without them and caused rework.
  - **Inefficient path:** obvious detours, repeated attempts, suboptimal parameters or steps.
- Points where a code change invalidated a doc
- **Times this session failed to find a doc, or found the wrong one, because the index description did not cover the task (a routing failure).** Record the action you were carrying when you searched (viewing, optimizing, troubleshooting, creating, changing a config, and so on); Step 3c uses it to patch the index description.

**Do not record:**

- Information the code itself already expresses (function signatures, class structure, import relationships)
- Information `git log` / `git blame` can provide (who changed what, when it merged)
- Temporary debugging steps (breakpoint locations, throwaway logs)
- Failure loops with no progress (hitting the same environment or tool error over and over without advancing the task). Only **task-level** approach failures are worth recording: the dead ends, the root cause, and the final fix.
- Rules already recorded in `AGENTS.md`

## Step 2: Classify by decision tree

| Information type | Target location | Examples |
|------------------|-----------------|----------|
| Cross-project reusable patterns / scripts / checklists | The matching skill's files | Migration checklist, generic review script |
| **Project-level behavior norms / constraints / mandatory requirements** | **Project root `AGENTS.md`** | Verification process requirements, wrap-up checklists, startup commands, curl judgment criteria |
| Project business rules / architecture / domain knowledge | Matching subdirectory under the project's `docs/` | Payment callback rules, split-settlement logic |
| User preferences / feedback / corrections (project scope) | Project `AGENTS.md` or `docs/` | Workflow conventions, review norms |
| Project progress / milestones | Matching subdirectory under the project's `docs/` | Module migration completion records |
| Code change → existing doc invalidated | Sync-update the corresponding file under `docs/` | Callback route changed → update the callback doc |

**When to write to `AGENTS.md` vs. `docs/`:**

- **`AGENTS.md`:** rules, constraints, and operating norms every session must follow (instructions for AI behavior)
- **`docs/`:** reference knowledge, historical records, module details (docs for humans to read)

## Step 3: Perform the update

### 3a. Update a skill (cross-project reusable information only)

- **Never** write project-specific class names, table names, config paths, or business rules into a skill
- If repeatable work can be scripted, create the script under the skill's `scripts/` directory and reference it from the skill docs, explaining what it is for
- When updating skill docs, keep the existing structure and add incrementally

### 3b. Update project docs / `AGENTS.md`

1. **Read `AGENTS.md` first** to confirm the documentation language, index, directory layout, naming rules, and module-level coverage rules.
2. **If it is AI behavior guidance** (mandatory process, wrap-up requirements, operating constraints), write it into the matching section of `AGENTS.md`.
3. **Classify by project doc type first**, then pick the target file:
   - Project norms / agent instructions → `<project-root>/AGENTS.md`
   - Module norms (only when a module has its own conventions) → `<module>/AGENTS.md`
   - Task-domain secondary index (only when a large project triggers it) → `docs/<domain>/<DOMAIN>_INDEX.md`; trigger conditions live in `$doc-compact`. The root `AGENTS.md` is the only primary entry — **never create a bare `INDEX.md` or `OVERVIEW.md` that competes with it**.
   - Domain knowledge base → `docs/<DOMAIN>_KNOWLEDGE_BASE.md`
   - How-to / operations guide → `docs/<TOPIC>_GUIDE.md`
   - Design or refactor proposals → `docs/design/<TOPIC>_DESIGN.md` or `docs/design/<kebab-case>.md`
   - Troubleshooting records → `docs/troubleshooting/YYYY-MM-DD-<kebab-case>.md`
   - Drafts / temporary analysis → keep them out of the repo; name them `DRAFT_*.md` or `*-draft.md`
4. **A matching doc already exists** → update it incrementally with the new findings. Sync checks:
   - Code changes touched the directory structure (packages added or moved) → update `§2.5 Physical path quick reference` in the knowledge base
   - Important classes were added (Service / Component / Builder / Handler) → check the file counts and representative class names in §2.5
   - Classes or methods were renamed → grep the knowledge base for old method-name anchors (they look like `ClassName.method()`) and replace them
   - Code or directories were **deleted** → remove the now-nonexistent path rows from §2.5, and the corresponding entries from §3 and §5
5. **No matching doc exists** → create one following the classification, path, and naming rules, and **add one entry to the "文档导航" / Document navigation section of the root `AGENTS.md`** (a single line carrying a one-sentence "when to read this" purpose). When the doc backs a specific rule, also add a nearby inline pointer next to that rule. If this is a document type the project has never had before, update the document-type explanation in the root `AGENTS.md` as well.
   - **Special handling for the preset foldable types:** when creating a troubleshooting record or a Review ledger, first count how many docs of that type already exist. Fewer than 3 → link the new one directly from the root (the normal flow). Once the count reaches 3 → fold: create the matching `<DOMAIN>_INDEX.md` if it does not exist, replace all flat same-type entries at the root with a single strong route (which must state when to skip it and whether it is the authoritative source), and put the new doc's entry into `<DOMAIN>_INDEX.md`. Strong-route examples are in the two-level index section of the global doc-governance norm.
6. **Deleting, moving, or renaming a doc** → search the whole repo for references, and sync the root `AGENTS.md` document navigation and all relative links.
7. **Never** drop docs at the project root, inside source directories, or in arbitrary places. Always place them by the type rules in item 3.
8. If the project's docs are already disordered at scale (broken index, bloated `AGENTS.md`, polluted `CLAUDE.md`, leftover `OVERVIEW.md` / `INDEX.md`), do not overhaul them casually during a retrospective — hand off to `$doc-compact` for a full restructure.

### 3c. Review and repair the doc index (incremental; only entries touched or exposed this session)

**Do this when any of the following holds:**

- This retrospective added, moved, or renamed a doc
- This session failed to find a doc, or found the wrong one, because of index routing failure (the last signal in Step 1)
- **New sections or new domain content were appended to an existing doc.** Even with no new doc created, if the range of tasks that doc covers has widened, its index description must be updated in step.

**Scope is limited to entries touched this session, or entries whose problems this session exposed.** If the root `AGENTS.md` index is disordered at scale, hand off to `$doc-compact` (see Step 3b item 8) rather than overhauling it during the retrospective.

For each doc involved, review its entry in the root `AGENTS.md` "文档导航" / Document navigation section against these points:

1. **Present and unique:** the doc has **exactly one** navigation entry, and after any move or rename the old links were searched repo-wide and synced, leaving no dead links. (Mechanical checks — dead links, orphans, uniqueness — can be run with `$doc-compact`'s `scripts/audit.py`.)
2. **The description covers the task (critical, and the easiest thing to miss):** the entry must be phrased as "when to read this," and must **cover the task trigger words this session actually carried**, plus every task type that naturally arises in that domain (modify, create, review, analyze, troubleshoot, optimize). Two self-test questions:
   - *Recall the action I was carrying when I went looking for it — viewing, optimizing, troubleshooting, reviewing, analyzing, creating, changing a config, and so on. Does the description include that trigger scenario?*
   - *Do the sections or domains I added to the doc this time appear in the index description?* (Appending to an existing doc is where index-description updates are missed most often.)

   Whenever this session hit a routing failure **or** the doc's content was expanded, check and complete the description: **add the missing trigger keys — add only, never delete existing trigger scenarios.**
3. **Inline pointers:** where a doc backs a specific rule or invariant, that rule has a nearby inline pointer. The bottom navigation table is only the fallback.

**Anti-patterns** — fix on sight:

- A description that says "what the doc talks about" (a list of its contents) instead of "what task should send you to it." Content-only descriptions cannot route.
- A description framed around a single failure or a single framework (for example, only "troubleshoot X failures") when the same doc must also serve other tasks (for example, "optimize or view the X config"). Fill in the missing task dimensions instead of leaving only the troubleshooting frame.

### 3d. Correct old docs that contradict this session's truth (bounded)

**Do this when** this session established or corrected a piece of logic or a term (through a user correction, or a conclusion confirmed by several parties) and existing docs still carry the contradictory old conclusion or old name. **Scope is limited to the concepts and domains this session actually touched.** Do not census every doc looking for contradictions; that is `$doc-compact`'s full health check, not part of a wrap-up retrospective.

Fix them in place per the global rule "§5 Single source of truth"; never leave a contradiction standing as two docs that each claim to be right.

- **Ruling:** by default, verify against the authoritative source (product or requirements docs, code) before deciding. If the user has reviewed the source, explicitly overturned it, and insists on the latest understanding, then once confirmed the user wins — and write a dated 【Ruling】 entry with its rationale into the relevant doc so it does not get reversed later (format in `$doc-init`'s `references/document-templates.md` §6).
- **Propagation:** once a ruling is made, sync everything automatically, without asking again. A rename of the primary term is replaced in full across the docs this session touched, keeping implementation aliases intact. Logic changes — including deletions and major doc rewrites — also run automatically; afterwards, list exactly what was changed or deleted in the Step 4 summary.

## Step 4: Output the summary

**Wrap-up self-test:** imagine a brand-new Agent joining right now, never seeing this session, reading only the updated docs — can it take over smoothly? If yes, output the summary and stop. If no, fill in the missing information first, then report done.

Tell the user in one sentence what was updated and where. Format:

```
Updated: [target file path] — [one-sentence description of the change]
```

If this session distilled reusable practices, the summary must state exactly which convention or checklist was written down — not an empty phrase like "summarized best practices."
