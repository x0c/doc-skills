#!/usr/bin/env python3
# 文档治理只读审计 —— 对应 SKILL.md Step 2。
# 只读、不改任何文件；自动排除第三方 / 构建产物 / 备份 / git 目录。
# 用法: audit.py [项目根] [--compact-date YYYY-MM-DD] [--save-metrics 路径] [--compare-metrics 路径]
#   默认当前目录；一次只审计一个项目。
#   --compact-date：仅 Step 6 收尾核对压缩账目时传，启用检查 I（逐篇压缩标识硬闸门）；
#                   Step 2 只读审计阶段不传，跳过该检查。
#   --save-metrics：把检查 J 的 AGENTS.md 量化指标写入 JSON 基线（Step 2 用）。
#   --compare-metrics：读基线 JSON，输出压缩前后对比（Step 6 用）；估算 token 上升则标 ⚠。
#
# 退出码不表达成败，结论看输出末尾「小结」三个计数与各节 ❌ 行。

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------- 参数解析 ----------

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
    print(f"无法进入目录: {PROJ}", file=sys.stderr)
    sys.exit(2)

# ---------- 排除目录集合 ----------

PRUNE_NAMES = {
    "node_modules", "target", "build", "dist", "out",
    ".build", ".git", ".claude", ".stversions", "vendor",
}

EXCL_RE = re.compile(
    r"node_modules|/target/|/build/|/dist/|/out/|/\.build/"
    r"|/\.git/|/\.claude/|/\.stversions/|/vendor/"
)


def should_prune(path: Path) -> bool:
    """判断 path 的任意父级是否是需排除的目录名。"""
    return any(part in PRUNE_NAMES for part in path.parts)


def find_md(name_glob: str):
    """在当前目录下递归查找匹配 name_glob 的 .md 文件，跳过排除目录。"""
    results = []
    for p in Path(".").rglob(name_glob):
        if p.is_file() and not should_prune(p):
            results.append(p)
    return results


def find_in_dirs(dirs, name_glob: str, extra_filter=None):
    """在指定目录列表下递归查找文件。"""
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


# ---------- 输出 ----------

print(f"==== 文档治理审计: {Path('.').resolve()} ====")

# ---------- A. CLAUDE.md 单行 @*.md ----------

print()
print("## A. CLAUDE.md 是否都只有一行 @*.md（任意 @引用.md 格式均合规）")
a = 0
for c in find_md("CLAUDE.md"):
    content = c.read_text(encoding="utf-8", errors="replace").replace("\n", "").replace("\r", "").replace(" ", "").replace("\t", "")
    if not re.fullmatch(r"@.+\.md", content):
        print(f"  ❌ 非单行 @*.md: {c}")
        a += 1
if a == 0:
    print("  ✓ 全部合规")

# ---------- B. 悬空 @AGENTS.md ----------

print()
print("## B. 悬空 @AGENTS.md（引入但同级无 AGENTS.md）")
b = 0
for c in find_md("CLAUDE.md"):
    text = c.read_text(encoding="utf-8", errors="replace")
    if "@AGENTS.md" in text:
        if not (c.parent / "AGENTS.md").exists():
            print(f"  ❌ 悬空: {c}")
            b += 1
if b == 0:
    print("  ✓ 无悬空")

# ---------- C. 旧索引 / 工具注入块残留 ----------

print()
print("## C. 旧索引 / 工具注入块残留")

# 文件引用中出现裸 INDEX.md 或 OVERVIEW.md（前缀不是下划线/大写字母）
bare_index_ref = []
inject_block = []

bare_re = re.compile(r"(?<![_A-Z])OVERVIEW\.md|(?<![_A-Z])INDEX\.md")
inject_re = re.compile(r"<!--\s.*:start\s*-->")

