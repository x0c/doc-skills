#!/usr/bin/env python3
"""
Idempotently add/update root AGENTS.md doc-nav entries, or register backlog items.

Normal doc-nav mode (default):
  upsert_agents_nav.py --root . --path docs/CUSTOMER_KNOWLEDGE_BASE.md --when-to-read "before changing customer domain"

Backlog mode (--backlog):
  upsert_agents_nav.py --root . --backlog --name "channel system KB" --anchor "src/channels/" --when-to-read "before any channel integration"
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NAV_HEADING_RE = re.compile(r"^(#{1,4})\s*文档导航\s*$", re.M)
BACKLOG_HEADING_RE = re.compile(r"^(#{1,4})\s*待补充知识库（doc-init backlog）\s*$", re.M)


def normalize_path(path: str) -> str:
    value = path.strip().replace("\\", "/")
    if value.startswith("./"):
        value = value[2:]
    return value


def ensure_sentence_end(text: str) -> str:
    text = text.strip()
    if text and text[-1] not in "。.!！?？":
        text += "。"
    return text


def make_nav_line(doc_path: str, when_to_read: str) -> str:
    return f"- `{doc_path}`：{ensure_sentence_end(when_to_read)}"


def make_backlog_line(name: str, anchor: str, when_to_read: str) -> str:
    return f"- [待补充] {name} —— 入口锚点：{anchor}；触发场景：{ensure_sentence_end(when_to_read)}"


def find_section_end(text: str, heading_match: re.Match[str]) -> int:
    """Return end offset of the heading's section (start of next same-or-higher heading)."""
    heading_level = len(heading_match.group(1))
    rest = text[heading_match.end():]
    next_heading = re.search(rf"^#{{1,{heading_level}}}\s+\S.*$", rest, re.M)
    if next_heading:
        return heading_match.end() + next_heading.start()
    return len(text)


def upsert(root: Path, doc_path: str, when_to_read: str) -> str:
    """Idempotently write one nav entry under the AGENTS.md 「文档导航」 section."""
    agents = root / "AGENTS.md"
    doc_path = normalize_path(doc_path)
    new_line = make_nav_line(doc_path, when_to_read)

    if agents.exists():
        text = agents.read_text(encoding="utf-8", errors="ignore")
    else:
        text = "# Project overview\n\n## 文档导航\n\n"

    # Replace in place if present; otherwise append at end of nav section
    line_pattern = re.compile(
        rf"^[-*]\s+.*(?:`|\()\.?/?{re.escape(doc_path)}(?:`|\)).*$", re.M
    )
    if line_pattern.search(text):
        text = line_pattern.sub(new_line, text, count=1)
    else:
        match = NAV_HEADING_RE.search(text)
        if not match:
            if not text.endswith("\n"):
                text += "\n"
            text += "\n## 文档导航\n\n" + new_line + "\n"
        else:
            section_end = find_section_end(text, match)
            before = text[:section_end].rstrip()
            after = text[section_end:]
            text = before + "\n" + new_line + "\n" + after

    agents.write_text(text.rstrip() + "\n", encoding="utf-8")
    return new_line


def upsert_backlog(root: Path, name: str, anchor: str, when_to_read: str) -> str:
    """Idempotently write one backlog entry under 「待补充知识库（doc-init backlog）」."""
    agents = root / "AGENTS.md"
    new_line = make_backlog_line(name, anchor, when_to_read)

    if agents.exists():
        text = agents.read_text(encoding="utf-8", errors="ignore")
    else:
        text = "# Project overview\n\n"

    # Replace in place if same-name entry exists (match by domain name)
    escaped_name = re.escape(name)
    line_pattern = re.compile(
        rf"^[-*]\s+\[待补充\]\s+{escaped_name}.*$", re.M
    )
    if line_pattern.search(text):
        text = line_pattern.sub(new_line, text, count=1)
    else:
        match = BACKLOG_HEADING_RE.search(text)
        if not match:
            # Create backlog section at end of file
            if not text.endswith("\n"):
                text += "\n"
            text += "\n## 待补充知识库（doc-init backlog）\n\n" + new_line + "\n"
        else:
            section_end = find_section_end(text, match)
            before = text[:section_end].rstrip()
            after = text[section_end:]
            text = before + "\n" + new_line + "\n" + after

    agents.write_text(text.rstrip() + "\n", encoding="utf-8")
    return new_line


def main() -> int:
    parser = argparse.ArgumentParser(description="Idempotently update root AGENTS.md doc nav or backlog entries")
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument(
        "--backlog",
        action="store_true",
        help="write the backlog section instead of doc nav",
    )
    # normal nav-mode args
    parser.add_argument("--path", help="doc path to register, e.g. docs/CUSTOMER_KNOWLEDGE_BASE.md")
    # backlog-mode args
    parser.add_argument("--name", help="(backlog mode) domain name, e.g. channel system KB")
    parser.add_argument("--anchor", help="(backlog mode) entry anchor, e.g. src/channels/")
    # shared by both modes
    parser.add_argument("--when-to-read", required=True, help="when-to-read / trigger-scene description")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: project root does not exist or is not a directory: {root}")
        return 2

    if args.backlog:
        if not args.name or not args.anchor:
            print("error: --backlog mode requires both --name and --anchor")
            return 2
        line = upsert_backlog(root, args.name, args.anchor, args.when_to_read)
        print(f"registered backlog: {line}")
    else:
        if not args.path:
            print("error: normal nav mode requires --path")
            return 2
        line = upsert(root, args.path, args.when_to_read)
        print(f"updated doc nav: {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
