# Git History Mining

This document defines how `doc-init` uses Git history. Git history is high-noise weak signal: it only helps discover hotspots, risks, historical naming, and Q&A follow-ups—not as an authoritative source for current business rules.

## Goals

- Hotspot risk: frequently changed directories and repeatedly fixed/reverted files hint where to gather more evidence when generating KBs.
- Historical compatibility: commit-message clues about compatibility, migration, deprecation, legacy data, rollback, production, etc., trigger user follow-ups.
- Domain boundaries: files that often change together can help judge which code may belong to the same business domain.
- Domain language: commit messages are corpus of names humans used; candidates for canonical terms or historical aliases.

## Forbidden

- Do not write current business rules from commit messages alone.
- Do not promote historical names directly to the final canonical term.
- Do not generate historical incident ledgers, troubleshooting history, or formal docs of “what once happened.”
- By default do not full-history scan, `git blame`, or deep-dive PR/MR APIs or issue trackers.

## How to scan

Default:

```bash
python3 <DOC_INIT_DIR>/scripts/git_history_miner.py --root . --output .doc-init-git-history.json
```

Default scans the latest 300 commits. When generating a domain KB and paths are known, narrow the scan:

```bash
python3 <DOC_INIT_DIR>/scripts/git_history_miner.py --root . --paths src/customer service/customer --output .doc-init-git-customer.json
```

Script failure, no `.git`, empty history, or shallow clone must not block; mark Git weak signals unavailable or under-covered in the knowledge-boundary report and self-assessment.

## Domain-language rules

Full canonical-term priority is in `knowledge-network-design.md` “Domain language unification”. Names in commit messages are only evidence that “the team once called it this” (priority #4); they must not override user confirmation or core docs. Do not generate glossaries for ordinary aliases.

## Where outputs land

Git weak signals enter the knowledge-boundary report:

- Hot paths
- Historical name candidates
- fix / revert / compatibility / migration / deprecation clues
- Conflicts with current evidence
- Questions that should be confirmed with the user

Only after weak signals are cross-validated by current code, database, runtime evidence, or user confirmation may they be persisted into a domain KB or shared Guide.

## Q&A templates

- Domain language: “Git history often calls it [A]; code/tables call it [B]. Which name does the team use in requirements and conversation now?”
- Historical compatibility: “History repeatedly mentions [legacy compatibility / migration / deprecation]. Is that logic still required in current code? What must AI preserve when changing this area?”
- Hotspot risk: “[path/file] has repeated fix/revert recently. Is it a business core or historical baggage? What traps are easiest when changing it?”
- Co-change: “These files often change together: [A, B, C]. Same business flow? Should the KB merge or split them?”
