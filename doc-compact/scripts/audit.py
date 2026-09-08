#!/usr/bin/env python3
# Read-only doc-governance audit — SKILL.md Step 2.
# Does not modify files; skips third-party / build / backup / git dirs.
# Usage: audit.py [project-root] [--compact-date YYYY-MM-DD]
#                  [--save-metrics path] [--compare-metrics path]
#   Default cwd; one project per run.
#   --compact-date: Step 6 only — enables check I (per-doc compact stamp gate).
#                   Omit during Step 2 read-only audit.
#   --save-metrics: write check J AGENTS.md metrics JSON baseline (Step 2).
#   --compare-metrics: load baseline JSON, print before/after (Step 6);
#                      estimated token growth marked ⚠.
#
# Exit code is not pass/fail; read the trailing summary counts and ❌ lines.

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------- args ----------

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("proj", nargs="?", default=".")
parser.add_argument("--compact-date", default="")
parser.add_argument("--save-metrics", default="")
parser.add_argument("--compare-metrics", default="")
args = parser.parse_args()

PROJ = Path(args.proj).resolve()
COMPACT_DATE = args.compact_date

SCRIPT_DIR = Path(__file__).resolve().parent
DOC_INIT_LINT = SCRIPT_DIR / ".." / ".." / "doc-init" / "scripts" / "doc_nav_lint.py"
DOC_INIT_LINT = DOC_INIT_LINT.resolve()

try:
    os.chdir(PROJ)
except OSError:
    print(f"cannot enter directory: {PROJ}", file=sys.stderr)
    sys.exit(2)

# ---------- prune dirs ----------

PRUNE_NAMES = {
    "node_modules", "target", "build", "dist", "out",
    ".build", ".git", ".claude", ".stversions", "vendor",
    ".worktrees", "SourcePackages", "DerivedData", ".derivedData",
}

# Prefixed build dirs: .build-foo, .derivedData-codex, etc. (exact names in PRUNE_NAMES)
PRUNE_PREFIXES = (".build", ".derivedData")

EXCL_RE = re.compile(
    r"node_modules|/target/|/build/|/dist/|/out/"
    r"|/\.build(?:-|/)|/\.derivedData(?:-|/)|/DerivedData/"
    r"|/\.worktrees/|/SourcePackages/"
    r"|/\.git/|/\.claude/|/\.stversions/|/vendor/"
)


def should_prune(path: Path) -> bool:
    """True if any path component is a pruned dir (incl. .build* / .derivedData*)."""
    for part in path.parts:
        if part in PRUNE_NAMES:
            return True
        for prefix in PRUNE_PREFIXES:
            if part == prefix or part.startswith(prefix + "-") or (
                part.startswith(prefix) and len(part) > len(prefix)
            ):
                return True
    return False


def find_md(name_glob: str):
    """Recursively find .md files matching name_glob under cwd, skipping pruned dirs."""
    results = []
    for p in Path(".").rglob(name_glob):
        if p.is_file() and not should_prune(p):
            results.append(p)
    return results


def find_in_dirs(dirs, name_glob: str, extra_filter=None):
    """Recursively find files under the given directory list."""
    results = []
    for d in dirs:
        dp = Path(d)
        if not dp.exists():
            continue
        for p in dp.rglob(name_glob):
            if p.is_file() and not should_prune(p):
                if extra_filter is None or extra_filter(p):
                    results.append(p)
    return results


# ---------- output ----------

print(f"==== doc-governance audit: {Path('.').resolve()} ====")

# ---------- A. CLAUDE.md single-line @*.md ----------

print()
print("## A. CLAUDE.md is a single-line @*.md (any @ref.md form is OK)")
a = 0
for c in find_md("CLAUDE.md"):
    content = c.read_text(encoding="utf-8", errors="replace").replace("\n", "").replace("\r", "").replace(" ", "").replace("\t", "")
    if not re.fullmatch(r"@.+\.md", content):
        print(f"  ❌ not single-line @*.md: {c}")
        a += 1