for p in find_md("*.md"):
    if EXCL_RE.search(str(p)):
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    if bare_re.search(text):
        bare_index_ref.append(p)
    if p.name in ("AGENTS.md", "CLAUDE.md") and inject_re.search(text):
        inject_block.append(p)

# 文件名本身是裸 INDEX.md 或 OVERVIEW.md
bare_file = [p for p in find_md("INDEX.md") if not EXCL_RE.search(str(p))]
bare_file += [p for p in find_md("OVERVIEW.md") if not EXCL_RE.search(str(p))]

for p in bare_index_ref:
    print(f"  旧索引引用（裸 INDEX/OVERVIEW）: {p}")
for p in bare_file:
    print(f"  裸索引文件: {p}")
for p in inject_block:
    print(f"  注入块: {p}")

if not bare_index_ref and not bare_file and not inject_block:
    print("  ✓ 无残留（具名 *_INDEX.md 为合法二级索引，已忽略）")

# ---------- D. AGENTS.md 体量 ----------

print()
print("## D. AGENTS.md 体量（> 500 行考虑拆二级索引）")
for f in find_md("AGENTS.md"):
    try:
        # 与 wc -l 行为一致：统计换行符数量，末尾无换行的文件不多计一行
        content = f.read_bytes()
        n = content.count(b"\n")
    except OSError:
        n = 0
    flag = "  ⚠ 超阈值" if n > 500 else ""
    # wc -l 在 macOS 输出 "     223"（5前导空格），printf "%6s" 不截断，
    # 结合脚本前导两空格，合计缩进为 "       223"（7空格+数字）
    print(f"  {n:8d} 行  {f}{flag}")

# ---------- E. 孤儿文档 ----------

print()
print("## E. 孤儿文档（docs/ 与 specs/ 下，未被 根AGENTS.md ∪ 任意README.md ∪ 任意*_INDEX.md 引用）")

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
        print(f"  ❌ 孤儿: {f}")
        e += 1
if e == 0:
    print("  ✓ 无孤儿")

# ---------- F. 文件命名合规 ----------

print()
print("## F. 文件命名合规（确定性强的目录）")
f_count = 0

date_re = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")
review_re = re.compile(r"^.+-review\.md$")
space_re = re.compile(r" ")

# troubleshooting 下的排查记录（具名 *_INDEX.md / README 合法，跳过）
for p in find_in_dirs(["."], "*.md",
                      extra_filter=lambda p: "troubleshooting" in p.parts):
    bn = p.name
    if bn == "README.md" or bn.endswith("_INDEX.md"):
        continue
    if not date_re.match(bn):
        print(f"  ❌ 排查记录应为 YYYY-MM-DD-*.md: {p}")
        f_count += 1

# reviews 下的 review 台账（具名 *_INDEX.md / README 合法，跳过）
for p in find_in_dirs(["."], "*.md",
                      extra_filter=lambda p: "reviews" in p.parts):
    bn = p.name
    if bn == "README.md" or bn.endswith("_INDEX.md"):
        continue
    if not review_re.match(bn):
        print(f"  ❌ review 台账应为 *-review.md: {p}")
        f_count += 1

# 含空格文件名
for p in find_md("*.md"):
    if " " in p.name:
        print(f"  ❌ 文件名含空格: {p}")
        f_count += 1

if f_count == 0:
    print("  ✓ 命名合规")

# ---------- G. 预置折叠建议 ----------

print()
print("## G. 预置折叠建议（故障排查 / Review 台账 ≥3 篇但未折叠）")
g_suggest = 0

ts_files = find_in_dirs(["."], "*.md",
                        extra_filter=lambda p: "troubleshooting" in p.parts and date_re.match(p.name))
ts_count = len(ts_files)
ts_idx_list = find_in_dirs(["."], "TROUBLESHOOTING_INDEX.md")
ts_idx = ts_idx_list[0] if ts_idx_list else None

