---
name: doc-update
description: Session retrospective — persist reusable findings into skills or project docs, and sync docs that code changes invalidated. Use at end of session to persist reusable findings to docs.
---

**Document language:** When writing or updating project docs, follow the project's existing documentation language and the user's language; if unclear, default to English. Do not invent a conflicting language policy beyond global AGENTS.

## Core goal

The next time a brand-new Agent joins, it should understand context, take over, and finish the work by reading existing docs alone.

Use this as the acceptance test for every update: *If we swap in a new Agent now, and it never sees this session—only these docs—can it work smoothly?*

## Boundary with memory

- This skill only updates the relevant skill file(s) or the current project's docs; it does not read or write any memory.
- When project rules disable memory, this skill still runs normally; do not misread "memory disabled" as "retrospective and doc updates disabled."

## Step 0: Decide whether to run

Skip conditions (if any match, tell the user "No updates needed this time" and stop):

- Pure Q&A / chat with no code, config, process, or rule changes
- All findings already exist in current docs (search first, then decide)
- Information is useful only for this session and will not recur
- Project rules explicitly forbid modifying skills / docs

## Step 1: Review the session and extract reusable findings

**Recall (scan everything first):** Treat this session as about to be permanently deleted—anything not written into docs disappears with it. With that premise, scan the session, focusing on two artifact-free sources (code changes leave a diff; these live only in conversation context and are easiest to miss):

- **Replay every user interjection one by one** (corrections, requirements, vetoes, suggestions; match against the 「User correction signal checklist」 below item by item to avoid misses).
- **Replay your own trial-and-error detours section by section:** paths that took multiple rounds to succeed, or mid-course vetoed / failed approaches. The final artifact only shows the right answer, not what was ruled out; when recording, you must include "which paths failed + root cause + final fix," not just the symptom or just the conclusion.

**Distill (actively synthesize; do not dump this on the user):** After recall, actively judge: did this session produce a reusable working method, checklist, troubleshooting path, naming/placement convention, or verification bar? If yes, write it as executable items and proceed to the write-down steps.

- **Do not** ask the user things like "should we distill best practices from this session?" or "want to capture the lessons?"—whether it is worth writing down is decided by this skill; the user only needs to see the update result or "No updates needed this time" in Step 4.
- **Do not** dress one-off operational play-by-play as "best practices"; only persist stable conventions future sessions will still use.
- Write items in imperative / checklist voice (what to do, when, what is forbidden), not as a session diary.

**Criteria (then filter precisely):** The core question—*Can a brand-new Agent take over smoothly by reading docs alone?* Anything that saves it from pitfalls or re-discovery → record; anything it can get directly from code / git / existing docs → skip. Common hits of this criterion:

- Newly discovered business rules, design mechanisms, architecture constraints
- Pitfalls hit (including root cause and fix)
- **Validated patterns, workflows, checklists** (including stable practices distilled in this session)—apply the "non-obvious element test": does the pattern contain non-obvious elements that would save a new Agent next time (key decisions, pitfall workarounds, ordering choices, verification bars)? A pretty play-by-play of only obvious steps → skip
- User preferences / feedback / corrections—**distinguish one-off vs long-term**: if the wording includes "from now on / every time / always / don't again," or it corrects / vetoes / demands rework of something you already did → default to long-term preference and write it down; only pure scope descriptions of this task (e.g. "this time only change X") count as session-only
- **User correction signal checklist** (scan the session against this list item by item to avoid missed recall—generic "user correction" most often misses these):
  - **Redirect:** user steers the plan / topic another way (not the same as criticism; treat as its own signal)
  - **Dissatisfaction / confusion / friction:** user never said "you're wrong," but expressed confusion, vague dissatisfaction, or got tangled
  - **Repeated request / follow-up:** user had to ask the same thing again—the strongest "last time wasn't persisted well" signal; must record
  - **Better default:** user implied the agent should already have had a better default behavior (implicit expectation)
  - **Surface-only handling:** the request was met on the surface, but the real intent wasn't dug out
  - **Existing resource unused:** docs / methods / tools were available, but the agent jumped in bare-handed and caused rework
  - **Inefficient path:** clear detours, repeated attempts, suboptimal parameters / steps
- Doc invalidation points caused by code changes
- **This session failed to find / found the wrong doc because the index description didn't cover the task (routing failure)**—record what action you were carrying when you searched (view / optimize / troubleshoot / create / change config…); Step 3c uses this to patch the index description