if a == 0:
    print("  ✓ all compliant")

# ---------- B. dangling @AGENTS.md ----------

print()
print("## B. dangling @AGENTS.md (referenced but no sibling AGENTS.md)")
b = 0
for c in find_md("CLAUDE.md"):
    text = c.read_text(encoding="utf-8", errors="replace")
    if "@AGENTS.md" in text:
        if not (c.parent / "AGENTS.md").exists():
            print(f"  ❌ dangling: {c}")
            b += 1
if b == 0:
    print("  ✓ none dangling")

# ---------- C. legacy index / tool inject-block leftovers ----------

print()
print("## C. legacy index / tool inject-block leftovers")

# Bare INDEX.md or OVERVIEW.md refs (prefix is not underscore/uppercase letter)
bare_index_ref = []
inject_block = []

bare_re = re.compile(r"(?<![_A-Z])OVERVIEW\.md|(?<![_A-Z])INDEX\.md")
inject_re = re.compile(r"<!--\s.*:start\s*-->")

for p in find_md("*.md"):
    if EXCL_RE.search(str(p)) or should_prune(p):
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    if bare_re.search(text):
        bare_index_ref.append(p)
    # managed:inherited-agents is re-injected by sync-agent-files, not leftover — exclude from inject-block
    if (
        p.name in ("AGENTS.md", "CLAUDE.md")
        and inject_re.search(text)
        and "managed:inherited-agents" not in text
    ):
        inject_block.append(p)

# Filename itself is bare INDEX.md or OVERVIEW.md
bare_file = [p for p in find_md("INDEX.md") if not EXCL_RE.search(str(p))]
bare_file += [p for p in find_md("OVERVIEW.md") if not EXCL_RE.search(str(p))]

for p in bare_index_ref:
    print(f"  legacy index ref (bare INDEX/OVERVIEW): {p}")
for p in bare_file:
    print(f"  bare index file: {p}")
for p in inject_block:
    print(f"  inject block: {p}")

if not bare_index_ref and not bare_file and not inject_block:
    print("  ✓ no leftovers (named *_INDEX.md is a valid secondary index, ignored)")

# ---------- D. AGENTS.md size ----------

print()
print("## D. AGENTS.md size (>500 lines → consider a secondary index)")
for f in find_md("AGENTS.md"):
    try:
        # Match wc -l: count newlines; no trailing newline does not add an extra line
        content = f.read_bytes()
        n = content.count(b"\n")
    except OSError:
        n = 0
    flag = "  ⚠ over threshold" if n > 500 else ""
    # wc -l on macOS prints "     223" (5 leading spaces); with the script's
    # two-space prefix the total indent is "       223" (7 spaces + digits)
    print(f"  {n:8d} lines  {f}{flag}")

# ---------- E. orphan docs ----------

print()
print("## E. orphan docs (under docs/ and specs/, not referenced by root AGENTS.md ∪ any README.md ∪ any *_INDEX.md)")

idx_texts = []
if Path("AGENTS.md").exists():
    idx_texts.append(Path("AGENTS.md").read_text(encoding="utf-8", errors="replace"))

for d in ("docs", "specs"):
    for p in find_in_dirs([d], "README.md"):
        idx_texts.append(p.read_text(encoding="utf-8", errors="replace"))
    for p in find_in_dirs([d], "*_INDEX.md"):
        idx_texts.append(p.read_text(encoding="utf-8", errors="replace"))

combined_idx = "\n".join(idx_texts)

e = 0
for f in find_in_dirs(["docs", "specs"], "*.md"):
    bn = f.name
    if bn == "README.md":
        continue
    if bn.endswith("_INDEX.md"):
        continue
    if bn not in combined_idx:
        print(f"  ❌ orphan: {f}")
        e += 1
if e == 0:
    print("  ✓ no orphans")

# ---------- F. filename compliance ----------