if ts_count >= 3 and not ts_idx:
    print(f"  💡 故障排查记录已有 {ts_count} 篇，建议折叠到 docs/troubleshooting/TROUBLESHOOTING_INDEX.md，根 AGENTS.md 留一条强路由（含「何时跳过 / 是否权威源」）")
    g_suggest += 1
elif ts_count >= 3 and ts_idx:
    print(f"  ✓ 故障排查（{ts_count} 篇）已折叠: {ts_idx}")
else:
    print(f"  ✓ 故障排查（{ts_count} 篇）未达折叠门槛")

rv_files = find_in_dirs(["."], "*.md",
                        extra_filter=lambda p: "reviews" in p.parts and review_re.match(p.name))
rv_count = len(rv_files)
rv_idx_list = find_in_dirs(["."], "REVIEW_INDEX.md")
rv_idx = rv_idx_list[0] if rv_idx_list else None

if rv_count >= 3 and not rv_idx:
    print(f"  💡 Review 台账已有 {rv_count} 篇，建议折叠到 docs/reviews/REVIEW_INDEX.md，根 AGENTS.md 留一条强路由（含「何时跳过 / 是否权威源」）")
    g_suggest += 1
elif rv_count >= 3 and rv_idx:
    print(f"  ✓ Review 台账（{rv_count} 篇）已折叠: {rv_idx}")
else:
    print(f"  ✓ Review 台账（{rv_count} 篇）未达折叠门槛")

if g_suggest == 0:
    print("  ✓ 无折叠建议")

# ---------- H. doc-init 联动检查 ----------

print()
print("## H. doc-init 联动检查（反向全局引用 / 自我导航残留 / 领域地图状态；与 doc-init 共享同一份检查逻辑，不在本脚本重复实现）")
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
            print(f"  ❌ 反向引用全局文件: {path}:{lineno} ({proj}) — {msg}")
            h += 1
        elif code == "self-navigation-in-doc":
            print(f"  ⚠ docs 内部自我导航残留: {path}:{lineno} ({proj})")
            h += 1

    if h == 0:
        print("  ✓ 无反向全局引用 / 自我导航残留")

    print("  doc-init 领域地图状态（若 domain_map_present=True，下方 Step 5 压缩禁止删除/折叠该项目根 AGENTS.md 里的「## 领域地图（doc-init）」与「## 待补充知识库（doc-init backlog）」两段）:")
    for line in lint_out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 6 and parts[0] == "SUMMARY":
            print(f"    {parts[5]}: {parts[3]}, {parts[4]}")
else:
    print(f"  ⏭ 未找到 doc-init（预期路径: {DOC_INIT_LINT}），跳过联动检查，以下三项需人工核对：")
    print("     - 根 AGENTS.md 是否反向引用了全局指令文件（不应出现 @~/.claude/... 之类）")
    print("     - docs/ 内部文档是否残留「何时该读/必读」自我导航句")
    print("     - 根 AGENTS.md 是否存在「## 领域地图（doc-init）」段（存在则该段及 backlog 段禁止在 Step 5 压缩中删除）")

# ---------- I. 压缩标识硬闸门 ----------

print()
print("## I. 压缩标识硬闸门（对应 SKILL.md Step 5/6 逐篇账目；仅 --compact-date 指定时启用）")
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
            print(f"  ❌ 缺本轮压缩标识（{COMPACT_DATE}）: {p}")
            i += 1
    if i == 0:
        print(f"  ✓ 范围内 docs/specs 文档均带本轮压缩标识（{COMPACT_DATE}）")
else:
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    print(f"  ⏭ 未指定 --compact-date，跳过（Step 2 只读阶段无需；Step 6 收尾用: audit.py <项目根> --compact-date {today}）")

# ---------- J. AGENTS.md 膨胀度量化与托管块（指标口径借鉴 prompt-audit 的 lint） ----------

print()
print("## J. AGENTS.md 膨胀度量化与托管块（口径: 字符×0.47 估 token，阈值均为经验值）")

