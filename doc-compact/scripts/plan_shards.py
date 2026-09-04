#!/usr/bin/env python3
# Step 5 分片方案计算 —— 在 Step 2 审计后、分发 subagent 前运行。
# 只做确定性算术：逐篇 token 估算、大 KB 判定、预算校验与打包；不含任何判断类工作。
# 领域聚类是判断类工作，由主 agent 完成后经 --domain-map 传入，本脚本据此出最终装箱。
#
# 系数来源（实测）：mc-mdcrm 仓库 14 篇文档抽样（含大中小 KB、设计、接口、排障记录），
# tiktoken cl100k_base 实测字符→token 加权平均系数 = 0.47；中文叙述密集偏高（接口/叙述类
# 0.55~0.60），英文标识符/表格/代码密集偏低（0.29~0.45）。本脚本按单篇内容构成自动选系数：
# 代码块+表格字符占比 < 15% → 0.55（叙述密集），> 40% → 0.40（代码/表格密集），其余 0.47。
# 新项目首跑建议抽 3-5 篇实测校正，偏差大时用 --coef 统一覆盖。
#
# 用法: plan_shards.py <项目根> [--budget 90000] [--coef 0.47] [--domain-map map.json] [--json]
#   --budget    单个 subagent 的净 token 预算（128K 窗口实测 ≈ 90k，其他窗口按比例折算）
#   --domain-map 主 agent 按根 AGENTS.md 领域地图手写的 JSON：{"领域名": ["docs/a.md", ...]}
#   --json      输出机器可读结果（供主 agent 程序化消费；默认输出人读文本）
#
# 退出码: 0 正常；2 用法/输入错误（目录不存在、domain-map 不可读或引用了不存在的文件）。
# 结论看输出：装箱方案 + 超预算告警，退出码不表达「有没有可压空间」。

import argparse
import json
import math
import sys
from pathlib import Path

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("proj", nargs="?", default=".")
parser.add_argument("--budget", type=int, default=90000)
parser.add_argument("--coef", type=float, default=0.0,
                    help="统一覆盖系数（>0 时启用，停用按内容构成的自动选系数）")
parser.add_argument("--domain-map", default="")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()

PROJ = Path(args.proj).resolve()
if not PROJ.is_dir():
    print(f"项目根不存在: {PROJ}", file=sys.stderr)
    sys.exit(2)

# 与 audit.py 一致的排除目录
PRUNE_NAMES = {"node_modules", "target", "build", "dist", "out",
               ".build", ".git", ".claude", ".stversions", "vendor"}

LARGE_KB_TOKENS = 20000  # 大 KB 判定：单篇 > 20k token 独占一个 subagent


def should_prune(path: Path) -> bool:
    return any(part in PRUNE_NAMES for part in path.parts)


def estimate(text: str):
    """返回 (字符数, 估算token, 所用系数)。按代码块/表格字符占比自动选系数。"""
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


# ---------- 扫描 docs/ 与 specs/ ----------

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
                print(f"⚠ 跳过不可读文件: {p} ({exc})", file=sys.stderr)
                continue
            chars, tokens, coef = estimate(text)
            files.append({"path": str(p.relative_to(PROJ)), "chars": chars,
                          "tokens": tokens, "coef": coef})

large_kbs = [f for f in files if f["tokens"] > LARGE_KB_TOKENS]
normal = [f for f in files if f["tokens"] <= LARGE_KB_TOKENS]
total_tokens = sum(f["tokens"] for f in files)
normal_tokens = sum(f["tokens"] for f in normal)


def pack(file_list):
    """按 token 预算装箱（首适应递减）。返回分片列表，单片不超预算（除非单篇即超）。"""
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
    """装箱结果转输出行。"""
    out = []
    for i, b in enumerate(shards, 1):
        flag = "" if b["tokens"] <= args.budget else "  ⚠ 超预算"
        out.append(f"  {label}{i}: {b['tokens']} token{flag}")
        for f in b["files"]:
            out.append(f"    {f['tokens']:7d}  {f['path']}")
    return out