print()
print("## F. filename compliance (high-certainty directories)")
f_count = 0

date_re = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")
review_re = re.compile(r"^.+-review\.md$")
space_re = re.compile(r" ")

# troubleshooting records (named *_INDEX.md / README are allowed, skip)
for p in find_in_dirs(["."], "*.md",
                      extra_filter=lambda p: "troubleshooting" in p.parts):
    bn = p.name
    if bn == "README.md" or bn.endswith("_INDEX.md"):
        continue
    if not date_re.match(bn):
        print(f"  ❌ troubleshooting record should be YYYY-MM-DD-*.md: {p}")
        f_count += 1

# review ledgers under reviews/ (named *_INDEX.md / README allowed, skip)
for p in find_in_dirs(["."], "*.md",
                      extra_filter=lambda p: "reviews" in p.parts):
    bn = p.name
    if bn == "README.md" or bn.endswith("_INDEX.md"):
        continue
    if not review_re.match(bn):
        print(f"  ❌ review ledger should be *-review.md: {p}")
        f_count += 1

# filenames containing spaces
for p in find_md("*.md"):
    if " " in p.name:
        print(f"  ❌ filename contains spaces: {p}")
        f_count += 1

if f_count == 0:
    print("  ✓ naming compliant")

# ---------- G. fold suggestions ----------

print()
print("## G. fold suggestions (troubleshooting / review ledgers ≥3 docs but not folded)")
g_suggest = 0

ts_files = find_in_dirs(["."], "*.md",
                        extra_filter=lambda p: "troubleshooting" in p.parts and date_re.match(p.name))
ts_count = len(ts_files)
# Incident writeups often live under operations/: filename contains incident/fix,
# or YYYY-MM-DD-*.md under ops dirs (exclude README / *_INDEX); dedupe with
# troubleshooting/ before applying the type-driven fold threshold.
ops_incident_re = re.compile(r"(incident|fix)", re.I)
ops_incident_files = find_in_dirs(
    ["."],
    "*.md",
    extra_filter=lambda p: (
        "operations" in p.parts
        and p.name not in {"README.md"}
        and not p.name.endswith("_INDEX.md")
        and (ops_incident_re.search(p.name) is not None or date_re.match(p.name))
    ),
)
ops_only = [p for p in ops_incident_files if "troubleshooting" not in p.parts]
ts_effective = ts_count + len(ops_only)
ts_idx_list = find_in_dirs(["."], "TROUBLESHOOTING_INDEX.md")
ts_idx = ts_idx_list[0] if ts_idx_list else None

if ts_effective >= 3 and not ts_idx:
    detail = f"troubleshooting naming-compliant {ts_count} + operations incident candidates {len(ops_only)}"
    print(f"  💡 troubleshooting records total {ts_effective} ({detail}); suggest folding into docs/troubleshooting/TROUBLESHOOTING_INDEX.md (pointer index only — do not relocate operations originals by default); keep one strong route in root AGENTS.md (incl. when to skip / whether authoritative)")
    g_suggest += 1
elif ts_effective >= 3 and ts_idx:
    print(f"  ✓ troubleshooting (total {ts_effective}; troubleshooting={ts_count}, operations incident candidates={len(ops_only)}) already folded: {ts_idx}")
else:
    print(f"  ✓ troubleshooting (total {ts_effective}; troubleshooting={ts_count}, operations incident candidates={len(ops_only)}) below fold threshold")

rv_files = find_in_dirs(["."], "*.md",
                        extra_filter=lambda p: "reviews" in p.parts and review_re.match(p.name))
rv_count = len(rv_files)
rv_idx_list = find_in_dirs(["."], "REVIEW_INDEX.md")
rv_idx = rv_idx_list[0] if rv_idx_list else None

if rv_count >= 3 and not rv_idx:
    print(f"  💡 review ledger has {rv_count} docs; suggest folding into docs/reviews/REVIEW_INDEX.md; keep one strong route in root AGENTS.md (incl. when to skip / whether authoritative)")
    g_suggest += 1
