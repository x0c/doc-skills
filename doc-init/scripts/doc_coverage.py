#!/usr/bin/env python3
"""doc-init documentation coverage gate.

When root AGENTS.md already has a `## 领域地图（doc-init）` section, decide with a script
(not model self-report) whether the old map still covers current code. Prefix-match current
entry points (Controller / Service / Handler / Job / submodules, etc.) against registered
anchors, compute coverage and "uncovered but dense" areas, then compare the embedded source
fingerprint baseline stamp to measure code growth since the map was written. Emit
COMPLETE / STALE / NEEDS_INIT plus exit code.

Design boundary (doc-init: scripts collect facts, models judge business):
- Mechanical coverage + threshold guards only — does NOT decide whether an uncovered dir is
  a real domain (may be dead code / vendor / tests); model filters by product north star.
- Hard gate when incomplete: non-COMPLETE verdict means the model must not finish early.

Input: project_inventory.py JSON + project root (read AGENTS.md domain-map section).
Exit: 0=COMPLETE, 2=STALE (continue/review), 3=NEEDS_INIT (no map), 1=usage/read error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

MAP_HEADING_RE = re.compile(r"^\s*##\s+领域地图（doc-init）\s*$")
NEXT_HEADING_RE = re.compile(r"^\s*##\s+")
STAMP_RE = re.compile(r"<!--\s*覆盖度复核基线：(?P<body>.*?)-->", re.S)
PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.\-/]+/[A-Za-z0-9_.\-/]*")
INT_RE = re.compile(r"(\d+)")


def find_agents_file(root: Path) -> Path | None:
    for name in ("AGENTS.md", "agents.md"):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def extract_map_section(text: str) -> str | None:
    """Extract body of `## 领域地图（doc-init）` until the next ## heading. None if missing."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if MAP_HEADING_RE.match(line):
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if NEXT_HEADING_RE.match(lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def parse_stamp(section: str) -> dict[str, Any] | None:
    """Parse baseline stamp: 覆盖度复核基线：DATE · 源码指纹 扫描 N 文件 ... / M 子模块 · 基线提交 HASH."""
    m = STAMP_RE.search(section)
    if not m:
        return None
    body = m.group("body")
    stamp: dict[str, Any] = {"raw": m.group(0).strip()}
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", body)
    stamp["date"] = date_m.group(1) if date_m else None
    files_m = re.search(r"扫描\s*(\d+)\s*文件", body)
    stamp["scanned_files"] = int(files_m.group(1)) if files_m else None
    mods_m = re.search(r"(\d+)\s*子模块", body)
    stamp["submodules"] = int(mods_m.group(1)) if mods_m else None
    commit_m = re.search(r"基线提交\s*([0-9a-fA-F]{6,40})", body)
    stamp["commit"] = commit_m.group(1) if commit_m else None
    return stamp


def parse_map_anchors(section: str, root: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Extract domain name + entry-anchor paths from each domain-map table row.

    Anchor cells may be `src/channels/` or `src/channels/ · ChannelHandler`; keep path-like
    tokens, preferring paths that exist on disk. Returns (domain rows, deduped anchor prefixes).
    """
    rows: list[dict[str, str]] = []
    anchors: list[str] = []
    seen: set[str] = set()
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        # Skip header / separator rows (Chinese column titles are detection literals)
        joined = "".join(cells)
        if set(joined) <= set("-: ") or "领域" in cells[0] or "入口锚点" in joined or "状态" in joined and "入口" in joined:
            # Header/sep heuristic: column titles 领域/入口锚点/状态, or all ---
            if set(joined) <= set("-: ") or ("领域" in cells[0] and "锚点" in joined):
                continue
        domain = cells[0]
        anchor_cell = cells[1]
        if set(anchor_cell) <= set("-: ") or not domain or set(domain) <= set("-: "):
            continue
        tokens = PATH_TOKEN_RE.findall(anchor_cell)
        row_anchors: list[str] = []
        for tok in tokens:
            norm = tok.strip().rstrip("/")
            if not norm:
                continue
            row_anchors.append(norm)
            if norm not in seen:
                seen.add(norm)
                anchors.append(norm)
        status = cells[2].strip() if len(cells) >= 3 else ""
        rows.append({"domain": domain, "anchor_cell": anchor_cell, "anchors": ",".join(row_anchors), "status": status})
    # Sort anchors: existing paths first, then longer (more specific)
    anchors.sort(key=lambda a: ((root / a).exists(), len(a)), reverse=True)
    return rows, anchors


def collect_code_units(inventory: dict[str, Any]) -> list[str]:
    """Current code entry set: entry_candidates files + submodule dirs, deduped."""
    units: set[str] = set()
    for paths in (inventory.get("entry_candidates") or {}).values():
        for p in paths:
            if isinstance(p, str):
                units.add(p)
    for mod in inventory.get("submodules") or []:
        path = mod.get("path") if isinstance(mod, dict) else None
        if path:
            units.add(str(path).rstrip("/"))
    return sorted(units)


def is_covered(unit: str, anchors: list[str]) -> bool:
    for anchor in anchors:
        if unit == anchor or unit.startswith(anchor + "/") or anchor.startswith(unit + "/"):
            return True
    return False


def entries_under(anchors_csv: str, units: list[str]) -> list[str]:
    """List current code entries under this domain's anchors (unit inside anchor only).

    For drift spot-checks: turn "spot-check reused domains" into "here are N current entries — verify KB still matches".
    """
    row_anchors = [a for a in anchors_csv.split(",") if a]
    hits: set[str] = set()
    for u in units:
        for a in row_anchors:
            if u == a or u.startswith(a + "/"):
                hits.add(u)
                break
    return sorted(hits)


def group_dir(unit: str, depth: int) -> str:
    parts = [p for p in unit.split("/") if p]
    if len(parts) <= 1:
        return parts[0] if parts else unit
    return "/".join(parts[: min(depth, len(parts) - 1)])


def git_short_commit(root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        return None
    return None


def build_fingerprint(inventory: dict[str, Any], root: Path) -> dict[str, Any]:
    langs = {item["language"]: item["file_count"] for item in inventory.get("languages") or []}
    return {
        "scanned_files": (inventory.get("scan") or {}).get("scanned_files"),
        "submodules": len(inventory.get("submodules") or []),
        "languages": langs,
        "commit": git_short_commit(root),
    }


def make_stamp_line(fp: dict[str, Any]) -> str:
    langs = fp.get("languages") or {}
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:3]
    lang_str = " · ".join(f"{k} {v}" for k, v in top) if top else "no recognized language"
    commit = fp.get("commit")
    commit_str = f" · 基线提交 {commit}" if commit else ""
    return (
        f"<!-- 覆盖度复核基线：{date.today().isoformat()} · 源码指纹 "
        f"扫描 {fp.get('scanned_files')} 文件 / {lang_str} / {fp.get('submodules')} 子模块{commit_str} -->"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="doc-init coverage gate: whether the old domain map still covers current code")
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--inventory", default=".doc-init-project-inventory.json", help="JSON path from project_inventory.py")
    parser.add_argument("--min-coverage", type=float, default=0.85, help="STALE if entry coverage is below this")
    parser.add_argument("--max-uncovered-area-entries", type=int, default=3, help="STALE if any uncovered dir has >= this many entries (likely unregistered domain)")
    parser.add_argument("--max-growth-pct", type=float, default=0.25, help="STALE if scanned-file growth vs baseline exceeds this fraction")
    parser.add_argument("--group-depth", type=int, default=2, help="directory depth for grouping uncovered areas")
    parser.add_argument("--allow-missing-baseline", action="store_true", help="do not force STALE when baseline stamp is missing")
    parser.add_argument("--json", action="store_true", help="emit JSON (default: human-readable summary)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    inv_path = Path(args.inventory)
    if not inv_path.is_absolute():
        inv_path = root / inv_path
    if not inv_path.is_file():
        print(f"[error] inventory not found: {inv_path}; run project_inventory.py --output {inv_path.name} first", file=sys.stderr)
        return 1
    try:
        inventory = json.loads(inv_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[error] inventory JSON parse failed: {exc}", file=sys.stderr)
        return 1

    agents = find_agents_file(root)
    fingerprint = build_fingerprint(inventory, root)
    result: dict[str, Any] = {
        "root": str(root),
        "current_fingerprint": fingerprint,
        "suggested_stamp": make_stamp_line(fingerprint),
    }

    if agents is None:
        result.update({"verdict": "NEEDS_INIT", "map_present": False,
                       "reasons": ["no AGENTS.md at project root"]})
        emit(result, args.json)
        return 3
    section = extract_map_section(agents.read_text(encoding="utf-8"))
    if section is None:
        result.update({"verdict": "NEEDS_INIT", "map_present": False,
                       "reasons": ["AGENTS.md has no `## 领域地图（doc-init）` section — treat as init incomplete"]})
        emit(result, args.json)
        return 3

    rows, anchors = parse_map_anchors(section, root)
    stamp = parse_stamp(section)

    units = collect_code_units(inventory)
    covered = [u for u in units if is_covered(u, anchors)]
    uncovered = [u for u in units if not is_covered(u, anchors)]
    total = len(units)
    coverage_pct = (len(covered) / total) if total else None

    # Aggregate uncovered areas
    area_counter: dict[str, list[str]] = {}
    for u in uncovered:
        area_counter.setdefault(group_dir(u, args.group_depth), []).append(u)
    uncovered_areas = sorted(
        ({"dir": d, "entry_count": len(v), "sample": sorted(v)[:5]} for d, v in area_counter.items()),
        key=lambda a: a["entry_count"], reverse=True,
    )

    # Code-volume growth
    growth = None
    if stamp and stamp.get("scanned_files") and fingerprint.get("scanned_files"):
        base = stamp["scanned_files"]
        cur = fingerprint["scanned_files"]
        growth = {
            "baseline_scanned_files": base,
            "current_scanned_files": cur,
            "delta": cur - base,
            "pct": round((cur - base) / base, 4) if base else None,
            "baseline_submodules": stamp.get("submodules"),
            "current_submodules": fingerprint.get("submodules"),
        }

    reasons: list[str] = []
    verdict = "COMPLETE"

    if total == 0:
        verdict = "STALE"
        reasons.append("inventory found no entry points (empty entry_candidates/submodules); cannot confirm coverage mechanically — manual review needed")
    if not anchors:
        verdict = "STALE"
        reasons.append("domain-map section yielded no entry-anchor paths; map may be damaged or anchors malformed")
    if coverage_pct is not None and coverage_pct < args.min_coverage:
        verdict = "STALE"
        reasons.append(f"entry coverage {coverage_pct:.0%} < threshold {args.min_coverage:.0%} ({len(uncovered)}/{total} entry points have no map-row coverage)")
    big_areas = [a for a in uncovered_areas if a["entry_count"] >= args.max_uncovered_area_entries]
    if big_areas:
        verdict = "STALE"
        reasons.append(
            "dense unregistered areas (likely new since map or originally missed): "
            + "; ".join(f"{a['dir']} ({a['entry_count']} entries)" for a in big_areas[:8])
        )
    if stamp is None and not args.allow_missing_baseline:
        verdict = "STALE"
        reasons.append("domain-map section has no 『覆盖度复核基线』 stamp; cannot judge code growth — treat as possibly badly stale")
    if growth and growth.get("pct") is not None and growth["pct"] > args.max_growth_pct:
        verdict = "STALE"
        reasons.append(f"code volume grew {growth['pct']:.0%} vs baseline ({growth['baseline_scanned_files']}→{growth['current_scanned_files']} files) > threshold {args.max_growth_pct:.0%}; per-domain drift spot-check needed")

    if verdict == "COMPLETE":
        reasons.append("map anchors cover current code areas and volume growth is modest — treat as truly complete")

    # Drift checklist: for 「已生成（复用现有）」 domains, list current entries under anchors for KB spot-check.
    reuse_domains: list[dict[str, Any]] = []
    for row in rows:
        if "已生成" not in row.get("status", ""):
            continue
        ents = entries_under(row["anchors"], units)
        reuse_domains.append({
            "domain": row["domain"],
            "anchors": row["anchors"],
            "status": row["status"],
            "entry_count": len(ents),
            "entries_sample": ents[:8],
        })

    result.update({
        "verdict": verdict,
        "map_present": True,
        "mapped_domains": len(rows),
        "map_anchors": anchors,
        "baseline_stamp": stamp,
        "growth": growth,
        "coverage": {
            "total_entry_points": total,
            "covered": len(covered),
            "uncovered": len(uncovered),
            "coverage_pct": round(coverage_pct, 4) if coverage_pct is not None else None,
            "uncovered_areas": uncovered_areas,
        },
        "reuse_domains_for_drift_check": reuse_domains,
        "reasons": reasons,
    })
    emit(result, args.json)
    return 0 if verdict == "COMPLETE" else 2


def emit(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    v = result["verdict"]
    badge = {"COMPLETE": "✅ COMPLETE", "STALE": "⚠️  STALE (continue/review)", "NEEDS_INIT": "🆕 NEEDS_INIT"}[v]
    print(f"coverage-gate verdict: {badge}")
    if result.get("map_present"):
        cov = result["coverage"]
        print(f"  mapped domains: {result['mapped_domains']} · parsed anchors {len(result['map_anchors'])}")
        pct = cov["coverage_pct"]
        print(f"  entry coverage: {cov['covered']}/{cov['total_entry_points']}"
              + (f"（{pct:.0%}）" if pct is not None else ""))
        if result.get("growth"):
            g = result["growth"]
            pctg = g.get("pct")
            print(f"  code-volume vs baseline: {g['baseline_scanned_files']}→{g['current_scanned_files']} files"
                  + (f"（+{pctg:.0%}）" if pctg is not None else ""))
        elif result.get("baseline_stamp") is None:
            print("  code-volume vs baseline: no baseline stamp; cannot compare")
        if cov["uncovered_areas"]:
            print("  uncovered areas (by entry count desc; model decides if real new domain):")
            for a in cov["uncovered_areas"][:10]:
                print(f"    - {a['dir']}: {a['entry_count']} entries, e.g. {', '.join(a['sample'][:3])}")
        rd = result.get("reuse_domains_for_drift_check") or []
        if rd:
            print("  drift checklist (『已生成（复用现有）』 domains' current entries; verify KB-tagged entries still land and no dense new unregistered entries):")
            for d in rd:
                line = f"    - {d['domain']} ({d['anchors'] or 'no anchors'}): {d['entry_count']} current entries"
                if d["entries_sample"]:
                    line += f", e.g. {', '.join(d['entries_sample'][:3])}"
                print(line)
    print("verdict reasons:")
    for r in result["reasons"]:
        print(f"  - {r}")
    print(f"suggested baseline stamp to write back into the map section:\n  {result['suggested_stamp']}")


if __name__ == "__main__":
    sys.exit(main())