**Do not record:**

- Information the code itself expresses (function signatures, class structure, import relationships)
- Information git log/blame can provide (who changed what, when it merged)
- Temporary debugging process (breakpoint locations, temporary logs)
- Failure loops with no progress (repeatedly hitting the same environment / tool error with no task advancement)—only **task-level** approach failures (dead ends + root cause + final fix) are worth recording
- Rules already recorded in AGENTS.md

## Step 2: Classify by decision tree

| Information type | Target location | Examples |
|------------------|-----------------|----------|
| Cross-project reusable patterns / scripts / checklists | Corresponding skill files | Migration checklist, generic review scripts |
| **Project-level behavior norms / constraints / mandatory requirements** | **Project root `AGENTS.md`** | Verification process requirements, wrap-up checklists, startup commands, curl judgment criteria |
| Project business rules / architecture / domain knowledge | Matching subdirectory under project `docs/` | Payment callback rules, split-settlement logic |
| User preferences / feedback / corrections (project scope) | Project `AGENTS.md` or `docs/` | Workflow conventions, review norms |
| Project progress / milestones | Matching subdirectory under project `docs/` | Module migration completion records |
| Code change → existing docs invalidated | Sync-update the corresponding docs/ file | Changed callback route → update callback docs |

**When to write AGENTS.md vs docs/:**

- **AGENTS.md:** Rules, constraints, and operating norms every session must follow (AI behavior instructions)
- **docs/:** Reference knowledge, historical records, module details (human-readable docs)

## Step 3: Perform the update

### 3a. Update a skill (cross-project reusable information only)

- **Do not** write project-specific class names, table names, config paths, or business rules
- If there is repeatable work that can be scripted → create a script under the skill's `scripts/` directory, and reference it in the skill docs explaining its purpose
- When updating skill docs, keep the existing structure and add incrementally

### 3b. Update project docs / AGENTS.md

1. **Read `AGENTS.md` first:** confirm documentation language, index, directories, naming, and module-level coverage rules.
2. **Is it AI behavior guidance** (mandatory process, wrap-up requirements, operating constraints) → write into the matching section of `AGENTS.md`.
3. **Classify by project doc type first**, then choose the target file:
   - Project norms / agent instructions → `<project-root>/AGENTS.md`
   - Module norms (as needed, only when a module has independent conventions) → `<module>/AGENTS.md`
   - Task-domain secondary index (as needed, only when a large project triggers it) → `docs/<domain>/<DOMAIN>_INDEX.md`; trigger conditions are in `$doc-compact`; root `AGENTS.md` is the only primary entry—**do not create bare `INDEX.md`/`OVERVIEW.md` that compete with the root**
   - Domain knowledge base → `docs/<DOMAIN>_KNOWLEDGE_BASE.md`
   - How-to / operations guide → `docs/<TOPIC>_GUIDE.md`
   - Design / refactor proposals → `docs/design/<TOPIC>_DESIGN.md` or `docs/design/<kebab-case>.md`
   - Troubleshooting records → `docs/troubleshooting/YYYY-MM-DD-<kebab-case>.md`
   - Drafts / temporary analysis → do not check into the repo; use `DRAFT_*.md` or `*-draft.md`
4. Matching doc already exists → update incrementally with new findings. **Sync checks:** if code changes involve directory structure (new/migrated packages) → update `§2.5 Physical path quick reference` in the KB; if important classes were added (Service/Component/Builder/Handler) → check §2.5 file counts / representative class names; if classes or methods were renamed → grep the KB for old method-name anchors and replace (method-name anchors look like `ClassName.method()`); if code/directories were **deleted** → remove nonexistent path rows from §2.5 and remove corresponding entries from §3/§5.
5. No matching doc → create one per classification, path, and naming rules, and **add one entry to root `AGENTS.md` 「文档导航」** (one line, with a one-sentence "when to read" purpose); when the doc supports a specific rule, add a nearby inline pointer next to that rule. If this is a previously unseen document type, also update the document-type explanation in root `AGENTS.md`.
   - **Special handling for preset foldable types:** when creating a troubleshooting or Review ledger doc, first count how many docs of that type already exist—under 3, link them directly from the root (normal flow); at 3, fold: create the matching `<DOMAIN>_INDEX.md` (if missing), replace all same-type flat root entries with one strong route (including "when to skip / whether this is the authority"), and put the new doc entry into `<DOMAIN>_INDEX.md`. Strong-route examples are in the global norm 「两级索引」 section.
