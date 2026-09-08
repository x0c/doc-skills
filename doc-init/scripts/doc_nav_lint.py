#!/usr/bin/env python3
"""
Lint project doc navigation and doc-init artifact structure consistency.

Report-only: does not rewrite files. Use upsert_agents_nav.py when fixing nav.

Shared check entry between doc-init and other doc-governance skills (e.g. doc-compact):
- AGENTS.md/CLAUDE.md structure, orphans, self-nav, reverse global refs live only here;
- other skills should call this script rather than duplicating similar checks.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DOC_LINK_RE = re.compile(r"(?:\[[^\]]+\]\()?`?(\.?/?(?:docs|specs)/[^\s`)]+?\.md)`?\)?")
GLOBAL_REF_RE = re.compile(r"(@?\s*(?:~|\$HOME|/Users/[^/\s`，。；；、)]+)/(?:\.claude|\.codex|\.config/opencode)/[^\s`，。；；、)]+)", re.I)
NEGATIVE_EXAMPLE_RE = re.compile(r"(不要|不应|禁止|例如|示例|常见路径|路径形态|不是)")
SELF_NAV_RE = re.compile(r"(何时该读|什么时候该读|前必读|前读|必读)")
FORBIDDEN_INDEX_NAMES = {"TABLE_INDEX.md", "CODE_INDEX.md"}

# doc-init bookkeeping headings in root AGENTS.md; these two sections are the
# sole Step 6 resume signal — other skills (e.g. doc-compact) must not delete,
# fold, or rewrite them when compacting.
DOMAIN_MAP_HEADING_RE = re.compile(r"^(#{1,4})\s*领域地图（doc-init）\s*$", re.M)
BACKLOG_HEADING_RE = re.compile(r"^(#{1,4})\s*待补充知识库（doc-init backlog）\s*$", re.M)

PRUNE_DIR_NAMES = {
    "node_modules", "target", "build", "dist", "out", ".build",
    ".git", ".claude", ".stversions", "vendor",
}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def add_issue(issues: list[dict[str, Any]], severity: str, code: str, message: str, path: str = "", line: int | None = None) -> None:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if path:
        item["path"] = path
    if line is not None:
        item["line"] = line
    issues.append(item)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def normalize_doc_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    if value.startswith("./"):
        value = value[2:]
    return value


def find_protected_sections(agents_text: str) -> dict[str, Any]:
    domain_map_match = DOMAIN_MAP_HEADING_RE.search(agents_text)
    backlog_match = BACKLOG_HEADING_RE.search(agents_text)
    protected = []
    if domain_map_match:
        protected.append(domain_map_match.group(0).strip())
    if backlog_match:
        protected.append(backlog_match.group(0).strip())
    return {
        "domain_map_present": domain_map_match is not None,
        "backlog_present": backlog_match is not None,
        "protected_sections": protected,
    }


def collect_index_text(root: Path, agents_text: str) -> str:
    """Build index text: root AGENTS.md + all README.md + all *_INDEX.md.

    Same union logic as doc-compact audit check E — keep both sides in sync
    when the union rule changes.
    """
    parts = [agents_text]
    for sub in ("docs", "specs"):
        sub_dir = root / sub
        if not sub_dir.exists():
            continue
        for p in sub_dir.rglob("*.md"):
            if p.name == "README.md" or p.name.endswith("_INDEX.md"):
                try:
                    parts.append(p.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
    return "\n".join(parts)


def lint(root: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"

    agents_text = ""
    protected_info = {"domain_map_present": False, "backlog_present": False, "protected_sections": []}
    if not agents.exists():
        add_issue(issues, "error", "missing-agents", "project root is missing AGENTS.md", "AGENTS.md")
    else:
        agents_text = agents.read_text(encoding="utf-8", errors="ignore")
        protected_info = find_protected_sections(agents_text)
        if "文档导航" not in agents_text:
            add_issue(issues, "error", "missing-doc-nav", "AGENTS.md is missing the 「文档导航」 section", "AGENTS.md")
        for current_line, line in enumerate(agents_text.splitlines(), start=1):
            if NEGATIVE_EXAMPLE_RE.search(line):
                continue
            if not line.lstrip().startswith("@"):
                continue
            for match in GLOBAL_REF_RE.finditer(line):
                add_issue(
                    issues,
                    "error",
                    "global-ref-in-project-agents",
                    f"project-root AGENTS.md must not reference user-level or global instruction files: {match.group(1).strip()}",
                    "AGENTS.md",
                    current_line,
                )

    if claude.exists():
        claude_text = claude.read_text(encoding="utf-8", errors="ignore").strip()
        if claude_text != "@AGENTS.md":
            add_issue(issues, "error", "invalid-claude-md", "project-root CLAUDE.md must be a single line @AGENTS.md", "CLAUDE.md")
    else:
        add_issue(issues, "warning", "missing-claude-md", "project root is missing CLAUDE.md", "CLAUDE.md")

    docs_files: list[Path] = []
    found_docs_dir = False
    for sub in ("docs", "specs"):
        sub_dir = root / sub
        if sub_dir.exists():
            found_docs_dir = True
            docs_files.extend(sorted(p for p in sub_dir.rglob("*.md") if p.is_file()))
    if not found_docs_dir:
        add_issue(issues, "warning", "missing-docs-dir", "project root is missing docs/", "docs")

    referenced_docs = set()
    if agents_text:
        for match in DOC_LINK_RE.finditer(agents_text):
            doc_path = normalize_doc_path(match.group(1))
            referenced_docs.add(doc_path)
            if not (root / doc_path).exists():
                add_issue(
                    issues,
                    "error",
                    "dead-doc-link",
                    f"AGENTS.md nav references a missing doc: {doc_path}",
                    "AGENTS.md",
                    line_number(agents_text, match.start()),
                )

    # Orphan check index text = root AGENTS.md ∪ all README.md ∪ all *_INDEX.md
    # (valid secondary indexes). Root-only would false-positive every secondary doc.
    index_text = collect_index_text(root, agents_text)

    for doc in docs_files:
        doc_rel = rel(doc, root)
        if doc.name in FORBIDDEN_INDEX_NAMES:
            add_issue(issues, "warning", "global-index-default", f"found a global index doc; confirm it is truly needed: {doc_rel}", doc_rel)
            continue
        if doc.name == "README.md":
            continue
        if doc.name.endswith("_INDEX.md"):
            # Named secondary indexes are OK if root AGENTS.md links them; skip self-orphan check
            continue
        if doc.name not in index_text:
            add_issue(issues, "warning", "orphan-doc", f"doc under docs/specs/ not referenced by root AGENTS.md or any secondary index: {doc_rel}", doc_rel)

        text = doc.read_text(encoding="utf-8", errors="ignore")
        for match in SELF_NAV_RE.finditer(text):
            line = line_number(text, match.start())
            add_issue(
                issues,
                "warning",
                "self-navigation-in-doc",
                "docs/ body may duplicate self-nav 「何时该读 / 必读」; prefer scope/purpose wording instead",
                doc_rel,
                line,
            )
            break

    return {
        "root": str(root),
        "summary": {
            "errors": sum(1 for item in issues if item["severity"] == "error"),
            "warnings": sum(1 for item in issues if item["severity"] == "warning"),
            "docs_count": len(docs_files),
            "referenced_docs_count": len(referenced_docs),
            **protected_info,
        },
        "issues": issues,
    }


def find_project_roots(root: Path) -> list[Path]:
    """Recursively find dirs containing AGENTS.md; skip common build/vendor/backup dirs."""
    roots: list[Path] = []
    if (root / "AGENTS.md").exists():
        roots.append(root)
    for dirpath in sorted(root.rglob("*")):
        if not dirpath.is_dir():
            continue
        if any(part in PRUNE_DIR_NAMES for part in dirpath.relative_to(root).parts):
            continue
        if dirpath == root:
            continue
        if (dirpath / "AGENTS.md").exists():
            roots.append(dirpath)
    return roots


def format_text(results: list[dict[str, Any]]) -> str:
    """Plain-text one-line-per-issue format for shell grep (no jq required)."""
    lines = []
    for data in results:
        for item in data["issues"]:
            lines.append(
                "\t".join(
                    [
                        item["severity"],
                        item["code"],
                        item.get("path", ""),
                        str(item.get("line", "")),
                        item["message"],
                        data["root"],
                    ]
                )
            )
        s = data["summary"]
        lines.append(
            "\t".join(
                [
                    "SUMMARY",
                    f"errors={s['errors']}",
                    f"warnings={s['warnings']}",
                    f"domain_map_present={s['domain_map_present']}",
                    f"backlog_present={s['backlog_present']}",
                    data["root"],
                ]
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint project documentation navigation structure")
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--recursive", action="store_true", help="recursively find every dir with AGENTS.md and lint each (multi-module)")
    parser.add_argument("--output", help="output file; default stdout")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="output format; text is shell-grep friendly without jq")
    parser.add_argument("--fail-on-error", action="store_true", help="exit non-zero when any error is present")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: project root does not exist or is not a directory: {root}")
        return 2

    if args.recursive:
        roots = find_project_roots(root) or [root]
    else:
        roots = [root]

    results = [lint(r) for r in roots]
    total_errors = sum(r["summary"]["errors"] for r in results)

    if args.format == "text":
        text = format_text(results)
    else:
        payload: Any = results[0] if len(results) == 1 else {"projects": results}
        text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if args.fail_on_error and total_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