EMPHASIS_WORDS = ("必须", "一律", "禁止", "务必", "不得")
TOKEN_COEF = 0.47  # 字符→token 实测系数，与 SKILL.md「系数来源」一致
MARKER_RE = re.compile(r"<!--\s*([\w.-]+)\s*:\s*(begin|start|end)(?:\s+[\w.\-/]+)?\s*-->")

def agents_md_metrics(path):
    """单份 AGENTS.md 的量化指标：字符/估算 token/规则条数/强调词密度 + 托管块清单。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    chars = len(text)
    rules = sum(
        1 for line in text.splitlines()
        if re.match(r"^[-*]\s+\S", line.strip()) or re.match(r"^\d+[.、]\s+\S", line.strip())
    )
    emphasis = sum(text.count(w) for w in EMPHASIS_WORDS)
    density = round(emphasis * 1000 / chars, 1) if chars else 0.0
    # 托管标记块：成对的 <!-- name:begin/end -->；Step 4 索引重建时须原样保留
    markers = [MARKER_RE.search(line) for line in text.splitlines()]
    opens, closes, managed = [], set(), []
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
    print("  ⏭ 未找到 AGENTS.md，跳过")
else:
    for rel, m in current_metrics.items():
        dens_flag = "  ⚠ 超阈值" if m["density"] > 10 else ""
        print(f"  {rel}: {m['chars']} 字符 ≈ {m['tokens']} token，规则 {m['rules']} 条，"
              f"强调词 {m['emphasis']} 次（{m['density']}/千字，阈值 10）{dens_flag}")
        if m["managed_blocks"]:
            print(f"    🔒 托管块（Step 4 索引重建时原样保留，不压不删）: {', '.join(m['managed_blocks'])}")
        if m["unmatched_markers"]:
            print(f"    ❌ 未配对的托管标记（人工检查是否残缺）: {', '.join(m['unmatched_markers'])}")

if args.save_metrics:
    import json
    Path(args.save_metrics).write_text(
        json.dumps(current_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  已保存基线 → {args.save_metrics}（Step 6 对比用: audit.py <项目根> --compare-metrics {args.save_metrics}）")

if args.compare_metrics:
    import json
    try:
        baseline = json.loads(Path(args.compare_metrics).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"  ❌ 基线文件不可读（{exc}），跳过对比")
        baseline = None
    if baseline is not None:
        print("  ---- 与基线对比（Step 2 → 当前）----")
        grew = 0
        for rel, cur in current_metrics.items():
            if rel not in baseline:
                print(f"  {rel}: 新增（≈ {cur['tokens']} token）")
                continue
            old = baseline[rel]
            delta = cur["tokens"] - old["tokens"]
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
            flag = "  ⚠ 膨胀（应 ≤ 基线，上升需在收工报告说明原因）" if delta > 0 else ""
            print(f"  {rel}: token {old['tokens']} → {cur['tokens']}（{arrow}{abs(delta)}），"
                  f"规则 {old['rules']} → {cur['rules']} 条，强调词 {old['density']} → {cur['density']}/千字{flag}")
            if delta > 0:
                grew += 1
        for rel in baseline:
            if rel not in current_metrics:
                print(f"  {rel}: 基线里有、现已不存在")
        if grew == 0 and current_metrics:
            print("  ✓ 全部 AGENTS.md 估算 token 未超基线")

# ---------- 小结 ----------

print()
if COMPACT_DATE:
    print(f"==== 小结: 非规范CLAUDE.md={a} 悬空={b} 孤儿={e} 命名违规={f_count} 压缩缺标识={i}（折叠建议={g_suggest}，doc-init联动={h}，不计成败）====")
else:
    print(f"==== 小结: 非规范CLAUDE.md={a} 悬空={b} 孤儿={e} 命名违规={f_count}（折叠建议={g_suggest}，doc-init联动={h}，压缩标识检查未启用，不计成败）====")
