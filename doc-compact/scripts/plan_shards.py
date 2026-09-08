#!/usr/bin/env python3
# Step 5 shard planner — run after Step 2 audit, before dispatching subagents.
# Deterministic arithmetic only: per-file token estimates, large-KB detection,
# budget checks, and bin packing. Domain clustering is judgment work done by
# the main agent and passed in via --domain-map.
#
# Coefficient (measured): weighted average chars→tokens = 0.47 on 14 docs from
# mc-mdcrm (mixed KB / design / API / troubleshooting), tiktoken cl100k_base.
# Narrative-dense Chinese docs trend 0.55–0.60; code/table-dense docs 0.29–0.45.
# Auto-pick by content mix: code+table char ratio < 15% → 0.55, > 40% → 0.40,
# else 0.47. On a new project, sample 3–5 docs and override with --coef if needed.
#
# Usage: plan_shards.py <project-root> [--budget 90000] [--coef 0.47]
#                        [--domain-map map.json] [--json]
#   --budget      Net token budget per subagent (≈90k for a 128K window)
#   --domain-map  Main-agent domain map JSON: {"domain": ["docs/a.md", ...]}
#   --json        Machine-readable output
#
# Exit: 0 ok; 2 usage/input error. Packing warnings are in stdout, not exit code.

import argparse
import json
import math
import sys
from pathlib import Path

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("proj", nargs="?", default=".")
parser.add_argument("--budget", type=int, default=90000)
parser.add_argument("--coef", type=float, default=0.0,
                    help="Uniform coefficient override (>0 disables auto-pick)")
parser.add_argument("--domain-map", default="")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()

PROJ = Path(args.proj).resolve()
if not PROJ.is_dir():
    print(f"project root not found: {PROJ}", file=sys.stderr)
    sys.exit(2)

# Keep in sync with audit.py (agentsync: also prune worktrees / derived data)
PRUNE_NAMES = {
    "node_modules", "target", "build", "dist", "out",
    ".build", ".git", ".claude", ".stversions", "vendor",
    ".worktrees", "SourcePackages", "DerivedData", ".derivedData",
}
PRUNE_PREFIXES = (".build", ".derivedData")

LARGE_KB_TOKENS = 20000  # single doc > 20k tokens → exclusive subagent


def should_prune(path: Path) -> bool:
    """True if any path component is an excluded build/vendor/worktree dir."""
    for part in path.parts:
        if part in PRUNE_NAMES:
            return True
        for prefix in PRUNE_PREFIXES:
            if part == prefix or part.startswith(prefix + "-") or (
                part.startswith(prefix) and len(part) > len(prefix)
            ):
                return True
    return False


def estimate(text: str):
    """Return (chars, estimated_tokens, coefficient). Auto-picks by content mix."""
    chars = len(text)
    if chars == 0:
        return 0, 0, 0.47
    if args.coef > 0:
        return chars, int(chars * args.coef), args.coef
    code_chars, in_fence = 0, False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or stripped.startswith("|"):
            code_chars += len(line)
    ratio = code_chars / chars
    coef = 0.55 if ratio < 0.15 else (0.40 if ratio > 0.40 else 0.47)
    return chars, int(chars * coef), coef


# ---------- scan docs/ and specs/ ----------

files = []
for d in ("docs", "specs"):
    base = PROJ / d
    if not base.is_dir():
        continue
    for p in sorted(base.rglob("*.md")):
        if p.is_file() and not should_prune(p):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                print(f"⚠ skip unreadable: {p} ({exc})", file=sys.stderr)
                continue
            chars, tokens, coef = estimate(text)
            files.append({"path": str(p.relative_to(PROJ)), "chars": chars,
                          "tokens": tokens, "coef": coef})

large_kbs = [f for f in files if f["tokens"] > LARGE_KB_TOKENS]
normal = [f for f in files if f["tokens"] <= LARGE_KB_TOKENS]
total_tokens = sum(f["tokens"] for f in files)
normal_tokens = sum(f["tokens"] for f in normal)


def pack(file_list):
    """First-fit decreasing bin pack by token budget."""
    bins = []
    for f in sorted(file_list, key=lambda x: -x["tokens"]):
        for b in bins:
            if b["tokens"] + f["tokens"] <= args.budget:
                b["tokens"] += f["tokens"]
                b["files"].append(f)
                break
        else:
            bins.append({"tokens": f["tokens"], "files": [f]})
    return bins


def shard_lines(shards, label):
    """Format packed bins for human output."""
    out = []
    for i, b in enumerate(shards, 1):
        flag = "" if b["tokens"] <= args.budget else "  ⚠ over budget"
        out.append(f"  {label}{i}: {b['tokens']} token{flag}")
        for f in b["files"]:
            out.append(f"    {f['tokens']:7d}  {f['path']}")
    return out


