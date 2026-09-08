#!/usr/bin/env python3
"""
Insert the Project Documentation Management standard into the real global AI
instruction file, with version detection and automatic upgrade.

Usage: python3 insert_doc_governance.py <real-path>

Idempotent behavior:
- If the file already has the current version → skip.
- If the file has an older version (or an unversioned old section) → replace with the new version.
- If there is no Project Documentation Management section → insert.

Insert position (priority order):
1) Before "## 附：外部托管区块" (agentsync canonical Chinese marker)
2) Before agentsync:begin / external-managed markers
3) Before the first @ reference line (@RTK.md, etc.)
4) Append at end of file

Version upgrades: after changing STANDARD, bump CURRENT_VERSION by 1;
the next doc-init run will detect and upgrade already-deployed older versions.
"""

import sys
import re

CURRENT_VERSION = 15

# Heading used in the injectable STANDARD (English for open-source inject).
SECTION_TITLE = "Project Documentation Management"
# Legacy Chinese heading still present in older deployments; must be removable on upgrade.
LEGACY_SECTION_TITLE = "项目文档管理"

STANDARD = f"""## {SECTION_TITLE}
<!-- doc-governance-version: {CURRENT_VERSION} -->

### 1. Core rules

* Root `AGENTS.md` is the project's only top-level documentation entry; long-lived docs must be reachable in one or two hops from root `AGENTS.md`.
* Project-root `CLAUDE.md` must default to a single line: `@AGENTS.md`
* When creating or first taking over a project, check whether the global AI instruction file declares where cross-project tech standard docs live; if declared, look up matching docs by the project's primary language/stack and add a reference at the top of project-root `AGENTS.md` (if undeclared, skip—do not invent paths).
* **This managed block owns only documentation structure and governance** (entry points, navigation, indexes, single source of truth, what belongs in docs, end-of-task doc checks). **It does not own:** comment/log language, disabling memory, reading standards before review, how to speak to the user, search-before-acting, or other Agent behavior—those live only in global-instruction **non-managed** sections; do not re-introduce them into this block or doc-* skills as a global source of truth. Boundary details: global `docs/SKILLS_GUIDE.md`.

### 2. Documentation navigation

Project-root `AGENTS.md` must contain a 「Documentation navigation」 section that registers every long-lived doc in the project.

Navigation rules:

* One navigation line per doc, with path and purpose.
* Purpose must be written as 「when to read」, covering all task types for that domain (change / create / review / troubleshoot)—not merely 「what it is」.
* Trigger conditions by 「task type / business domain」 (e.g. 「when changing/reviewing module X」), not by 「whether code already uses a concrete technology」 (e.g. 「when involving Liquid Glass」)—the latter fails for review tasks: the code under review may not use that technology yet, so the model skips as 「condition unmet」 and misses exactly the 「should use but does not」 finding.
* **Navigation importance strength must match the doc's real value:** truly must-read docs (costly, hard constraints, recorded pitfalls) must be written as 「**must read** + consequence preview」 in nav / nearby pointers—not weak hints (「read before involving X」「read first」「when reading」). Agents scanning normative docs sort by format weight; weak sentences are skipped. Index reachability ≠ will be read. (2026-08 Harbor client coordinate offset: GCJ-02 docs existed, but only 「read before involving location/maps」—Agent skipped and re-hit the pitfall.)
* **When the same doc is referenced in multiple places, strength must not be mutually downgraded:** if root `AGENTS.md` says 「must read」, a subproject or nearby pointer must not weaken it to 「read before / read first」—when strengths conflict, Agents follow the weaker one (2026-08 full-repo audit: LingoWeave product KB 「must read」 at root vs 「read before」 on the client side; SharedPlatform same doc with inconsistent strength).
* **Forbidden: wrapping a doc list in a batch weak lead-in:** e.g. 「Read the following docs first when involving the matching domain」 then a list of KBs—the lead-in itself is the weakest hint and the whole list gets skipped. Every must-read doc must independently say 「**must read** + consequence」; do not uniformly weaken via a lead-in sentence (2026-08 audit: JotBox/Curio backend KB lists; Outbox idempotency and state-machine hard constraints all weakened).
* **Strength rules are not limited to project-root `AGENTS.md` nav:** cross-product standards (`_standards/*.md`), `workspace-docs/*/README.md` secondary indexes, and global-instruction-file navigation follow the same strength rules—these files are the real entry for Agents across projects; index entries must also carry 「when to read + must read + consequence」 (2026-08 audit: swift/go/frontend standards still used weak 「see」「pitfalls in」 wording; java.md and 12 java-docs runbooks had no index entry despite hard constraints).
* **Register new docs immediately, then reverse-check; no todo placeholders:** after writing a `docs/` doc, sync it into nav; after registering, reverse-scan `docs/` for misses; do not leave 「should add? / register after implement」 placeholders (2026-08 audit: AlphaForge strategy/backtest architecture docs existed unregistered with only 「should add?」 in AGENTS.md; Infrastructure observability README had hard pitfalls with zero registration).
* Prefer placing doc pointers next to the rule they support, not only in a bottom navigation table.

Examples:

```md
- `docs/BILLING_KNOWLEDGE_BASE.md`: must read before changing, reviewing, or troubleshooting subscription, payment, quota deduction, or bill status flows.
- `docs/AUTH_PERMISSION_GUIDE.md`: must read before developing, reviewing, or changing user login / permission control.
```

```text
<project-root>/
├── AGENTS.md
├── CLAUDE.md
└── docs/
    ├── *_KNOWLEDGE_BASE.md (domain knowledge bases)
    ├── *_GUIDE.md (domain guides)
    ├── ...
    ├── design/
    ├── troubleshooting/
    └── ...
```

### 3. Secondary indexes

Do not create secondary indexes by default; prefer root `AGENTS.md` navigating directly to concrete docs.

Only when a class of docs is so large that flattening harms root `AGENTS.md` readability, create a secondary index, e.g.:

```text
- `docs/troubleshooting/TROUBLESHOOTING_INDEX.md`: must read before troubleshooting any fault / error / abnormal behavior—check for prior similar cases first
- `docs/reviews/REVIEW_INDEX.md`: must read before reviewing or largely changing a module: read historical review conclusions and residual risks first
```

After creating a secondary index, root `AGENTS.md` keeps only the index entry; details sink into the secondary index. No tertiary-or-deeper index chains.

### 4. Documentation changes

* New docs: register in root `AGENTS.md` at the same time.
* Deleted docs: remove the nav entry from root `AGENTS.md` at the same time.
* Migrated or renamed docs: search the whole repo for references and update them.
* New long-lived doc types: explain purpose, location, and entry path in root `AGENTS.md` at the same time.

### 5. Single source of truth

* One concept, rule, or mechanism has one authoritative source.
* Other docs that need it use relative-path links—do not copy-paste.
* Once an authoritative conclusion or canonical term is confirmed and updated, every doc citing the old conclusion / old name must be corrected in sync; two docs must never contradict each other on the same fact at any moment. If you cannot decide which is right on the spot, return to authoritative sources (product / requirements / code); if still undecided, mark 「pending confirmation」—do not leave contradictions.

### 6. What to record

Should record:

* Project-level behavior norms, constraints, mandatory processes.
* Project business rules, architecture mechanisms, domain knowledge.
* Design, process, and config explanations that change because code changed.
* Reusable failure causes, troubleshooting paths, and fixes.
* Long-lived conclusions, risk points, and follow-up constraints from reviews.

Should not record:

* Information already clearly expressed by the code itself.
* History available via `git log` / `git blame`.
* One-off phenomena.
* Information useful only for the current session and not reusable later.
* Rules already recorded elsewhere.

When to persist user product intent or investigation conclusions, whether to call `doc-update`, and when to promote cross-project findings to global docs—follow global-instruction **non-managed** sections such as 「Conclusions and product-intent persistence」; this block does not re-legislate them.

### 7. End-of-task documentation check

Before ending a task, check:

* Promised docs are finished.
* New docs are registered in root `AGENTS.md`.
* After delete / migrate / rename, old references are cleaned.
* List added / modified / deleted docs by path for the user with a one-line note each; if nothing changed, say clearly 「No documentation changes this time」.

| Information type | Target location |
|---|---|
| Cross-project reusable patterns / checklists / scripts | Corresponding skill files |
| Project-level behavior norms / constraints / mandatory processes | Project-root `AGENTS.md` |
| Project business rules / architecture / domain knowledge / docs invalidated by code changes | Docs under `docs/` |

Where global docs land and end-of-task discipline such as 「must call doc-update」 → see global non-managed 「Conclusions and product-intent persistence / Pre-finish reflection」; do not repeat here.
"""

