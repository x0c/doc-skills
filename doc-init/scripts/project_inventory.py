#!/usr/bin/env python3
"""
Scan project structure and emit mechanical facts for doc-init Phase 2.

Collects candidate facts only — does not decide business domains or write long-lived docs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


IGNORE_DIRS = {
    ".git",
    ".build",
    ".doc-init-dd",
    ".idea",
    ".vscode",
    ".claude",
    ".agents",
    ".codex",
    ".codegraph",
    ".gradle",
    ".mvn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "target",
    "build",
    "dist",
    "out",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
}

IGNORE_PATH_PARTS = {
    (".cache",),
}

BUILD_MARKERS = {
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "settings.gradle": "gradle",
    "settings.gradle.kts": "gradle",
    "package.json": "node",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "composer.json": "php",
    "Gemfile": "ruby",
    "Directory.Build.props": "dotnet",
}

LANG_EXTS = {
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".py": "Python",
    ".go": "Go",
    ".cs": "C#/.NET",
    ".fs": "F#/.NET",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".cpp": "C/C++",
    ".cc": "C/C++",
    ".cxx": "C/C++",
    ".c": "C/C++",
    ".h": "C/C++",
    ".hpp": "C/C++",
}

HIDDEN_REF_BY_LANG = {
    "Java": "references/hidden-semantics/java-kotlin.md",
    "Kotlin": "references/hidden-semantics/java-kotlin.md",
    "JavaScript": "references/hidden-semantics/javascript-typescript.md",
    "TypeScript": "references/hidden-semantics/javascript-typescript.md",
    "Python": "references/hidden-semantics/python.md",
    "Go": "references/hidden-semantics/go.md",
    "C#/.NET": "references/hidden-semantics/csharp-dotnet.md",
    "F#/.NET": "references/hidden-semantics/csharp-dotnet.md",
}

ENTRY_NAME_PATTERNS = [
    ("controller", re.compile(r"(controller|resource|endpoint)", re.I)),
    ("service", re.compile(r"(service|facade|manager|usecase|interactor)", re.I)),
    ("component", re.compile(r"(component|processor|executor|plugin|extension)", re.I)),
    ("flow", re.compile(r"(flow|workflow|process|pipeline|node)", re.I)),
    ("job", re.compile(r"(job|task|scheduler|cron|runner)", re.I)),
    ("event", re.compile(r"(listener|consumer|producer|subscriber|handler|event)", re.I)),
    ("middleware", re.compile(r"(middleware|interceptor|filter|guard|aspect|decorator)", re.I)),
    ("data", re.compile(r"(mapper|repository|dao|entity|model|schema|migration)", re.I)),
    ("config", re.compile(r"(config|settings|properties|profile)", re.I)),
]

CONFIG_EXTS = {
    ".yml",
    ".yaml",
    ".properties",
    ".toml",
    ".ini",
    ".env",
    ".json",
    ".xml",
}

EVIDENCE_LIMIT_PER_KIND = 80

EVIDENCE_KIND_LABELS = {
    "tests": "tests / fixtures / mocks",
    "api_contracts": "API contracts",
    "frontend": "frontend / pages / menus",
    "config_runtime": "config / environment",
    "ci_cd": "CI/CD / deploy / startup scripts",
    "logs_metrics": "logs / metrics / alerts",
    "ddl_migrations_seed": "DDL / migrations / seed",
    "external_contracts": "MQ / webhook / third-party contracts",
    "permissions_dictionary": "permissions / menus / dictionaries / enum config",
    "generated_metadata": "generated code / metadata / flow config",
    "runtime_validation": "runtime validation entry points",
}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def has_path_parts(path: Path, parts: tuple[str, ...]) -> bool:
    value = tuple(path.parts)
    if not parts:
        return False
    for idx in range(0, len(value) - len(parts) + 1):
        if value[idx : idx + len(parts)] == parts:
            return True
    return False


def should_skip_path(path: Path) -> bool:
    if path.name in IGNORE_DIRS:
        return True
    return any(has_path_parts(path, parts) for parts in IGNORE_PATH_PARTS)


def iter_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = [
            d
            for d in dirs
            if not should_skip_path(current_path / d) and not d.startswith(".cache")
        ]
        dirs.sort()
        for name in sorted(names):
            path = Path(current) / name
            if should_skip_path(path):
                continue
            files.append(path)
            if len(files) >= max_files:
                return files
    return files


def read_small_text(path: Path, max_bytes: int = 200_000) -> str:
    try:
        data = path.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except OSError:
        return ""


def detect_modules(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    seen: set[str] = set()

    for path in files:
        name = path.name
        text = ""
        if name == "pom.xml":
            text = read_small_text(path)
            for item in re.findall(r"<module>\s*([^<]+?)\s*</module>", text):
                module_path = (path.parent / item.strip()).resolve()
                if module_path.exists():
                    value = rel(module_path, root)
                    if value not in seen:
                        modules.append({"path": value, "source": rel(path, root), "kind": "maven-module"})
                        seen.add(value)
        elif name in {"settings.gradle", "settings.gradle.kts"}:
            text = read_small_text(path)
            for item in re.findall(r"include\s*\(?\s*['\"]([^'\"]+)['\"]", text):
                value = item.strip().replace(":", "/").strip("/")
                module_path = (path.parent / value).resolve()
                if value and module_path.exists() and value not in seen:
                    modules.append({"path": value, "source": rel(path, root), "kind": "gradle-module"})
                    seen.add(value)
        elif name.endswith(".sln"):
            text = read_small_text(path)
            for item in re.findall(r"Project\([^)]*\)\s*=\s*\"[^\"]+\",\s*\"([^\"]+\.(?:csproj|fsproj))\"", text):
                module_path = (path.parent / item.replace("\\", "/")).resolve().parent
                if module_path.exists():
                    value = rel(module_path, root)
                    if value not in seen:
                        modules.append({"path": value, "source": rel(path, root), "kind": "dotnet-project"})
                        seen.add(value)

    if not modules:
        for path in files:
            if path.name in BUILD_MARKERS and path.parent != root:
                value = rel(path.parent, root)
                if value not in seen:
                    modules.append({"path": value, "source": rel(path, root), "kind": "build-file-directory"})
                    seen.add(value)

    return modules[:200]


def classify_entry(path: Path) -> str | None:
    stem = path.stem
    text_path = path.as_posix()
    for kind, pattern in ENTRY_NAME_PATTERNS:
        if pattern.search(stem) or pattern.search(text_path):
            return kind
    return None


def add_evidence(
    evidence: dict[str, list[dict[str, str]]],
    kind: str,
    path_rel: str,
    reason: str,
) -> None:
    values = evidence[kind]
    if len(values) >= EVIDENCE_LIMIT_PER_KIND:
        return
    if any(item["path"] == path_rel for item in values):
        return
    values.append({"path": path_rel, "reason": reason})


def classify_evidence(path: Path, root: Path, evidence: dict[str, list[dict[str, str]]]) -> None:
    path_rel = rel(path, root)
    lower_path = path_rel.lower()
    name = path.name
    lower_name = name.lower()
    suffix = path.suffix.lower()
    parts = {part.lower() for part in path.parts}

    if (
        "test" in parts
        or "tests" in parts
        or "__tests__" in parts
        or re.search(r"(^|[-_.])(test|spec|fixture|fixtures|mock|mocks)([-_.]|$)", lower_name)
    ) and not lower_name.startswith("appsettings."):
        add_evidence(evidence, "tests", path_rel, "path or filename looks like a test, fixture, or mock")

    if (
        suffix in {".proto", ".graphql", ".gql"}
        or "openapi" in lower_name
        or "swagger" in lower_name
        or "asyncapi" in lower_name
        or "postman" in lower_name
        or lower_name.endswith("-docs.json")
        or "api-docs" in lower_name
    ):
        add_evidence(evidence, "api_contracts", path_rel, "filename or extension looks like an API contract")

    if (
        suffix in {".vue", ".svelte", ".tsx", ".jsx", ".html"}
        or "frontend" in lower_path
        or "webapp" in lower_path
        or "/pages/" in lower_path
        or "/views/" in lower_path
        or "/router/" in lower_path
        or "/routes/" in lower_path
        or "/menus/" in lower_path
    ):
        add_evidence(evidence, "frontend", path_rel, "path or extension looks like frontend page, route, or menu")

    if (
        suffix in CONFIG_EXTS
        or lower_name in {"dockerfile", "makefile", "procfile"}
        or lower_name.startswith("application")
        or lower_name.startswith("appsettings")
        or lower_name.startswith(".env")
    ):
        add_evidence(evidence, "config_runtime", path_rel, "config, environment, or runtime parameter candidate")

    if (
        ".github/workflows/" in lower_path
        or "jenkinsfile" == lower_name
        or lower_name == "dockerfile"
        or lower_name.startswith("docker-compose")
        or "/helm/" in lower_path
        or "/k8s/" in lower_path
        or "/kubernetes/" in lower_path
        or lower_name in {"makefile", "procfile"}
    ):
        add_evidence(evidence, "ci_cd", path_rel, "CI/CD, deploy, or startup script candidate")

    if (
        "log4j" in lower_name
        or "logback" in lower_name
        or "prometheus" in lower_path
        or "grafana" in lower_path
        or "alert" in lower_path
        or "metrics" in lower_path
        or "tracing" in lower_path
        or "arthas" in lower_path
    ):
        add_evidence(evidence, "logs_metrics", path_rel, "logs, metrics, alerts, or tracing candidate")

    if (
        suffix == ".sql"
        or "migration" in lower_path
        or "migrations" in lower_path
        or "flyway" in lower_path
        or "liquibase" in lower_path
        or "seed" in lower_path
        or "初始化" in path_rel
        or "数据库变更" in path_rel
    ):
        add_evidence(evidence, "ddl_migrations_seed", path_rel, "DDL, migration, seed, or init-data candidate")

    if (
        "mq" in lower_path
        or "rabbit" in lower_path
        or "kafka" in lower_path
        or "topic" in lower_path
        or "webhook" in lower_path
        or "callback" in lower_path
        or "provider" in lower_path
        or lower_path.endswith("sdk")
        or "/sdk/" in lower_path
        or suffix in {".proto", ".graphql", ".gql"}
    ):
        add_evidence(evidence, "external_contracts", path_rel, "messaging, callback, SDK, or external-contract candidate")

    if (
        "permission" in lower_path
        or "auth" in lower_path
        or "role" in lower_path
        or "menu" in lower_path
        or "dict" in lower_path
        or "dictionary" in lower_path
        or "enum" in lower_path
        or "字典" in path_rel
        or "菜单" in path_rel
        or "权限" in path_rel
    ):
        add_evidence(evidence, "permissions_dictionary", path_rel, "permission, menu, dictionary, or enum candidate")

    if (
        "pdman" in lower_name
        or "schema" in lower_name
        or "generator" in lower_path
        or "generated" in lower_path
        or "codegen" in lower_path
        or suffix in {".bpmn", ".puml", ".proto", ".graphql", ".gql"}
        or "flow" in lower_path
        or "workflow" in lower_path
        or "规则" in path_rel
    ):
        add_evidence(evidence, "generated_metadata", path_rel, "generated code, metadata, flow, or rule-config candidate")

    if (
        name in BUILD_MARKERS
        or lower_name.endswith(".sln")
        or lower_name.endswith(".csproj")
        or lower_name.endswith(".fsproj")
        or lower_name in {"readme.md", "readme", "makefile", "procfile"}
        or "local-debug" in lower_name
        or "启动" in path_rel
        or "验证" in path_rel
    ):
        add_evidence(evidence, "runtime_validation", path_rel, "build, startup, validation, or local-debug entry candidate")


def collect_inventory(root: Path, max_files: int) -> dict[str, Any]:
    files = iter_files(root, max_files)
    ext_counter: Counter[str] = Counter()
    lang_counter: Counter[str] = Counter()
    build_files: list[dict[str, str]] = []
    docs: list[str] = []
    configs: list[str] = []
    entries_by_kind: dict[str, list[str]] = defaultdict(list)
    evidence_sources: dict[str, list[dict[str, str]]] = defaultdict(list)

    for path in files:
        suffix = path.suffix.lower()
        if suffix:
            ext_counter[suffix] += 1
        if suffix in LANG_EXTS:
            lang_counter[LANG_EXTS[suffix]] += 1

        name = path.name
        path_rel = rel(path, root)
        if name in BUILD_MARKERS or name.endswith(".sln") or name.endswith(".csproj") or name.endswith(".fsproj"):
            build_files.append({"path": path_rel, "kind": BUILD_MARKERS.get(name, "dotnet")})
        if suffix == ".md" or name.upper() in {"README", "AGENTS.MD", "CLAUDE.MD"}:
            docs.append(path_rel)
        if suffix in CONFIG_EXTS or name in {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile", "Procfile"}:
            configs.append(path_rel)

        classify_evidence(path, root, evidence_sources)

        entry_kind = classify_entry(path)
        if entry_kind and suffix in LANG_EXTS:
            entries_by_kind[entry_kind].append(path_rel)

    languages = [{"language": name, "file_count": count} for name, count in lang_counter.most_common()]
    hidden_refs = sorted({HIDDEN_REF_BY_LANG[name] for name in lang_counter if name in HIDDEN_REF_BY_LANG})

    return {
        "root": str(root),
        "scan": {
            "max_files": max_files,
            "scanned_files": len(files),
            "truncated": len(files) >= max_files,
        },
        "languages": languages,
        "build_files": build_files[:200],
        "submodules": detect_modules(root, files),
        "existing_docs": sorted(docs)[:300],
        "config_candidates": sorted(configs)[:300],
        "entry_candidates": {kind: sorted(values)[:120] for kind, values in sorted(entries_by_kind.items())},
        "evidence_sources": {
            kind: {
                "label": EVIDENCE_KIND_LABELS.get(kind, kind),
                "items": sorted(values, key=lambda item: item["path"])[:EVIDENCE_LIMIT_PER_KIND],
            }
            for kind, values in sorted(evidence_sources.items())
        },
        "extension_summary": [{"extension": k, "count": v} for k, v in ext_counter.most_common(30)],
        "recommended_hidden_semantics_refs": hidden_refs,
        "depth_scanner_hint": "run depth_scanner.py --inventory <this file> for state-machine/concurrency/event/component deep candidates",
        "notes": [
            "This report is mechanical candidate facts only; domain boundaries still need Agent judgment with code, materials, DB, and user input.",
            "entry_candidates are filename/path heuristics and may include false positives/negatives.",
            "Deep extraction (status enums / concurrency / events / components) is done separately by depth_scanner.py.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit doc-init project-structure candidate facts")
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--max-files", type=int, default=8000, help="max files to scan")
    parser.add_argument("--output", help="output JSON file; default stdout")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: project root does not exist or is not a directory: {root}")
        return 2

    data = collect_inventory(root, args.max_files)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
