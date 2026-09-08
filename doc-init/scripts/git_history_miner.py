#!/usr/bin/env python3
"""Lightweight Git-history weak-signal miner."""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KEYWORD_GROUPS = {
    "fix": ["fix", "bug", "hotfix", "修复", "异常", "问题", "报错"],
    "revert": ["revert", "rollback", "回滚", "撤销"],
    "compatibility": ["compat", "compatible", "legacy", "兼容", "历史", "老数据", "旧数据"],
    "migration": ["migrate", "migration", "迁移", "转换"],
    "deprecated": ["deprecated", "deprecate", "废弃", "下线", "删除"],
    "risk": ["临时", "兜底", "线上", "重复", "幂等", "补偿"],
}

DEFAULT_EXCLUDED_PATH_PARTS = {
    ".git",
    ".idea",
    ".claude",
    ".agents",
    ".codex",
    ".codegraph",
    "target",
    "build",
    "dist",
    "out",
    "node_modules",
    ".gradle",
    ".mvn",
    ".pytest_cache",
    "__pycache__",
}

DEFAULT_EXCLUDED_PATH_SEQUENCES: set[tuple[str, ...]] = set()

DEFAULT_EXCLUDED_PATHS = {
    "AGENTS.md",
    "CLAUDE.md",
}

ENGLISH_STOPWORDS = {
    "add",
    "feat",
    "feature",
    "fix",
    "bug",
    "hotfix",
    "update",
    "remove",
    "delete",
    "refactor",
    "merge",
    "into",
    "origin",
    "remote",
    "tracking",
    "remote-tracking",
    "branch",
    "master",
    "main",
    "dev",
    "test",
    "tests",
    "init",
    "initial",
    "change",
    "changes",
    "code",
    "style",
    "format",
    "build",
    "ci",
    "docs",
    "readme",
    "revert",
    "rollback",
    "doc",
    "docs",
    "document",
    "documentation",
    "skill",
    "commit",
}

CHINESE_PREFIXES = (
    "修复",
    "新增",
    "增加",
    "优化",
    "调整",
    "兼容",
    "删除",
    "回滚",
    "迁移",
    "处理",
    "支持",
    "更新",
    "补充",
)

CHINESE_STOPWORDS = {
    "新增",
    "增加",
    "修复",
    "优化",
    "调整",
    "删除",
    "回滚",
    "迁移",
    "处理",
    "支持",
    "更新",
    "补充",
    "字段",
    "入口",
    "代码",
    "文件",
    "问题",
    "文档",
    "测试",
    "改为",
}


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_toplevel(root: Path) -> Path | None:
    proc = run_git(root, ["rev-parse", "--show-toplevel"])
    if proc.returncode != 0:
        return None
    text = proc.stdout.strip()
    if not text:
        return None
    return Path(text).resolve()


def default_paths_for_root(root: Path) -> list[str]:
    toplevel = git_toplevel(root)
    if not toplevel:
        return []
    root = root.resolve()
    if root == toplevel:
        return []
    try:
        root.relative_to(toplevel)
        return ["."]
    except ValueError:
        return []


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def top_path_dir(path: str, depth: int = 2) -> str:
    parts = [part for part in Path(path).parts if part not in (os.sep, "")]
    if not parts:
        return path
    return "/".join(parts[:depth])


def has_path_sequence(path: str, sequence: tuple[str, ...]) -> bool:
    parts = tuple(part for part in Path(path).parts if part not in (os.sep, ""))
    for idx in range(0, len(parts) - len(sequence) + 1):
        if parts[idx : idx + len(sequence)] == sequence:
            return True
    return False


def is_default_excluded_path(path: str) -> bool:
    if path in DEFAULT_EXCLUDED_PATHS or Path(path).name in DEFAULT_EXCLUDED_PATHS:
        return True
    parts = [part for part in Path(path).parts if part not in (os.sep, "")]
    if any(part in DEFAULT_EXCLUDED_PATH_PARTS for part in parts):
        return True
    return any(has_path_sequence(path, sequence) for sequence in DEFAULT_EXCLUDED_PATH_SEQUENCES)


def detect_keywords(subject: str) -> list[str]:
    lower = subject.lower()
    hits: list[str] = []
    for group, words in KEYWORD_GROUPS.items():
        if any(word.lower() in lower for word in words):
            hits.append(group)
    return hits


