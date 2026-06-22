#!/usr/bin/env bash
# 文档治理只读审计 —— 对应 SKILL.md Step 2。
# 只读、不改任何文件；自动排除第三方 / 构建产物 / 备份 / git 目录。
# 用法: audit.sh [项目根] [--compact-date YYYY-MM-DD]   默认当前目录；一次只审计一个项目。
#   --compact-date：仅 Step 6 收尾核对压缩账目时传，启用检查 I（逐篇压缩标识硬闸门）；
#                   Step 2 只读审计阶段不传，跳过该检查。
#
# 退出码不表达成败，结论看输出末尾「小结」三个计数与各节 ❌ 行。

PROJ="."
COMPACT_DATE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --compact-date) COMPACT_DATE="$2"; shift 2;;
    --compact-date=*) COMPACT_DATE="${1#*=}"; shift;;
    *) PROJ="$1"; shift;;
  esac
done
# 先在 cd 之前算好脚本自身绝对路径，避免后面用相对路径找 doc-init 时被 cd 带偏。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOC_INIT_LINT="$SCRIPT_DIR/../../doc-init/scripts/doc_nav_lint.py"
cd "$PROJ" || { echo "无法进入目录: $PROJ" >&2; exit 2; }

# 统一排除：第三方 / 构建产物 / 备份 / worktree
PRUNE='-name node_modules -o -name target -o -name build -o -name dist -o -name out -o -name .build -o -name .git -o -name .claude -o -name .stversions -o -name vendor'
find_md() { find . \( $PRUNE \) -prune -o -type f -name "$1" -print 2>/dev/null; }

echo "==== 文档治理审计: $(pwd) ===="

echo
echo "## A. CLAUDE.md 是否都只有一行 @*.md（任意 @引用.md 格式均合规）"
a=0
while IFS= read -r c; do
  [ -z "$c" ] && continue
  content=$(tr -d '[:space:]' < "$c")
  if ! echo "$content" | grep -qE '^@.+\.md$'; then
    echo "  ❌ 非单行 @*.md: $c"; a=$((a+1))
  fi
done < <(find_md CLAUDE.md)
[ "$a" = 0 ] && echo "  ✓ 全部合规"

echo
echo "## B. 悬空 @AGENTS.md（引入但同级无 AGENTS.md）"
b=0
while IFS= read -r c; do
  [ -z "$c" ] && continue
  d=$(dirname "$c")
  if grep -q '@AGENTS.md' "$c" && [ ! -f "$d/AGENTS.md" ]; then
    echo "  ❌ 悬空: $c"; b=$((b+1))
  fi
done < <(find_md CLAUDE.md)
[ "$b" = 0 ] && echo "  ✓ 无悬空"

echo
echo "## C. 旧索引 / 工具注入块残留"
# 注意：合法具名二级索引（*_INDEX.md，如 DESIGN_INDEX.md）不报；
# 只检测裸 INDEX.md / OVERVIEW.md（与根竞争的散索引）。
EXCL='node_modules|/target/|/build/|/dist/|/out/|/\.build/|/\.git/|/\.claude/|/\.stversions/|/vendor/'
# 文件引用中出现裸 INDEX.md 或 OVERVIEW.md（前后不是下划线/字母，排除 _INDEX.md 前缀形式）
c1=$(grep -rIlE --include='*.md' '(^|[^_A-Z])OVERVIEW\.md|(^|[^_A-Z])INDEX\.md' . 2>/dev/null | grep -vE "$EXCL")
# 文件名本身就是裸 INDEX.md 或 OVERVIEW.md
c1f=$(find . \( $PRUNE \) -prune -o \( -name 'INDEX.md' -o -name 'OVERVIEW.md' \) -type f -print 2>/dev/null)
c2=$(grep -rIl --include='AGENTS.md' --include='CLAUDE.md' -e '<!-- .*:start -->' . 2>/dev/null | grep -vE "$EXCL")
[ -n "$c1" ]  && echo "$c1"  | sed 's/^/  旧索引引用（裸 INDEX\/OVERVIEW）: /'
[ -n "$c1f" ] && echo "$c1f" | sed 's/^/  裸索引文件: /'
[ -n "$c2" ]  && echo "$c2"  | sed 's/^/  注入块: /'
[ -z "$c1$c1f$c2" ] && echo "  ✓ 无残留（具名 *_INDEX.md 为合法二级索引，已忽略）"

echo
echo "## D. AGENTS.md 体量（> 500 行考虑拆二级索引）"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  n=$(wc -l < "$f")
  flag=""; [ "$n" -gt 500 ] && flag="  ⚠ 超阈值"
  printf "  %6s 行  %s%s\n" "$n" "$f" "$flag"
