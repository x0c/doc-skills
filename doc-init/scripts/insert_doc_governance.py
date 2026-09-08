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

CURRENT_VERSION = 16

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
* **This managed block owns only documentation structure and governance** (entry points, navigation, indexes, single source of truth, what belongs in docs, end-of-task doc checks). **It does not own:** comment/log language, disabling memory, reading standards before review, how to speak to the user, search-before-acting, or any other Agent behavior—those live only in the **non-managed** sections of the global instructions; do not re-introduce them into this block, or into doc-* skills, as a global source of truth. Boundary details: global `docs/SKILLS_GUIDE.md`.

### 2. Documentation navigation

Project-root `AGENTS.md` must contain a documentation-navigation section that registers every long-lived doc in the project.

Navigation rules:

* One navigation line per doc, with path and purpose.
* Write the purpose as "when to read", covering every task type for that domain (change / create / review / troubleshoot)—not merely "what it is".
* Gate triggers on task type and business domain (e.g. "before changing or reviewing module X"), never on whether the code already uses a given technology (e.g. "when Liquid Glass is involved"). The latter breaks review tasks: the code under review may not use that technology yet, so the model treats the condition as unmet, skips the doc, and misses exactly the "should have used it but did not" finding.
* **Importance strength must match the doc's real value:** a genuinely must-read doc (costly, hard constraints, recorded pitfalls) must be registered as "**must read** + what breaks if you skip it", in nav and in nearby pointers—not as a weak hint such as "read before involving X", "read first", or "worth a look". Agents triaging normative docs rank by that wording, and weak sentences get dropped. Being reachable from an index does not mean it will be read. (2026-08, Harbor client coordinate offset: the GCJ-02 doc existed, but was registered only as "read before involving location/maps"; the Agent skipped it and hit the same pitfall again.)
* **When the same doc is referenced from several places, the strengths must not contradict each other:** if root `AGENTS.md` says "must read", a subproject entry or nearby pointer must not soften it to "read before" or "read first"—when strengths conflict, Agents follow the weakest one (2026-08 full-repo audit: the LingoWeave product knowledge base was "must read" at root but only "read before" on the client side; the same SharedPlatform doc carried inconsistent strengths).
* **Forbidden: wrapping a doc list in one weak lead-in**, e.g. "read the following docs first when the matching domain is involved" followed by a list of knowledge bases. The lead-in is the weakest possible hint, and the entire list gets skipped with it. Every must-read doc must carry its own "**must read** + consequence"; do not weaken a whole group through a shared lead-in sentence (2026-08 audit: the JotBox and Curio backend knowledge-base lists weakened Outbox idempotency and state-machine hard constraints this way).
* **These strength rules are not limited to project-root `AGENTS.md` nav:** cross-product standards (`_standards/*.md`), `workspace-docs/*/README.md` secondary indexes, and global-instruction-file navigation follow them too—across projects, those files are the entry Agents actually land on, so their index entries also need "when to read + must read + consequence" (2026-08 audit: the swift, go, and frontend standards still used weak wording like "see" and "pitfalls in"; `java.md` and 12 java-docs runbooks had no index entry at all despite carrying hard constraints).
* **Register new docs immediately, then reverse-check; no todo placeholders:** after writing a doc under `docs/`, sync it into nav; after registering, scan `docs/` in reverse for anything missed; never leave placeholders like "should we add this?" or "register once implemented" (2026-08 audit: AlphaForge strategy and backtest architecture docs existed unregistered, with only a "should we add this?" note in `AGENTS.md`; the Infrastructure observability README carried hard pitfalls with zero registration).
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

Create a secondary index only when one class of docs has grown large enough that listing it flat hurts root `AGENTS.md` readability, e.g.:

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
* Once an authoritative conclusion or canonical term is confirmed and updated, every doc citing the old conclusion / old name must be corrected in sync; two docs must never contradict each other on the same fact at any moment. If you cannot decide which is right on the spot, return to authoritative sources (product / requirements / code); if still undecided, mark it "pending confirmation"—do not leave contradictions in place.

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

When to persist user product intent or investigation conclusions, whether to call `doc-update`, and when to promote cross-project findings to global docs—follow the **non-managed** sections of the global instructions, such as "Conclusions and product-intent persistence"; this block does not re-legislate them.

### 7. End-of-task documentation check

Before ending a task, check:

* Promised docs are finished.
* New docs are registered in root `AGENTS.md`.
* After delete / migrate / rename, old references are cleaned.
* List added / modified / deleted docs by path for the user, one line of explanation each; if nothing changed, say so explicitly: "No documentation changes this time".

| Information type | Target location |
|---|---|
| Cross-project reusable patterns / checklists / scripts | Corresponding skill files |
| Project-level behavior norms / constraints / mandatory processes | Project-root `AGENTS.md` |
| Project business rules / architecture / domain knowledge / docs invalidated by code changes | Docs under `docs/` |

Where global docs land, and end-of-task discipline such as "always call doc-update", stay in the non-managed global sections "Conclusions and product-intent persistence" and "Pre-finish reflection"; do not repeat them here.
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