def clean_chinese_term(term: str) -> str:
    cleaned = term.strip(" ：:，,。.;；（）()[]【】")
    changed = True
    while changed:
        changed = False
        for prefix in CHINESE_PREFIXES:
            if cleaned.startswith(prefix) and len(cleaned) > len(prefix) + 1:
                cleaned = cleaned[len(prefix) :]
                changed = True
    return cleaned.strip(" ：:，,。.;；（）()[]【】")


def extract_terms(subject: str) -> list[str]:
    terms: list[str] = []
    if subject.lower().startswith("merge "):
        return terms
    for raw in re.findall(r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_-]{1,15}", subject):
        term = clean_chinese_term(raw)
        if 2 <= len(term) <= 16 and term not in CHINESE_STOPWORDS:
            terms.append(term)
    for raw in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b", subject):
        term = raw.strip("_-")
        lower = term.lower()
        if (
            lower not in ENGLISH_STOPWORDS
            and not term.isdigit()
            and not lower.startswith(("dev_", "feature_", "feat_", "release_", "hotfix_"))
            and not lower.startswith(("dev-", "feature-", "feat-", "release-", "hotfix-"))
            and lower not in {"dev_java", "grandjoy_master"}
        ):
            terms.append(term)
    return terms


def parse_git_log(text: str) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    for block in text.split("\x1e"):
        block = block.strip()
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        header = lines[0].split("\x1f", 2)
        if len(header) != 3:
            continue
        commit_hash, date, subject = header
        paths = [line for line in lines[1:] if line and not line.startswith("\x1f")]
        commits.append(
            {
                "hash": commit_hash,
                "short_hash": commit_hash[:12],
                "date": date,
                "subject": subject,
                "paths": paths,
                "keywords": detect_keywords(subject),
                "terms": extract_terms(subject),
            }
        )
    return commits