done < <(find_md AGENTS.md)

echo
echo "## E. 孤儿文档（docs/ 与 specs/ 下，未被 根AGENTS.md ∪ 任意README.md ∪ 任意*_INDEX.md 引用）"
# 关键：索引文本 = 根 AGENTS.md + 全部 README.md + 全部 *_INDEX.md（具名二级索引）。
# 若只用根 AGENTS.md+README，做了两级索引的项目会把所有二级文档误报为孤儿。
# *_INDEX.md 自身像 README 一样跳过（它被根引用，不需要被自己引用）。
idxfiles=$( { [ -f AGENTS.md ] && echo AGENTS.md
              find docs specs -name 'README.md' 2>/dev/null
              find docs specs -name '*_INDEX.md' 2>/dev/null; } )
idx=$(cat $idxfiles 2>/dev/null)
e=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  base=$(basename "$f")
  [ "$base" = "README.md" ] && continue
  # 具名二级索引自身不报孤儿（它经根 AGENTS.md 引用即合规）
  case "$base" in *_INDEX.md) continue;; esac
  if ! printf '%s' "$idx" | grep -qF "$base"; then
    echo "  ❌ 孤儿: $f"; e=$((e+1))
  fi
done < <(find docs specs \( $PRUNE \) -prune -o -type f -name '*.md' -print 2>/dev/null)
[ "$e" = 0 ] && echo "  ✓ 无孤儿"

echo
echo "## F. 文件命名合规（确定性强的目录）"
f=0
# 排查记录: */troubleshooting/*.md 必须 YYYY-MM-DD-*.md
while IFS= read -r p; do
  [ -z "$p" ] && continue
  case "$(basename "$p")" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.md) ;;
    *) echo "  ❌ 排查记录应为 YYYY-MM-DD-*.md: $p"; f=$((f+1));;
  esac
done < <(find . \( $PRUNE \) -prune -o -path '*/troubleshooting/*.md' -type f -print 2>/dev/null)
# review 台账: */reviews/**/*.md 必须 *-review.md
while IFS= read -r p; do
  [ -z "$p" ] && continue
  bn=$(basename "$p"); [ "$bn" = "README.md" ] && continue
  case "$bn" in
    *-review.md) ;;
    *) echo "  ❌ review 台账应为 *-review.md: $p"; f=$((f+1));;
  esac
done < <(find . \( $PRUNE \) -prune -o -path '*/reviews/*.md' -type f -print 2>/dev/null)
# 任何含空格的 .md 文件名
while IFS= read -r p; do
  [ -z "$p" ] && continue
  echo "  ❌ 文件名含空格: $p"; f=$((f+1))
done < <(find . \( $PRUNE \) -prune -o -type f -name '*.md' -name '* *' -print 2>/dev/null)
[ "$f" = 0 ] && echo "  ✓ 命名合规"

echo
echo "## G. 预置折叠建议（故障排查 / Review 台账 ≥3 篇但未折叠）"
# 建议性检查，不计入小结成败计数
g_suggest=0
# 故障排查
ts_count=$(find . \( $PRUNE \) -prune -o -path '*/troubleshooting/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.md' -type f -print 2>/dev/null | wc -l | tr -d ' ')
ts_idx=$(find . \( $PRUNE \) -prune -o -name 'TROUBLESHOOTING_INDEX.md' -type f -print 2>/dev/null | head -1)
if [ "$ts_count" -ge 3 ] && [ -z "$ts_idx" ]; then
  echo "  💡 故障排查记录已有 ${ts_count} 篇，建议折叠到 docs/troubleshooting/TROUBLESHOOTING_INDEX.md，根 AGENTS.md 留一条强路由（含「何时跳过 / 是否权威源」）"
  g_suggest=$((g_suggest+1))
elif [ "$ts_count" -ge 3 ] && [ -n "$ts_idx" ]; then
  echo "  ✓ 故障排查（${ts_count} 篇）已折叠: $ts_idx"
else
  echo "  ✓ 故障排查（${ts_count} 篇）未达折叠门槛"
fi
# Review 台账
rv_count=$(find . \( $PRUNE \) -prune -o -path '*/reviews/*-review.md' -type f -print 2>/dev/null | wc -l | tr -d ' ')
rv_idx=$(find . \( $PRUNE \) -prune -o -name 'REVIEW_INDEX.md' -type f -print 2>/dev/null | head -1)
if [ "$rv_count" -ge 3 ] && [ -z "$rv_idx" ]; then
  echo "  💡 Review 台账已有 ${rv_count} 篇，建议折叠到 docs/reviews/REVIEW_INDEX.md，根 AGENTS.md 留一条强路由（含「何时跳过 / 是否权威源」）"
  g_suggest=$((g_suggest+1))