6. Delete, migrate, or rename a doc → search whole-repo references; sync-update root `AGENTS.md` document navigation and relative links.
7. **Do not** create docs arbitrarily at the project root, in source directories, or in random places—always place them by the type rules in step 3.
8. If project docs are already widely disordered (broken index, bloated `AGENTS.md`, polluted CLAUDE.md, leftover `OVERVIEW.md`/`INDEX.md`), do not casually overhaul during retrospective—hand off to `$doc-compact` for a full restructure.

### 3c. Document index review and repair (incremental; only entries touched / exposed this time)

**When to do this:** any of the following:

- This retrospective added / migrated / renamed docs
- This session failed to find / found the wrong doc due to index routing failure (Step 1 last signal hit)
- **New sections or new domain content were appended to an existing doc** (even without creating a new doc, if the task scope the doc covers widened, the index description must be updated in sync)

**Scope is limited to entries touched this time or whose problems were exposed this time**; if root `AGENTS.md` indexing is widely disordered, hand off to `$doc-compact` (see Step 3b item 8)—do not casually overhaul during retrospective.

For each involved doc, review its entry in root `AGENTS.md` 「文档导航」 item by item:

1. **Exists and unique:** the doc has **exactly one** navigation entry; after migrate / rename, old links were searched and synced repo-wide with no dead links. (Mechanical checks like dead links / orphans / uniqueness can run via `$doc-compact`'s `scripts/audit.py`.)
2. **Description covers the task (critical, easiest to miss):** the entry description must use the "when to read" sentence form, and **cover the task trigger words actually carried in this session**, plus all task types naturally possible in that domain (modify / create / review / analyze / troubleshoot / optimize). Self-test with two questions—
   - *Recall what action I was carrying when I looked for it (view / optimize / troubleshoot / review / analyze / create / change a config…)—does the description include that trigger scenario?*
   - *Did I add new sections or domains to the doc this time—does the index description cover them?* (Appending to an existing doc is the scenario where index-description updates are most often missed)

   Whenever this session had a routing failure **or** the doc content was expanded, check and complete: **add the missing trigger keys into the description (incremental add only; do not delete existing trigger scenarios)**.
3. **Inline pointers:** when a doc supports a specific rule / invariant, that rule has a nearby inline pointer (the bottom navigation table is only a fallback).

**Anti-patterns** (hit → fix):

- Description written as "what it talks about" (listing doc content) rather than "with what task you should read it"—content-only descriptions cannot route.
- A failure / single-framework description (e.g. only "troubleshoot X failures") that must also serve other tasks for the same doc (e.g. "optimize / view X config")—complete the task dimensions; don't leave only the troubleshooting frame.

### 3d. Correct old docs that conflict with this session's truth (bounded)

**When to do this:** this session established or corrected a piece of logic or terminology (user correction, multi-party confirmed conclusion), and existing docs contain contradictory old conclusions / old names. **Scope is limited to concepts / domains this session actually touched**—do not census every doc for contradictions; that is `$doc-compact`'s full health check, not part of wrap-up retrospective.

Fix in place per global norm 「§5 单一来源」; do not leave contradictions as two docs each claiming truth:

- **Ruling:** default to verifying against the authority (product / requirements docs, code) before deciding; if the user reviewed the source, explicitly overturned it, and insists on the latest understanding, after confirmation the user wins—and write a dated 【裁定】 record with rationale in the corresponding doc to prevent later overturns (format in `$doc-init`'s `references/document-templates.md` §6).
- **Propagation:** after a ruling, sync all changes automatically without a second confirmation. Renames (primary term) are fully replaced in docs this session touched, keeping implementation aliases; logic changes including delete / major doc rewrites also run automatically, then list what was changed / deleted in detail in the Step 4 summary.

## Step 4: Output summary

**Wrap-up self-test:** imagine a brand-new Agent joining now, never seeing this session, only reading the updated docs—can it take over smoothly? Yes → output the summary and stop; No → fill the missing information first, then report done.

Tell the user in one sentence what was updated and where. Format:

```
Updated: [target file path] — [one-sentence description of the change]
```

If this session distilled reusable practices, the summary must say clearly "what convention / checklist was written down," not empty phrases like "summarized best practices."