elif rv_count >= 3 and rv_idx:
    print(f"  ✓ review ledger ({rv_count} docs) already folded: {rv_idx}")
else:
    print(f"  ✓ review ledger ({rv_count} docs) below fold threshold")

if g_suggest == 0:
    print("  ✓ no fold suggestions")

# ---------- H. doc-init cross-check ----------

print()
print("## H. doc-init cross-check (reverse global refs / self-nav leftovers / domain-map status; shared with doc-init — not reimplemented here)")
h = 0

if DOC_INIT_LINT.exists():
    try:
        result = subprocess.run(
            [sys.executable, str(DOC_INIT_LINT), "--root", ".", "--recursive", "--format", "text"],
            capture_output=True, text=True, encoding="utf-8"
        )
        lint_out = result.stdout
    except OSError:
        lint_out = ""

    for line in lint_out.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        severity, code, path, lineno, msg, proj = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        if code == "global-ref-in-project-agents":
            print(f"  ❌ reverse global-file ref: {path}:{lineno} ({proj}) — {msg}")
            h += 1
        elif code == "self-navigation-in-doc":
            print(f"  ⚠ self-navigation leftover inside docs: {path}:{lineno} ({proj})")
            h += 1

    if h == 0:
        print("  ✓ no reverse global refs / self-nav leftovers")

    print("  doc-init domain-map status (if domain_map_present=True, Step 5 compression must NOT delete/fold root AGENTS.md sections 「## 领域地图（doc-init）」 and 「## 待补充知识库（doc-init backlog）」):")
    for line in lint_out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 6 and parts[0] == "SUMMARY":
            print(f"    {parts[5]}: {parts[3]}, {parts[4]}")
else:
    print(f"  ⏭ doc-init not found (expected: {DOC_INIT_LINT}); skip cross-check; verify these three manually:")
    print("     - whether root AGENTS.md reverse-references global instruction files (no @~/.claude/... etc.)")
    print("     - whether docs/ still contain self-nav phrases like 「何时该读/必读」")
    print("     - whether root AGENTS.md has 「## 领域地图（doc-init）」 (if so, that section and the backlog section must not be deleted in Step 5 compression)")

# ---------- I. compact-stamp hard gate ----------

print()
print("## I. compact-stamp hard gate (SKILL.md Step 5/6 per-doc ledger; only when --compact-date is set)")
i = 0