def load_commits(root: Path, max_commits: int, paths: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    args = [
        "log",
        f"-n{max_commits}",
        "--date=short",
        "--pretty=format:%x1e%H%x1f%ad%x1f%s",
        "--name-only",
    ]
    if paths:
        args.extend(["--", *paths])
    proc = run_git(root, args)
    if proc.returncode != 0:
        return [], proc.stderr.strip() or "git log failed"
    commits = parse_git_log(proc.stdout)
    if not paths:
        filtered: list[dict[str, Any]] = []
        for commit in commits:
            kept_paths = [path for path in commit["paths"] if not is_default_excluded_path(path)]
            if not kept_paths:
                continue
            commit["paths"] = kept_paths
            filtered.append(commit)
        commits = filtered
    return commits, None


def summarize(commits: list[dict[str, Any]], paths: list[str], max_items: int) -> dict[str, Any]:
    file_counts: Counter[str] = Counter()
    dir_counts: Counter[str] = Counter()
    term_counts: Counter[str] = Counter()
    term_subjects: dict[str, list[str]] = defaultdict(list)
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_examples: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    keyword_hits: list[dict[str, Any]] = []

    for commit in commits:
        for path in commit["paths"]:
            file_counts[path] += 1
            dir_counts[top_path_dir(path)] += 1
        for term in commit["terms"]:
            term_counts[term] += 1
            if len(term_subjects[term]) < 3:
                term_subjects[term].append(commit["subject"])
        if commit["keywords"]:
            keyword_hits.append(
                {
                    "hash": commit["short_hash"],
                    "date": commit["date"],
                    "subject": commit["subject"],
                    "keywords": commit["keywords"],
                    "paths": commit["paths"][:12],
                }
            )
        unique_paths = sorted(set(commit["paths"]))
        if 2 <= len(unique_paths) <= 20:
            for left, right in itertools.combinations(unique_paths[:12], 2):
                pair = (left, right)
                pair_counts[pair] += 1
                if len(pair_examples[pair]) < 2:
                    pair_examples[pair].append(
                        {"hash": commit["short_hash"], "subject": commit["subject"]}
                    )

    cochange_groups = [
        {
            "paths": list(pair),
            "commit_count": count,
            "sample_commits": pair_examples[pair],
        }
        for pair, count in pair_counts.most_common(max_items)
        if count >= 2
    ]

    term_candidates = [
        {
            "term": term,
            "count": count,
            "sample_subjects": term_subjects[term],
        }
        for term, count in term_counts.most_common(max_items)
        if count >= 1
    ]

    qa_prompts: list[str] = []
    if term_candidates:
        top_terms = ", ".join(item["term"] for item in term_candidates[:5])
        qa_prompts.append(
            f"Git history uses these names: {top_terms}. Do they match current code/table/API names for the same concept? Which term should the final docs standardize on?"
        )
    for hit in keyword_hits[:5]:
        qa_prompts.append(
            f"Commit {hit['hash']} mentions 「{hit['subject']}」. Do matching compatibility/fix constraints still apply? What must AI preserve when changing related code?"
        )

    domain_path_summaries = []
    for path_filter in paths:
        matched = [
            commit
            for commit in commits
            if any(path == path_filter or path.startswith(path_filter.rstrip("/") + "/") for path in commit["paths"])
        ]
        domain_path_summaries.append(
            {
                "path": path_filter,
                "commit_count": len(matched),
                "keyword_hit_count": sum(1 for commit in matched if commit["keywords"]),
                "recent_subjects": [
                    {
                        "hash": commit["short_hash"],
                        "date": commit["date"],
                        "subject": commit["subject"],
                    }
                    for commit in matched[:8]
                ],
            }
        )

    return {
        "hot_paths": [
            {"path": path, "commit_count": count}
            for path, count in file_counts.most_common(max_items)
        ],
        "hot_directories": [
            {"path": path, "commit_count": count}
            for path, count in dir_counts.most_common(max_items)
        ],
        "keyword_hits": keyword_hits[: max_items * 2],
        "cochange_groups": cochange_groups,
        "term_candidates": term_candidates,
        "domain_path_summaries": domain_path_summaries,
        "qa_prompts": qa_prompts[: max_items],
    }


def unavailable(root: Path, reason: str, max_commits: int, paths: list[str]) -> dict[str, Any]:
    return {
        "scan": {
            "root": str(root),
            "generated_at": now_iso(),
            "git_available": False,
            "status": reason,
            "max_commits": max_commits,
            "paths_filter": paths,
            "scanned_commits": 0,
        },
        "weak_signal_policy": "Git history is a high-noise weak signal; use only for hotspots, historical names, and Q&A leads.",
        "hot_paths": [],
        "hot_directories": [],
        "keyword_hits": [],
        "cochange_groups": [],
        "term_candidates": [],
        "domain_path_summaries": [],
        "qa_prompts": [],
        "notes": [reason],
    }


def empty_history(root: Path, reason: str, max_commits: int, paths: list[str], shallow: bool | None) -> dict[str, Any]:
    report = unavailable(root, "Git history empty or no commits after path filter", max_commits, paths)
    report["scan"]["git_available"] = True
    report["scan"]["status"] = "Git history empty or no commits after path filter"
    report["scan"]["shallow_repository"] = shallow
    report["notes"] = [reason]
    return report


def build_report(root: Path, max_commits: int, paths: list[str], max_items: int) -> dict[str, Any]:
    root = root.resolve()
    inside = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return unavailable(root, "current directory is not a Git work tree", max_commits, paths)

    shallow_proc = run_git(root, ["rev-parse", "--is-shallow-repository"])
    shallow = shallow_proc.stdout.strip() == "true" if shallow_proc.returncode == 0 else None

    effective_paths = paths or default_paths_for_root(root)
    commits, error = load_commits(root, max_commits, effective_paths)
    if error:
        if "does not have any commits yet" in error or "尚无提交" in error:
            return empty_history(root, error, max_commits, paths, shallow)
        return unavailable(root, error, max_commits, paths)
    if not commits:
        return empty_history(root, "Git history empty or no commits after path filter", max_commits, paths, shallow)

    summary = summarize(commits, paths, max_items)
    notes = [
        "Git history is a weak signal only; do not write it alone as current business rules.",
    ]
    if shallow:
        notes.append("Repository is a shallow clone; Git weak-signal coverage is incomplete.")

    return {
        "scan": {
            "root": str(root),
            "generated_at": now_iso(),
            "git_available": True,
            "status": "ok",
            "shallow_repository": shallow,
            "max_commits": max_commits,
            "paths_filter": paths,
            "effective_paths_filter": effective_paths,
            "scanned_commits": len(commits),
        },
        "weak_signal_policy": "Git history is a high-noise weak signal; use only for hotspots, historical names, and Q&A leads; promote into KB/Guide only after code/DB/runtime or user confirmation.",
        **summary,
        "notes": notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lightweight Git-history weak-signal miner")
    parser.add_argument("--root", default=".", help="project root (default: cwd)")
    parser.add_argument("--max-commits", type=int, default=300, help="max recent commits to scan (default 300)")
    parser.add_argument("--max-items", type=int, default=20, help="max summary items per category (default 20)")
    parser.add_argument("--paths", nargs="*", default=[], help="optional: only scan these paths")
    parser.add_argument("--output", help="output JSON path; default stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(Path(args.root), args.max_commits, args.paths, args.max_items)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