VERSION_RE = re.compile(r"<!--\s*doc-governance-version:\s*(\d+)\s*-->")
# Match English or legacy Chinese section titles for upgrade/removal.
SECTION_HEADING_RE = re.compile(
    rf"(^|\n)(## (?:{re.escape(SECTION_TITLE)}|{re.escape(LEGACY_SECTION_TITLE)})\b.*?)(?=\n## |\Z)",
    re.S,
)


def _get_installed_version(content: str) -> int | None:
    """Return the installed version number, or None if unmarked."""
    m = VERSION_RE.search(content)
    return int(m.group(1)) if m else None


def _has_section(content: str) -> bool:
    return f"## {SECTION_TITLE}" in content or f"## {LEGACY_SECTION_TITLE}" in content


def _remove_section(content: str) -> str:
    """Remove an existing Project Documentation Management section (English or legacy Chinese)."""
    pattern = re.compile(
        rf"\n## (?:{re.escape(SECTION_TITLE)}|{re.escape(LEGACY_SECTION_TITLE)})\b.*?(?=\n## |\Z)",
        re.S,
    )
    return pattern.sub("", content)


def insert(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    installed = _get_installed_version(content)

    if installed is not None and installed >= CURRENT_VERSION:
        print(f"[skip] {SECTION_TITLE} already latest (v{installed}): {path}")
        return

    if _has_section(content):
        if installed is None:
            print(
                f"[upgrade] Unversioned old section detected; replacing with v{CURRENT_VERSION}: {path}"
            )
        else:
            print(f"[upgrade] v{installed} → v{CURRENT_VERSION}: {path}")
        content = _remove_section(content)
    else:
        print(f"[added] Inserting {SECTION_TITLE} v{CURRENT_VERSION}: {path}")

    # Insert position (priority order):
    # 1) Before "## 附：外部托管区块" (agentsync canonical Chinese marker)
    # 2) Before agentsync:begin / external-managed markers
    # 3) Before the first @ reference line (@RTK.md, etc.)
    # 4) End of file
    insert_pos = None
    for pat in (
        r"\n## 附：外部托管区块\b",
        r"\n<!--\s*agentsync:begin",
        r"\n(@\S+.*)",
    ):
        m = re.search(pat, content)
        if m:
            insert_pos = m.start()
            break
    if insert_pos is not None:
        before = content[:insert_pos]
        after = content[insert_pos:]
        new_content = (
            before.rstrip("\n") + "\n\n" + STANDARD.rstrip("\n") + "\n\n" + after.lstrip("\n")
        )
    else:
        new_content = content.rstrip("\n") + "\n\n" + STANDARD.rstrip("\n") + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[done] Wrote successfully: {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            f"Usage: python3 {sys.argv[0]} <real path of AI instruction file>",
            file=sys.stderr,
        )
        sys.exit(1)
    insert(sys.argv[1])