if COMPACT_DATE:
    stamp = f"整理/压缩于 {COMPACT_DATE}"
    for p in find_in_dirs(["docs", "specs"], "*.md"):
        bn = p.name
        if bn == "README.md":
            continue
        if bn.endswith("_INDEX.md"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if stamp not in text:
            print(f"  ❌ missing this-round compact stamp ({COMPACT_DATE}): {p}")
            i += 1
    if i == 0:
        print(f"  ✓ in-scope docs/specs all have this-round compact stamp ({COMPACT_DATE})")
else:
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    print(f"  ⏭ --compact-date not set; skip (not needed in Step 2 read-only; Step 6 finish: audit.py <project-root> --compact-date {today})")

# ---------- J. AGENTS.md inflation metrics + managed blocks ----------

print()
print("## J. AGENTS.md inflation metrics + managed blocks (chars×0.47 ≈ tokens; thresholds are empirical)")

EMPHASIS_WORDS = ("必须", "一律", "禁止", "务必", "不得")
TOKEN_COEF = 0.47  # chars→token; adaptive coef details in plan_shards.py header
MARKER_RE = re.compile(r"<!--\s*([\w.-]+)\s*:\s*(begin|start|end)(?:\s+[\w.\-/]+)?\s*-->")


def agents_md_metrics(path):
    """Metrics for one AGENTS.md: chars/tokens/rules/emphasis + managed blocks."""
    text = path.read_text(encoding="utf-8", errors="replace")
    chars = len(text)
    rules = sum(
        1 for line in text.splitlines()
        if re.match(r"^[-*]\s+\S", line.strip()) or re.match(r"^\d+[.、]\s+\S", line.strip())
    )
    emphasis = sum(text.count(w) for w in EMPHASIS_WORDS)
    density = round(emphasis * 1000 / chars, 1) if chars else 0.0
    # Paired <!-- name:begin/end --> blocks; Step 4 index rebuild must keep verbatim
    markers = [MARKER_RE.search(line) for line in text.splitlines()]
    opens, closes = [], set()
    for m in markers:
        if not m:
            continue
        if m.group(2) in ("begin", "start"):
            opens.append(m.group(1))
        else:
            closes.add(m.group(1))
    managed = sorted(set(opens) & closes)
    unmatched = sorted((set(opens) | closes) - (set(opens) & closes))
    return {
        "chars": chars, "tokens": int(chars * TOKEN_COEF),
        "rules": rules, "emphasis": emphasis, "density": density,
        "managed_blocks": managed, "unmatched_markers": unmatched,
    }


current_metrics = {}
for f in find_md("AGENTS.md"):
    try:
        current_metrics[str(f)] = agents_md_metrics(f)
    except OSError:
        continue

if not current_metrics:
    print("  ⏭ no AGENTS.md found; skip")
else:
    for rel, m in current_metrics.items():
        dens_flag = "  ⚠ over threshold" if m["density"] > 10 else ""
        print(f"  {rel}: {m['chars']} chars ≈ {m['tokens']} tokens, {m['rules']} rules, "
              f"emphasis words {m['emphasis']} ({m['density']}/1k chars, threshold 10){dens_flag}")
        if m["managed_blocks"]:
            print(f"    🔒 managed blocks (keep verbatim in Step 4 index rebuild; do not compress/delete): {', '.join(m['managed_blocks'])}")
        if m["unmatched_markers"]:
            print(f"    ❌ unmatched managed markers (check manually for incomplete pairs): {', '.join(m['unmatched_markers'])}")

if args.save_metrics:
    import json
    Path(args.save_metrics).write_text(
        json.dumps(current_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved baseline → {args.save_metrics} (Step 6 compare: audit.py <project-root> --compare-metrics {args.save_metrics})")

if args.compare_metrics:
    import json
    try:
        baseline = json.loads(Path(args.compare_metrics).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"  ❌ baseline unreadable ({exc}); skip compare")
        baseline = None
    if baseline is not None:
        print("  ---- compare to baseline (Step 2 → current) ----")
        grew = 0
        for rel, cur in current_metrics.items():
            if rel not in baseline:
                print(f"  {rel}: new (≈ {cur['tokens']} tokens)")
                continue
            old = baseline[rel]
            delta = cur["tokens"] - old["tokens"]
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
            flag = "  ⚠ inflated (should be ≤ baseline; explain growth in finish report)" if delta > 0 else ""
            print(f"  {rel}: tokens {old['tokens']} → {cur['tokens']} ({arrow}{abs(delta)}), "
                  f"rules {old['rules']} → {cur['rules']}, emphasis density {old['density']} → {cur['density']}/1k chars{flag}")
            if delta > 0:
                grew += 1
        for rel in baseline:
            if rel not in current_metrics:
                print(f"  {rel}: in baseline, missing now")
        if grew == 0 and current_metrics:
            print("  ✓ all AGENTS.md estimated tokens within baseline")

# ---------- summary ----------

print()
if COMPACT_DATE:
    print(f"==== summary: noncompliant CLAUDE.md={a} dangling={b} orphans={e} naming={f_count} missing compact stamp={i} (fold suggestions={g_suggest}, doc-init cross-check={h}; not pass/fail) ====")
else:
    print(f"==== summary: noncompliant CLAUDE.md={a} dangling={b} orphans={e} naming={f_count} (fold suggestions={g_suggest}, doc-init cross-check={h}; compact-stamp check off; not pass/fail) ====")
