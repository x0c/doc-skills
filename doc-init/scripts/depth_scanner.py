#!/usr/bin/env python3
"""
doc-init deep knowledge extraction.

Reads project_inventory.py inventory JSON and mechanically extracts patterns
for the detected language stack (no business judgment):
  - status enums (status_patterns)
  - concurrency control (concurrency_patterns)
  - events/messaging (event_patterns)
  - framework component registration (framework_components)
  - soft-delete markers (soft_delete_patterns)
  - idempotency markers (idempotency_patterns)
  - runnable project metadata (runnable_project)
  - hot files (hot_files)

Usage:
  python3 depth_scanner.py --root <project_root> --inventory <inventory.json> --output <depth_scan.json>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Skip dirs (keep in sync with project_inventory.py)
# ---------------------------------------------------------------------------
IGNORE_DIRS = {
    ".git",
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
    "vendor",
}

# Large files: read only the first N lines
LARGE_FILE_LINE_LIMIT = 500
LARGE_FILE_BYTE_LIMIT = 100 * 1024  # 100 KB

# Cap results per category to keep output bounded
RESULT_LIMIT = 200

# Total runtime budget (seconds)
TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# Multi-language regex pattern config
# ---------------------------------------------------------------------------

# Per language-family pattern dict; keys match output field names
# value is (compiled_pattern, purpose description)
LANG_PATTERNS: dict[str, dict[str, list[tuple[re.Pattern[str], str]]]] = {
    "java_kotlin": {
        "status": [
            (re.compile(r"enum\s+\w*(?:Status|State)\w*", re.I), "Java/Kotlin status enum"),
        ],
        "concurrency": [
            (re.compile(r"@Version\b"), "JPA/Hibernate optimistic lock @Version"),
            (re.compile(r"synchronized\s*\(|ReentrantLock|StampedLock"), "Java explicit lock"),
        ],
        "event": [
            (re.compile(r"class\s+\w+Event\b"), "event class definition"),
            (re.compile(r"@(?:EventListener|TransactionalEventListener)\b"), "Spring event listener"),
            (re.compile(r"publishEvent\s*\(|applicationEventPublisher\.publish", re.I), "Spring event publish"),
            (re.compile(r"@(?:RabbitListener|KafkaListener)\b"), "MQ listener annotation"),
        ],
        "component": [
            (re.compile(r'@LiteflowComponent\s*\('), "LiteFlow component registration"),
            (re.compile(r'@(?:Component|Service|Controller|RestController)\s*\(\s*(?:value\s*=\s*)?["\']'), "Spring named Bean"),
            (re.compile(r"@Scheduled\b"), "Spring scheduled task"),
        ],
        "idempotency": [
            (re.compile(r"idempotent|dedup|idempotentId|timingIdempotentId", re.I), "idempotency field/marker"),
        ],
        "soft_delete": [
            (re.compile(r"biz_status|is_deleted|deleted_at|isDeleted", re.I), "soft-delete field"),
            (re.compile(r"\.ne\s*\(.*?DELETED", re.I), "MyBatis-Plus ne(DELETED) query"),
        ],
        "sharding": [
            (re.compile(r"BusinessContextHolder|ShardingContext", re.I), "sharding context holder"),
            (re.compile(r"@TableName\s*\("), "MyBatis-Plus @TableName"),
        ],
    },
    "python": {
        "status": [
            (re.compile(r"class\s+\w*(?:Status|State)\s*[\w(,\s]*(?:Enum|IntEnum)\b"), "Python status enum"),
            (re.compile(r"STATUS_CHOICES\s*="), "Django choices pattern"),
        ],
        "concurrency": [
            (re.compile(r"version_id|_version\b|select_for_update\s*\("), "Python ORM optimistic lock"),
        ],
        "event": [
            (re.compile(r"signal\.\w+\.connect|@receiver\s*\("), "Django signal"),
            (re.compile(r"celery\.task|@app\.task|@shared_task"), "Celery task"),
            (re.compile(r"publish_event|event_bus\.publish", re.I), "event-bus publish"),
        ],
        "component": [
            (re.compile(r"@app\.route\s*\(|@router\."), "Flask/FastAPI route"),
            (re.compile(r"@dramatiq\.actor|@celery\.task"), "Dramatiq/Celery Actor"),
        ],
        "idempotency": [
            (re.compile(r"idempotency_key|get_or_create\s*\(", re.I), "idempotency key / get_or_create"),
            (re.compile(r"ON CONFLICT", re.I), "SQL ON CONFLICT idempotency"),
        ],
        "soft_delete": [
            (re.compile(r"is_deleted|deleted_at|SoftDeletable"), "Python soft-delete field"),
            (re.compile(r"objects\.filter.*\.exclude.*deleted", re.I), "Django soft-delete query"),
        ],
        "sharding": [
            (re.compile(r"tenant_id|schema_name|connection\.set_schema", re.I), "multi-tenant / DB-routing"),
        ],
    },
    "typescript_javascript": {
        "status": [
            (re.compile(r"enum\s+\w*Status\b"), "TS status enum"),
            (re.compile(r"type\s+\w*Status\s*=|Status\s*=\s*\{"), "TS union type / object status"),
        ],
        "concurrency": [
            (re.compile(r"@VersionColumn\(\)|version.*:\s*number", re.I), "TypeORM optimistic lock"),
            (re.compile(r"optimisticLock|_version\b", re.I), "optimistic-lock marker"),
        ],
        "event": [
            (re.compile(r"EventEmitter|\.emit\s*\(|\.on\s*\("), "Node.js EventEmitter"),
            (re.compile(r"@OnEvent\s*\(|pubSub\.publish|eventBus\.emit", re.I), "event publish/subscribe"),
        ],
        "component": [
            (re.compile(r"@(?:Controller|Injectable|Module)\s*\("), "NestJS decorator"),
            (re.compile(r'app\.(?:get|post|put|delete|patch)\s*\(|router\.(?:get|post|put)'), "Express/Koa route"),
        ],
        "idempotency": [
            (re.compile(r"idempotencyKey|idempotent|upsert\s*\(", re.I), "idempotency key / upsert"),
            (re.compile(r"ON CONFLICT", re.I), "SQL ON CONFLICT"),
        ],
        "soft_delete": [
            (re.compile(r"deletedAt|isDeleted|@DeleteDateColumn", re.I), "TS soft-delete field"),
            (re.compile(r"withDeleted\s*\(\)", re.I), "TypeORM withDeleted"),
        ],
        "sharding": [
            (re.compile(r"tenantId|cls\.schema|setSchema|multiTenancy", re.I), "multi-tenant / DB-routing"),
        ],
    },
    "go": {
        "status": [
            (re.compile(r"Status\w+\s+(?:int|string)|State\w+\s+(?:int|string)"), "Go status constant type"),
            (re.compile(r"iota.*(?:Status|State)", re.I), "Go iota status enum"),
            (re.compile(r"type\s+\w*Status\s+(?:int|string)\b"), "Go named status type"),
        ],
        "concurrency": [
            (re.compile(r"version\s+(?:int|int64)|Version\s+(?:int|int64)"), "Go version optimistic lock"),
            (re.compile(r"sync\.Mutex|sync\.RWMutex|atomic\."), "Go sync primitive"),
            (re.compile(r"\.CAS\s*\(|compare_and_swap", re.I), "CAS operation"),
        ],
        "event": [
            (re.compile(r"chan\s+\w*Event"), "Go channel event"),
            (re.compile(r"\.Publish\s*\(|\.Subscribe\s*\("), "publish/subscribe call"),
            (re.compile(r"nats\.Conn|amqp\.Channel"), "NATS/AMQP"),
        ],
        "component": [
            (re.compile(r"func\s+init\s*\(\s*\)"), "Go init registration"),
            (re.compile(r"http\.Handle\s*\(|mux\.Handle\s*\("), "Go HTTP route"),
            (re.compile(r'gin\.(?:GET|POST|PUT|DELETE)\s*\(|echo\.(?:GET|POST)'), "Gin/Echo route"),
        ],
        "idempotency": [
            (re.compile(r"idempotent|SetNX\s*\(|setnx\b", re.I), "Redis SetNX idempotency"),
            (re.compile(r"InsertOrUpdate|UPSERT\b", re.I), "Upsert idempotency"),
        ],
        "soft_delete": [
            (re.compile(r"deleted_at|IsDeleted|gorm\.DeletedAt"), "GORM soft delete"),
            (re.compile(r"Unscoped\s*\(\)"), "GORM Unscoped"),
        ],
        "sharding": [
            (re.compile(r"context\.Value\s*\(|WithValue.*tenant", re.I), "context shard routing"),
            (re.compile(r"shardKey|partition\b", re.I), "shard key"),
        ],
    },
    "csharp_dotnet": {
        "status": [
            (re.compile(r"enum\s+\w*(?:Status|State)\b"), "C# status enum"),
            (re.compile(r"\[Flags\]\s*\n\s*enum\b"), "C# Flags enum"),
        ],
        "concurrency": [
            (re.compile(r"\[ConcurrencyCheck\]|\[Timestamp\]|IsRowVersion\s*\("), "EF Core concurrency marker"),
            (re.compile(r"Interlocked\.|Monitor\.Enter|SemaphoreSlim"), ".NET concurrency primitive"),
        ],
        "event": [
            (re.compile(r"INotification\b|IMediator\b"), "MediatR event/command"),
            (re.compile(r"\.Publish\s*\(|DomainEvent\b|EventHandler\b"), "domain event"),
        ],
        "component": [
            (re.compile(r"\[(?:ApiController|HttpGet|HttpPost|HttpPut|HttpDelete)\]"), "ASP.NET Controller"),
            (re.compile(r"services\.Add|builder\.Services\.Add"), ".NET DI registration"),
        ],
        "idempotency": [
            (re.compile(r"IdempotencyKey|idempotent", re.I), "idempotency key"),
            (re.compile(r"MERGE\s+INTO|ExecuteUpdateOrInsert", re.I), "Upsert statement"),
        ],
        "soft_delete": [
            (re.compile(r"IsDeleted|DeletedAt|ISoftDelete\b"), "C# soft-delete interface/field"),
            (re.compile(r"HasQueryFilter.*!.*[Ii]s[Dd]eleted"), "EF Core global filter"),
        ],
        "sharding": [
            (re.compile(r"ITenantProvider|TenantId|UseDatabasePerTenant", re.I), "multi-tenant routing"),
            (re.compile(r"IMultiTenantDbContext"), "multi-tenant DbContext"),
        ],
    },
}

# Language label → pattern-family map (from project_inventory.py language field)
LANG_TO_PATTERN_KEY: dict[str, str] = {
    "Java": "java_kotlin",
    "Kotlin": "java_kotlin",
    "Python": "python",
    "TypeScript": "typescript_javascript",
    "JavaScript": "typescript_javascript",
    "Go": "go",
    "C#/.NET": "csharp_dotnet",
    "F#/.NET": "csharp_dotnet",
}

# File extension → language label
EXT_TO_LANG: dict[str, str] = {
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".cs": "C#/.NET",
    ".fs": "F#/.NET",
}


# ---------------------------------------------------------------------------
# Status enum value extraction (shared across Java/Kotlin/Go/C#/Python/TS)
# ---------------------------------------------------------------------------

# Match enum block { ... }; only first 2000 chars to avoid cross-block matches
_ENUM_BODY_RE = re.compile(r"\{([^{}]{0,2000})\}", re.S)
# Enum values: ALL_CAPS underscore / SCREAMING_SNAKE + optional parens
_ENUM_VALUE_RE = re.compile(r"\b([A-Z][A-Z0-9_]{1,40})\b")


def extract_enum_values(text: str, start: int) -> list[str]:
    """Extract enum value list after start (at most first 20 ALL_CAPS members)."""
    fragment = text[start : start + 2000]
    m = _ENUM_BODY_RE.search(fragment)
    if not m:
        return []
    body = m.group(1)
    values = _ENUM_VALUE_RE.findall(body)
    # Filter Java keywords and similar noise
    stop_words = {"NULL", "TRUE", "FALSE", "VOID", "INT", "LONG", "STRING", "BYTE"}
    return [v for v in values if v not in stop_words][:20]


# ---------------------------------------------------------------------------
# File iteration
# ---------------------------------------------------------------------------

def iter_source_files(root: Path, active_exts: set[str]) -> list[Path]:
    """Walk source files, skip ignore dirs, return only extensions in active_exts."""
    result: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".cache"))
        for name in sorted(names):
            ext = Path(name).suffix.lower()
            if ext in active_exts:
                result.append(Path(current) / name)
    return result


def read_file_lines(path: Path) -> list[str]:
    """Read a file; large files only the first LARGE_FILE_LINE_LIMIT lines."""
    try:
        size = path.stat().st_size
        if size > LARGE_FILE_BYTE_LIMIT:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                return [fh.readline() for _ in range(LARGE_FILE_LINE_LIMIT)]
        return path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    except OSError as e:
        warnings.warn(f"skip file {path}: {e}")
        return []


def read_file_text(path: Path) -> str:
    return "".join(read_file_lines(path))


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


# ---------------------------------------------------------------------------
# Pattern scans by category
# ---------------------------------------------------------------------------

def scan_status_patterns(
    path: Path, root: Path, text: str, lang_key: str, results: list[dict[str, Any]]
) -> None:
    if len(results) >= RESULT_LIMIT:
        return
    patterns = LANG_PATTERNS.get(lang_key, {}).get("status", [])
    for pattern, _ in patterns:
        for m in pattern.finditer(text):
            values = extract_enum_values(text, m.end())
            results.append({
                "file": rel(path, root),
                "name": m.group(0).strip(),
                "values": values,
                "type": "enum",
            })
            if len(results) >= RESULT_LIMIT:
                return


def scan_concurrency_patterns(
    path: Path, root: Path, text: str, lang_key: str, results: list[dict[str, Any]]
) -> None:
    if len(results) >= RESULT_LIMIT:
        return
    patterns = LANG_PATTERNS.get(lang_key, {}).get("concurrency", [])
    # Extract field name near @Version (Java)
    field_re = re.compile(r"(?:private|protected|public|var|val)\s+\S+\s+(\w+)\s*;")
    for pattern, signal in patterns:
        for m in pattern.finditer(text):
            # Try to extract nearby field name
            nearby = text[m.start(): m.start() + 200]
            fm = field_re.search(nearby)
            field = fm.group(1) if fm else ""
            results.append({
                "file": rel(path, root),
                "type": "optimistic_lock" if "Version" in signal or "version" in signal else "lock",
                "field": field,
                "signal": m.group(0).strip()[:80],
            })
            if len(results) >= RESULT_LIMIT:
                return


def scan_event_patterns(
    path: Path, root: Path, text: str, lang_key: str, publishers: list[dict[str, Any]]
) -> None:
    if len(publishers) >= RESULT_LIMIT:
        return
    patterns = LANG_PATTERNS.get(lang_key, {}).get("event", [])
    # Extract event class name (simple: class XxxEvent or publishEvent(new XxxEvent))
    event_name_re = re.compile(r"(?:class\s+(\w+Event\b)|publish\w*\s*\(\s*(?:new\s+)?(\w+Event)\b)", re.I)
    for pattern, _ in patterns:
        for m in pattern.finditer(text):
            en_match = event_name_re.search(text[max(0, m.start()-50): m.end()+100])
            event_name = ""
            if en_match:
                event_name = en_match.group(1) or en_match.group(2) or ""
            publishers.append({
                "publisher_file": rel(path, root),
                "event_name": event_name,
                "subscriber_file": "",  # cross-file link left empty for LLM stage
                "signal": m.group(0).strip()[:80],
            })
            if len(publishers) >= RESULT_LIMIT:
                return


def scan_framework_components(
    path: Path, root: Path, text: str, lang_key: str, results: list[dict[str, Any]]
) -> None:
    if len(results) >= RESULT_LIMIT:
        return
    patterns = LANG_PATTERNS.get(lang_key, {}).get("component", [])
    # LiteFlow component ID extraction
    liteflow_id_re = re.compile(r'@LiteflowComponent\s*\(\s*(?:id\s*=\s*)?["\']([^"\']+)["\'](?:\s*,\s*name\s*=\s*["\']([^"\']+)["\'])?')
    for pattern, comp_type in patterns:
        for m in pattern.finditer(text):
            comp_id = ""
            comp_name = ""
            if "LiteFlow" in comp_type or "liteflow" in comp_type.lower():
                lm = liteflow_id_re.search(text[m.start(): m.start() + 200])
                if lm:
                    comp_id = lm.group(1) or ""
                    comp_name = lm.group(2) or ""
            results.append({
                "file": rel(path, root),
                "type": "liteflow_component" if comp_id else comp_type.lower().replace(" ", "_"),
                "id": comp_id,
                "name": comp_name,
                "signal": m.group(0).strip()[:80],
            })
            if len(results) >= RESULT_LIMIT:
                return


def scan_soft_delete(
    path: Path, root: Path, text: str, lang_key: str, results: list[dict[str, Any]]
) -> None:
    if len(results) >= RESULT_LIMIT:
        return
    patterns = LANG_PATTERNS.get(lang_key, {}).get("soft_delete", [])
    for pattern, _ in patterns:
        if pattern.search(text):
            # Extract first matching field name
            m = pattern.search(text)
            results.append({
                "file": rel(path, root),
                "field": m.group(0).strip()[:60] if m else "",
                "signal": m.group(0).strip()[:80] if m else "",
            })
            return  # record once per file


def scan_idempotency(
    path: Path, root: Path, text: str, lang_key: str, results: list[dict[str, Any]]
) -> None:
    if len(results) >= RESULT_LIMIT:
        return
    patterns = LANG_PATTERNS.get(lang_key, {}).get("idempotency", [])
    for pattern, _ in patterns:
        m = pattern.search(text)
        if m:
            results.append({
                "file": rel(path, root),
                "key_field": m.group(0).strip()[:60],
                "signal": m.group(0).strip()[:80],
            })
            return  # record once per file


# ---------------------------------------------------------------------------
# Runnable project detection
# ---------------------------------------------------------------------------

def _is_ignored_path(path: Path) -> bool:
    """True if path contains a directory segment that should be skipped."""
    for part in path.parts:
        if part in IGNORE_DIRS:
            return True
    return False


def _rglob_filtered(base: Path, pattern: str) -> list[Path]:
    """rglob variant that skips IGNORE_DIRS subtrees."""
    return [p for p in base.rglob(pattern) if not _is_ignored_path(p)]


def detect_runnable_project(root: Path) -> dict[str, Any]:
    """Detect project type, ports, start command, and log paths."""
    result: dict[str, Any] = {
        "type": "unknown",
        "ports": [],
        "start_commands": [],
        "log_paths": [],
    }

    def read_text_safe(p: Path) -> str:
        try:
            return p.read_text(encoding="utf-8", errors="ignore")[:50000]
        except OSError:
            return ""

    # Spring Boot
    for pom in _rglob_filtered(root, "pom.xml"):
        if pom.stat().st_size == 0:
            continue
        text = read_text_safe(pom)
        if "spring-boot-maven-plugin" in text or "spring-boot-starter" in text:
            result["type"] = "spring-boot"
            module_dir = pom.parent
            # Ports: scan application*.properties / application*.yml (skip target/)
            for prop_path in _rglob_filtered(module_dir, "application*.properties"):
                prop_text = read_text_safe(prop_path)
                m = re.search(r"server\.port\s*=\s*(\d+)", prop_text)
                if m:
                    result["ports"].append({
                        "module": rel(module_dir, root),
                        "port": m.group(1),
                        "source": rel(prop_path, root),
                    })
            for yml_path in _rglob_filtered(module_dir, "application*.yml"):
                yml_text = read_text_safe(yml_path)
                m = re.search(r"port\s*:\s*(\d+)", yml_text)
                if m:
                    result["ports"].append({
                        "module": rel(module_dir, root),
                        "port": m.group(1),
                        "source": rel(yml_path, root),
                    })
            # Start command: use host-module relative path
            module_rel = rel(module_dir, root)
            result["start_commands"].append(f"mvn spring-boot:run -pl {module_rel}")
            # Log path: only logs/ sibling of src/main
            for log_dir in _rglob_filtered(module_dir, "logs"):
                if log_dir.is_dir() and not _is_ignored_path(log_dir):
                    result["log_paths"].append(rel(log_dir, root) + "/*.log")
        # Only take the first match
        if result["type"] != "unknown":
            break

    # Django
    if result["type"] == "unknown":
        if (root / "manage.py").exists() and any(_rglob_filtered(root, "settings.py")):
            result["type"] = "django"
            result["start_commands"].append("python manage.py runserver")
            for settings in _rglob_filtered(root, "settings.py"):
                text = read_text_safe(settings)
                m = re.search(r"(?:PORT|DJANGO_PORT)\s*=\s*(\d+)", text)
                if m:
                    result["ports"].append({"module": ".", "port": m.group(1), "source": rel(settings, root)})

    # Express / NestJS
    if result["type"] == "unknown":
        pkg = root / "package.json"
        if pkg.exists():
            text = read_text_safe(pkg)
            if '"express"' in text or '"@nestjs/core"' in text or '"fastify"' in text:
                result["type"] = "express"
                result["start_commands"].append("npm start")
                # Scan .env or source for listen(
                for env_file in [root / ".env", root / ".env.local"]:
                    if env_file.exists():
                        env_text = read_text_safe(env_file)
                        m = re.search(r"PORT\s*=\s*(\d+)", env_text)
                        if m:
                            result["ports"].append({"module": ".", "port": m.group(1), "source": rel(env_file, root)})

    # Docker
    if result["type"] == "unknown":
        docker_files = list(root.glob("Dockerfile")) + list(root.glob("docker-compose*.yml"))
        if docker_files:
            result["type"] = "docker"
            for df in docker_files:
                text = read_text_safe(df)
                for m in re.finditer(r"EXPOSE\s+(\d+)", text):
                    result["ports"].append({"module": ".", "port": m.group(1), "source": rel(df, root)})
                for m in re.finditer(r'"(\d+):\d+"', text):
                    result["ports"].append({"module": ".", "port": m.group(1), "source": rel(df, root)})

    # Go
    if result["type"] == "unknown":
        if (root / "go.mod").exists():
            for main_go in _rglob_filtered(root, "main.go"):
                text = read_text_safe(main_go)
                if "http.ListenAndServe" in text or "gin.Default" in text or "echo.New" in text:
                    result["type"] = "go-server"
                    result["start_commands"].append("go run ./...")
                    m = re.search(r'ListenAndServe\s*\(\s*"[^"]*:(\d+)', text)
                    if m:
                        result["ports"].append({"module": rel(main_go.parent, root), "port": m.group(1), "source": rel(main_go, root)})
                    break

    # .NET
    if result["type"] == "unknown":
        csproj_files = list(_rglob_filtered(root, "*.csproj"))
        for csproj in csproj_files:
            text = read_text_safe(csproj)
            if "Microsoft.NET.Sdk.Web" in text:
                result["type"] = "dotnet"
                result["start_commands"].append(f"dotnet run --project {rel(csproj.parent, root)}")
                break

    # library / cli / unknown
    if result["type"] == "unknown":
        if (root / "setup.py").exists() or (root / "pyproject.toml").exists():
            result["type"] = "library"
        elif any(_rglob_filtered(root, "*.py")):
            # Detect CLI
            for py in list(_rglob_filtered(root, "*.py"))[:50]:
                text = read_text_safe(py)
                if "argparse.ArgumentParser" in text or "click.command" in text:
                    result["type"] = "cli"
                    break

    # Dedupe ports
    seen_ports: set[str] = set()
    unique_ports = []
    for p in result["ports"]:
        key = f"{p.get('module')}:{p.get('port')}"
        if key not in seen_ports:
            seen_ports.add(key)
            unique_ports.append(p)
    result["ports"] = unique_ports[:30]

    return result


# ---------------------------------------------------------------------------
# Hot files
# ---------------------------------------------------------------------------

def get_hot_files(root: Path) -> list[dict[str, Any]]:
    """Top 20 most-changed files via git log."""
    if not (root / ".git").exists():
        return []
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "--format=", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return []
        counter: dict[str, int] = {}
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line:
                counter[line] = counter.get(line, 0) + 1
        return [
            {"file": f, "commit_count": c}
            for f, c in sorted(counter.items(), key=lambda x: -x[1])[:20]
        ]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ---------------------------------------------------------------------------
# Runnable project type detection
# ---------------------------------------------------------------------------

def detect_runnable_project(root: Path) -> dict[str, Any]:
    """Detect runnable project type, ports, start command, and log paths."""
    result: dict[str, Any] = {"type": "unknown", "ports": [], "start_commands": [], "log_paths": []}

    # Spring Boot
    for pom in root.rglob("pom.xml"):
        try:
            text = pom.read_text(encoding="utf-8", errors="ignore")[:8000]
            if "spring-boot-maven-plugin" in text:
                result["type"] = "spring-boot"
                module = str(pom.parent.relative_to(root))
                result["start_commands"].append(f"mvn spring-boot:run -pl {module}")
                for prop_file in pom.parent.rglob("application*.properties"):
                    try:
                        for line in prop_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                            if "server.port" in line and "=" in line:
                                port = line.split("=", 1)[1].strip()
                                result["ports"].append({"module": module, "port": port, "source": str(prop_file.relative_to(root))})
                    except OSError:
                        pass
                for yml_file in pom.parent.rglob("application*.yml"):
                    try:
                        for line in yml_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                            if "port:" in line:
                                port = line.split("port:", 1)[1].strip()
                                if port.isdigit():
                                    result["ports"].append({"module": module, "port": port, "source": str(yml_file.relative_to(root))})
                    except OSError:
                        pass
                for log_cfg in pom.parent.rglob("logback*.xml"):
                    result["log_paths"].append(str(log_cfg.relative_to(root)))
                break
        except OSError:
            continue

    if result["type"] != "unknown":
        return result

    # Django
    if (root / "manage.py").exists() and any(root.rglob("settings.py")):
        result["type"] = "django"
        result["start_commands"].append("python manage.py runserver")
        return result

    # Express / NestJS
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "express" in deps or "@nestjs/core" in deps:
                result["type"] = "express"
                scripts = pkg.get("scripts", {})
                for key in ("start", "dev", "serve"):
                    if key in scripts:
                        result["start_commands"].append(f"npm run {key}")
                return result
        except (json.JSONDecodeError, OSError):
            pass

    # Docker
    if (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
        result["type"] = "docker"
        if (root / "docker-compose.yml").exists():
            result["start_commands"].append("docker-compose up")
        elif (root / "docker-compose.yaml").exists():
            result["start_commands"].append("docker-compose up")
        return result

    # Go server
    for main_go in root.rglob("main.go"):
        try:
            text = main_go.read_text(encoding="utf-8", errors="ignore")[:5000]
            if "ListenAndServe" in text or "gin." in text or "mux." in text or "fiber." in text:
                result["type"] = "go-server"
                result["start_commands"].append(f"go run {main_go.relative_to(root)}")
                return result
        except OSError:
            continue

    # .NET Web
    for csproj in root.rglob("*.csproj"):
        try:
            text = csproj.read_text(encoding="utf-8", errors="ignore")[:3000]
            if "Microsoft.NET.Sdk.Web" in text:
                result["type"] = "dotnet"
                result["start_commands"].append("dotnet run")
                return result
        except OSError:
            continue

    # Library / CLI detection
    if (root / "setup.py").exists() or (root / "pyproject.toml").exists():
        result["type"] = "library"
    elif pkg_json.exists():
        result["type"] = "library"

    return result


# ---------------------------------------------------------------------------
# Entity field extraction (entity_fields)
# ---------------------------------------------------------------------------

# Per-stack entity markers and field-extraction regexes
_ENTITY_MARKERS: dict[str, list[re.Pattern[str]]] = {
    "java_kotlin": [
        re.compile(r'@TableName\s*\(\s*["\']([^"\']+)'),  # MyBatis-Plus
        re.compile(r'@Entity\b'),  # JPA
        re.compile(r'@Table\s*\(\s*name\s*=\s*["\']([^"\']+)'),  # JPA @Table
    ],
    "python": [
        re.compile(r'class\s+\w+\(.*?models\.Model\)', re.I),  # Django
        re.compile(r'__tablename__\s*=\s*["\']([^"\']+)'),  # SQLAlchemy
    ],
    "typescript_javascript": [
        re.compile(r'@Entity\s*\('),  # TypeORM
        re.compile(r'model\s+\w+\s*\{'),  # Prisma schema
    ],
    "go": [
        re.compile(r'TableName\s*\(\s*\)\s*string\s*\{'),  # GORM TableName()
        re.compile(r'`.*?gorm:".*?column:'),  # GORM struct tag
    ],
    "csharp_dotnet": [
        re.compile(r'\[Table\s*\(\s*["\']([^"\']+)'),  # EF [Table]
        re.compile(r'DbSet<\w+>\s+\w+\s*\{'),  # EF DbContext
    ],
}

# Java field extraction: capture type, field name, and possible annotations
_JAVA_FIELD_RE = re.compile(
    r'(?:(?:@\w+(?:\([^)]*\))?)\s*)*'  # optional annotations
    r'(?:private|protected|public)?\s+'
    r'([\w<>,?\s]+?)\s+'  # type
    r'(\w+)\s*[;=]',  # field name
)
_JAVA_TABLEFIELD_RE = re.compile(r'@TableField\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)')
_JAVA_VERSION_RE = re.compile(r'@Version\b')
_JAVA_TABLELOGIC_RE = re.compile(r'@TableLogic\b')


def scan_entity_fields(path: Path, root: Path, text: str, lang_key: str,
                       results: list[dict[str, Any]]) -> None:
    """Extract entity class fields: name, type, annotation markers."""
    if len(results) >= RESULT_LIMIT:
        return

    markers = _ENTITY_MARKERS.get(lang_key, [])
    if not markers:
        return

    is_entity = False
    table_name = ""
    for marker in markers:
        m = marker.search(text)
        if m:
            is_entity = True
            if m.lastindex and m.lastindex >= 1:
                table_name = m.group(1)
            break

    if not is_entity:
        return

    # Extract class name
    class_match = re.search(r'(?:public\s+)?class\s+(\w+)', text)
    class_name = class_match.group(1) if class_match else path.stem

    if lang_key == "java_kotlin":
        fields: list[dict[str, str]] = []
        for line in text.splitlines():
            line_stripped = line.strip()
            # Skip method definitions and comments
            if line_stripped.startswith("//") or line_stripped.startswith("/*") or line_stripped.startswith("*"):
                continue
            if "(" in line_stripped and ")" in line_stripped and not line_stripped.endswith(";"):
                continue

            fm = _JAVA_FIELD_RE.search(line_stripped)
            if fm:
                field_type = fm.group(1).strip()
                field_name = fm.group(2).strip()
                # Filter constants and serialization fields
                if field_name.isupper() or field_name == "serialVersionUID":
                    continue
                # Check special annotations
                annotations: list[str] = []
                # Look up to 3 lines above for annotations
                line_idx = text.find(line_stripped)
                context = text[max(0, line_idx - 200):line_idx]
                if _JAVA_VERSION_RE.search(context):
                    annotations.append("@Version")
                if _JAVA_TABLELOGIC_RE.search(context):
                    annotations.append("@TableLogic")
                col_match = _JAVA_TABLEFIELD_RE.search(context)
                col_name = col_match.group(1) if col_match else ""

                fields.append({
                    "name": field_name,
                    "type": field_type,
                    "column": col_name,
                    "annotations": annotations,
                })

        if fields:
            results.append({
                "file": str(path.relative_to(root)),
                "class": class_name,
                "table": table_name,
                "fields": fields[:50],  # cap 50 fields per entity
            })


# ---------------------------------------------------------------------------
# JSON field pattern detection (json_field_patterns)
# ---------------------------------------------------------------------------

_JSON_PARSE_PATTERNS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "java_kotlin": [
        (re.compile(r'JSON\.parse(?:Object|Array)\s*\(\s*\w+\.get(\w+)\s*\(\s*\)\s*,\s*(\w+)\.class'), "Fastjson parseObject"),
        (re.compile(r'objectMapper\.readValue\s*\(\s*\w+\.get(\w+)\s*\(\s*\)\s*,\s*(\w+)\.class'), "Jackson readValue"),
        (re.compile(r'typeHandler\s*=\s*JacksonTypeHandler\.class'), "MyBatis-Plus JacksonTypeHandler"),
        (re.compile(r'@TableField\s*\([^)]*typeHandler\s*=\s*(\w+)TypeHandler'), "custom TypeHandler"),
    ],
    "python": [
        (re.compile(r'json\.loads\s*\(\s*(?:self|instance|obj)\.(\w+)'), "json.loads field parse"),
        (re.compile(r'JSONField\s*\('), "Django JSONField"),
    ],
    "typescript_javascript": [
        (re.compile(r'JSON\.parse\s*\(\s*\w+\.(\w+)'), "JSON.parse field parse"),
        (re.compile(r"type:\s*['\"]jsonb?['\"]"), "TypeORM jsonb column"),
    ],
    "go": [
        (re.compile(r'json\.Unmarshal\s*\(\s*\[\]byte\s*\(\s*\w+\.(\w+)'), "json.Unmarshal field"),
        (re.compile(r'`[^`]*gorm:"[^"]*type:jsonb?[^"]*"'), "GORM jsonb tag"),
    ],
    "csharp_dotnet": [
        (re.compile(r'JsonSerializer\.Deserialize<(\w+)>\s*\(\s*\w+\.(\w+)'), "System.Text.Json deserialize"),
        (re.compile(r'\[Column\s*\(\s*TypeName\s*=\s*["\']jsonb?["\']'), "EF jsonb Column"),
    ],
}


def scan_json_field_patterns(path: Path, root: Path, text: str, lang_key: str,
                             results: list[dict[str, Any]]) -> None:
    """Detect JSON field parse patterns (String-stored JSON deserialized to DTO)."""
    if len(results) >= RESULT_LIMIT:
        return

    patterns = _JSON_PARSE_PATTERNS.get(lang_key, [])
    for pat, desc in patterns:
        for m in pat.finditer(text):
            results.append({
                "file": str(path.relative_to(root)),
                "match": m.group(0)[:120],
                "pattern_type": desc,
                "line": text[:m.start()].count("\n") + 1,
            })
            if len(results) >= RESULT_LIMIT:
                return


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def run_scan(root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    start_time = time.monotonic()

    # Language stack from inventory (original labels, not internal keys)
    language_stack: list[str] = [item["language"] for item in inventory.get("languages", [])]

    # Active pattern families and file extensions for this scan
    active_lang_keys: set[str] = set()
    active_exts: set[str] = set()
    for lang in language_stack:
        key = LANG_TO_PATTERN_KEY.get(lang)
        if key:
            active_lang_keys.add(key)
    for ext, lang in EXT_TO_LANG.items():
        if LANG_TO_PATTERN_KEY.get(lang) in active_lang_keys:
            active_exts.add(ext)

    # If inventory empty (run without inventory), scan all known extensions
    if not active_exts:
        active_exts = set(EXT_TO_LANG.keys())
        active_lang_keys = set(LANG_PATTERNS.keys())

    # language_stack output uses original labels (not internal keys)
    if not language_stack:
        language_stack = sorted(
            {lang for lang, key in LANG_TO_PATTERN_KEY.items() if key in active_lang_keys}
        )

    files = iter_source_files(root, active_exts)

    status_patterns: list[dict[str, Any]] = []
    concurrency_patterns: list[dict[str, Any]] = []
    event_patterns: list[dict[str, Any]] = []
    framework_components: list[dict[str, Any]] = []
    soft_delete_patterns: list[dict[str, Any]] = []
    idempotency_patterns: list[dict[str, Any]] = []
    entity_fields: list[dict[str, Any]] = []
    json_field_patterns: list[dict[str, Any]] = []

    for path in files:
        # Timeout guard
        if time.monotonic() - start_time > TIMEOUT_SECONDS:
            break

        ext = path.suffix.lower()
        lang = EXT_TO_LANG.get(ext, "")
        lang_key = LANG_TO_PATTERN_KEY.get(lang, "")
        if not lang_key:
            continue

        text = read_file_text(path)
        if not text:
            continue

        scan_status_patterns(path, root, text, lang_key, status_patterns)
        scan_concurrency_patterns(path, root, text, lang_key, concurrency_patterns)
        scan_event_patterns(path, root, text, lang_key, event_patterns)
        scan_framework_components(path, root, text, lang_key, framework_components)
        scan_soft_delete(path, root, text, lang_key, soft_delete_patterns)
        scan_idempotency(path, root, text, lang_key, idempotency_patterns)
        scan_entity_fields(path, root, text, lang_key, entity_fields)
        scan_json_field_patterns(path, root, text, lang_key, json_field_patterns)

    runnable_project = detect_runnable_project(root)
    hot_files = get_hot_files(root)

    return {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "language_stack": language_stack or list(active_lang_keys),
        "status_patterns": status_patterns,
        "concurrency_patterns": concurrency_patterns,
        "event_patterns": event_patterns,
        "framework_components": framework_components,
        "soft_delete_patterns": soft_delete_patterns,
        "idempotency_patterns": idempotency_patterns,
        "entity_fields": entity_fields,
        "json_field_patterns": json_field_patterns,
        "runnable_project": runnable_project,
        "hot_files": hot_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="doc-init deep knowledge extraction (language pattern scan)")
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--inventory", help="JSON from project_inventory.py; if omitted, infer from extensions only")
    parser.add_argument("--output", help="output JSON file; default stdout")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: project root does not exist or is not a directory: {root}")
        return 2

    inventory: dict[str, Any] = {}
    if args.inventory:
        inv_path = Path(args.inventory).expanduser()
        if inv_path.exists():
            try:
                inventory = json.loads(inv_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"warning: cannot read inventory {inv_path}: {e}; inferring from file extensions")

    data = run_scan(root, inventory)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