# ---------- domain-map ----------

domain_groups = None
if args.domain_map:
    try:
        raw = json.loads(Path(args.domain_map).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"❌ domain-map unreadable: {exc}", file=sys.stderr)
        sys.exit(2)
    by_path = {f["path"]: f for f in files}
    domain_groups = {}
    missing = []
    for domain, paths in raw.items():
        group = []
        for rel in paths:
            norm = str(Path(rel))
            if norm in by_path:
                group.append(by_path[norm])
            else:
                missing.append(f"{domain}: {rel}")
        # Large KBs already get exclusive shards; exclude from domain bins
        domain_groups[domain] = [f for f in group if f["tokens"] <= LARGE_KB_TOKENS]
        domain_large = [f["path"] for f in group if f["tokens"] > LARGE_KB_TOKENS]
        if domain_large:
            print(f"ℹ domain[{domain}] large KB(s) already exclusive, skipped in domain pack: "
                  f"{', '.join(domain_large)}", file=sys.stderr)
    if missing:
        print("❌ domain-map references missing/out-of-scope files:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        sys.exit(2)
    assigned = {f["path"] for g in domain_groups.values() for f in g}
    unassigned = [f["path"] for f in normal if f["path"] not in assigned]
    if unassigned:
        print(f"⚠ {len(unassigned)} normal doc(s) missing from domain-map "
              f"(not packed; re-run without --domain-map for full list)",
              file=sys.stderr)

# ---------- output ----------

result = {
    "proj": str(PROJ), "budget": args.budget,
    "total_files": len(files), "total_tokens": total_tokens,
    "normal_tokens": normal_tokens,
    "min_shards_normal": math.ceil(normal_tokens / args.budget) if args.budget else 0,
    "large_kbs": [{"path": f["path"], "tokens": f["tokens"]} for f in large_kbs],
    "files": files,
}

if args.json:
    shards_out = []
    for lk in large_kbs:
        shards_out.append({"domain": "(large-KB exclusive)", "tokens": lk["tokens"],
                           "files": [lk["path"]]})
    if domain_groups is not None:
        for domain, group in domain_groups.items():
            bins = pack(group)
            for i, b in enumerate(bins, 1):
                shards_out.append({"domain": f"{domain}#{i}" if len(bins) > 1 else domain,
                                   "tokens": b["tokens"],
                                   "files": [f["path"] for f in b["files"]]})
    result["shards"] = shards_out
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)

print(f"==== Step 5 shard plan: {PROJ} ====")
print()
print(f"total {len(files)} docs ≈ {total_tokens} token"
      f" (large KB {len(large_kbs)} = {sum(f['tokens'] for f in large_kbs)} token, "
      f"other {len(normal)} = {normal_tokens} token)")
print(f"budget {args.budget} token/shard: other docs need ≥ {result['min_shards_normal']} shards, "
      f"with large KBs ≥ {result['min_shards_normal'] + len(large_kbs)} subagents")
print()

if large_kbs:
    print("## Large KB (single doc > 20k token → exclusive subagent each)")
    for f in large_kbs:
        over = "  ⚠ single doc over budget; compress chapter-by-chapter" \
            if f["tokens"] > args.budget else ""
        print(f"  {f['tokens']:7d} token  {f['path']}{over}")
    print()

if domain_groups is not None:
    print("## Final pack (--domain-map; large KBs exclusive, not repeated in domains)")
    n = 0
    for domain, group in domain_groups.items():
        bins = pack(group)
        domain_tokens = sum(f["tokens"] for f in group)
        note = f"  ⚠ domain total {domain_tokens} over budget → split into {len(bins)} shards" \
            if domain_tokens > args.budget and len(bins) > 1 else ""
        print(f"[{domain}] {len(group)} docs ≈ {domain_tokens} token{note}")
        for line in shard_lines(bins, "  shard"):
            print(line)
        n += len(bins)
    print(f"  total subagents (incl. large KB): {n + len(large_kbs)}")
else:
    print("## Draft groups by directory (inventory only). Final plan MUST re-cluster by")
    print("   domain map / AGENTS.md nav — same-domain docs share terms; do not split by path.")
    by_dir = {}
    for f in normal:
        by_dir.setdefault(str(Path(f["path"]).parent), []).append(f)
    for d in sorted(by_dir):
        toks = sum(f["tokens"] for f in by_dir[d])
        print(f"  {d}/  {len(by_dir[d])} docs ≈ {toks} token")
    print()
    print("Next: main agent re-clusters by domain → write domain-map JSON → re-run this script.")