elif [ "$rv_count" -ge 3 ] && [ -n "$rv_idx" ]; then
  echo "  ✓ Review 台账（${rv_count} 篇）已折叠: $rv_idx"
else
  echo "  ✓ Review 台账（${rv_count} 篇）未达折叠门槛"
fi
[ "$g_suggest" = 0 ] && echo "  ✓ 无折叠建议"

echo
echo "## H. doc-init 联动检查（反向全局引用 / 自我导航残留 / 领域地图状态；与 doc-init 共享同一份检查逻辑，不在本脚本重复实现）"
h=0
if [ -f "$DOC_INIT_LINT" ]; then
  lint_out=$(python3 "$DOC_INIT_LINT" --root . --recursive --format text 2>/dev/null)
  while IFS=$'\t' read -r severity code path line msg proj; do
    [ -z "$severity" ] && continue
    case "$code" in
      global-ref-in-project-agents)
        echo "  ❌ 反向引用全局文件: $path:$line ($proj) — $msg"; h=$((h+1));;
      self-navigation-in-doc)
        echo "  ⚠ docs 内部自我导航残留: $path:$line ($proj)"; h=$((h+1));;
    esac
  done <<< "$lint_out"
  [ "$h" = 0 ] && echo "  ✓ 无反向全局引用 / 自我导航残留"
  echo "  doc-init 领域地图状态（若 domain_map_present=True，下方 Step 5 压缩禁止删除/折叠该项目根 AGENTS.md 里的「## 领域地图（doc-init）」与「## 待补充知识库（doc-init backlog）」两段）:"
  echo "$lint_out" | awk -F'\t' '$1=="SUMMARY"{print "    "$6": "$4", "$5}'
else
  echo "  ⏭ 未找到 doc-init（预期路径: ${DOC_INIT_LINT}），跳过联动检查，以下三项需人工核对："
  echo "     - 根 AGENTS.md 是否反向引用了全局指令文件（不应出现 @~/.claude/... 之类）"
  echo "     - docs/ 内部文档是否残留「何时该读/必读」自我导航句"
  echo "     - 根 AGENTS.md 是否存在「## 领域地图（doc-init）」段（存在则该段及 backlog 段禁止在 Step 5 压缩中删除）"
fi

echo
echo "## I. 压缩标识硬闸门（对应 SKILL.md Step 5/6 逐篇账目；仅 --compact-date 指定时启用）"
# 范围：docs/ 与 specs/ 下的内容文档（与 E 一致地跳过 README.md 和具名 *_INDEX.md）。
# 凭据：每篇被 Step 5 处理过的文档末尾应有 `<!-- 该文档整理/压缩于 <COMPACT_DATE> -->`。
# 缺本轮日期标识 = 本轮漏审，必须补审后才算完成 —— 把「模型自陈都审过了」变成机器可验证。
i=0
if [ -n "$COMPACT_DATE" ]; then
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    base=$(basename "$p")
    [ "$base" = "README.md" ] && continue
    case "$base" in *_INDEX.md) continue;; esac
    if ! grep -qF "整理/压缩于 $COMPACT_DATE" "$p"; then
      echo "  ❌ 缺本轮压缩标识（$COMPACT_DATE）: $p"; i=$((i+1))
    fi
  done < <(find docs specs \( $PRUNE \) -prune -o -type f -name '*.md' -print 2>/dev/null)
  [ "$i" = 0 ] && echo "  ✓ 范围内 docs/specs 文档均带本轮压缩标识（$COMPACT_DATE）"
else
  echo "  ⏭ 未指定 --compact-date，跳过（Step 2 只读阶段无需；Step 6 收尾用: audit.sh <项目根> --compact-date $(date +%F)）"
fi

echo
if [ -n "$COMPACT_DATE" ]; then
  echo "==== 小结: 非规范CLAUDE.md=$a 悬空=$b 孤儿=$e 命名违规=${f} 压缩缺标识=${i}（折叠建议=${g_suggest}，doc-init联动=${h}，不计成败）===="
else
  echo "==== 小结: 非规范CLAUDE.md=$a 悬空=$b 孤儿=$e 命名违规=${f}（折叠建议=${g_suggest}，doc-init联动=${h}，压缩标识检查未启用，不计成败）===="
fi