# ---------- domain-map 读取与校验 ----------

domain_groups = None
if args.domain_map:
    try:
        raw = json.loads(Path(args.domain_map).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"❌ domain-map 不可读: {exc}", file=sys.stderr)
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
        # 域内的大 KB 不参与该域装箱——大 KB 已全局独占，重复装入会导致一篇文档分给两个 subagent
        domain_groups[domain] = [f for f in group if f["tokens"] <= LARGE_KB_TOKENS]
        domain_large = [f["path"] for f in group if f["tokens"] > LARGE_KB_TOKENS]
        if domain_large:
            print(f"ℹ 域[{domain}]内的大 KB 已独占分片，不参与该域装箱: {', '.join(domain_large)}",
                  file=sys.stderr)
    if missing:
        print("❌ domain-map 引用了范围外/不存在的文件:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        sys.exit(2)
    assigned = {f["path"] for g in domain_groups.values() for f in g}
    # domain-map 只列普通文档即可，大 KB 由脚本全局判定独占，不算未分配
    unassigned = [f["path"] for f in normal if f["path"] not in assigned]
    if unassigned:
        print(f"⚠ 有 {len(unassigned)} 篇普通文档未出现在 domain-map 中（不参与装箱，勿漏审；"
              f"去掉 --domain-map 重跑可看全量清单）", file=sys.stderr)

# ---------- 输出 ----------

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
        shards_out.append({"domain": "(大KB独占)", "tokens": lk["tokens"], "files": [lk["path"]]})
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

print(f"==== Step 5 分片方案: {PROJ} ====")
print()
print(f"总计 {len(files)} 篇，≈ {total_tokens} token"
      f"（大 KB {len(large_kbs)} 篇 {sum(f['tokens'] for f in large_kbs)} token，"
      f"其余 {len(normal)} 篇 {normal_tokens} token）")
print(f"预算 {args.budget} token/片：其余文档最少 {result['min_shards_normal']} 片，"
      f"加大 KB 共 ≥ {result['min_shards_normal'] + len(large_kbs)} 个 subagent")
print()

if large_kbs:
    print("## 大 KB（单篇 > 20k token，各独占一个 subagent）")
    for f in large_kbs:
        over = "  ⚠ 单篇即超预算，压缩时按章分批过判据" if f["tokens"] > args.budget else ""
        print(f"  {f['tokens']:7d} token  {f['path']}{over}")
    print()

if domain_groups is not None:
    print("## 最终装箱（--domain-map；大 KB 已各自独占，不重复出现在域内）")
    n = 0
    for domain, group in domain_groups.items():
        bins = pack(group)
        domain_tokens = sum(f["tokens"] for f in group)
        note = f"  ⚠ 域总量 {domain_tokens} 超预算，已拆 {len(bins)} 片" \
            if domain_tokens > args.budget and len(bins) > 1 else ""
        print(f"[{domain}] {len(group)} 篇 ≈ {domain_tokens} token{note}")
        for line in shard_lines(bins, "  片"):
            print(line)
        n += len(bins)
    print(f"  合计（含大 KB 独占）: {n + len(large_kbs)} 个 subagent")
else:
    print("## 草稿分组（按目录，仅供清点；最终方案必须由主 agent 按根 AGENTS.md")
    print("   领域地图/文档导航重新聚类——同领域文档共享术语与约束，禁止按物理目录切分）")
    by_dir = {}
    for f in normal:
        by_dir.setdefault(str(Path(f["path"]).parent), []).append(f)
    for d in sorted(by_dir):
        toks = sum(f["tokens"] for f in by_dir[d])
        print(f"  {d}/  {len(by_dir[d])} 篇 ≈ {toks} token")
    print()
    print("下一步: 主 agent 按领域重聚类 → 手写 domain-map JSON → 重跑本脚本出最终装箱。")
