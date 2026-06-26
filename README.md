# doc-skills

> **Claude Code Skills** for bootstrapping, compacting, and maintaining AI-readable project documentation — so coding agents stop re-discovering the same project context every session.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skills-5A67D8?logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://python.org)

**Languages:** [English](#english) | [中文](#中文)

---

<a id="english"></a>
## English

### Why this exists

AI coding agents waste time (and make mistakes) re-discovering the same project context every session: which module owns what, which fields lie, which side effects aren't visible in the code. `doc-skills` turns that tribal knowledge into a small, navigable documentation system that any agent can pick up cold — and keeps it from rotting as the codebase changes.

### Quick Install

```bash
git clone https://github.com/x0c/doc-skills.git ~/.claude/skills/doc-skills

# Or copy individual skill folders
cp -r doc-skills/doc-init doc-skills/doc-compact doc-skills/doc-update ~/.claude/skills/
```

Restart Claude Code. Each skill's entry point is its `SKILL.md`.

---

### Skills

#### `doc-init` — Documentation System Initialization

Bootstraps a full documentation system for a project from scratch. The overall design follows a two-phase approach: **fix the global AI instruction file first, then build the project documentation**.

**Phase 1 — Global governance check**

Before touching any project files, `doc-init` detects the active global AI instruction files (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, etc.) and uses a versioned script (`insert_doc_governance.py`) to install or upgrade the doc-management standard. This ensures all future agents operate under consistent rules regardless of which project they're in.

**Phase 2 — Project documentation initialization**

The core logic runs in a pipeline of steps designed to prevent the two failure modes of most doc-generation tools: *producing skeleton docs that don't capture real behavior*, and *building a doc system that rots the moment the code changes*.

Key design decisions:

- **Product truth before code topology.** The agent first establishes a "product north star" (from PRD, roadmap, or user input) before scanning the code. This prevents the common mistake of treating every directory as a "domain" and creating docs that describe code structure rather than business behavior.

- **Multi-source evidence gathering.** Rather than only reading code, `doc-init` runs several specialized scripts in parallel: `project_inventory.py` (language stack, entry points, submodules), `depth_scanner.py` (state machines, concurrency patterns, idempotency signals, event flows), `git_history_miner.py` (hotspots, historical naming, fix/revert patterns), and optionally `db_miner.py` (table catalog, field semantics). Scripts collect mechanical facts; the model makes judgment calls about business boundaries.

- **Human-in-the-loop at the domain map stage.** After scanning, the agent proposes a full domain map — "domains" in the business sense, not directory names — and asks the user to confirm or adjust before writing anything. This prevents silent misclassification of the entire project.

- **Structured sub-agent prompts, not vague delegation.** When writing multiple domain knowledge bases in parallel, each sub-agent receives a structured prompt containing: domain definition, entry point list, depth scanner signals, canonical terminology, Q&A results, and quality gates. Vague prompts produce skeleton docs; structured prompts produce usable ones.

- **Coverage gate at completion.** `doc_coverage.py` computes a coverage score against a fingerprinted baseline (file count, language breakdown, submodule count, git SHA). A doc system that was 90% complete six months ago and hasn't been touched since the codebase doubled is not "complete" — it gets flagged as `STALE` and the gaps are surfaced for targeted updates.

- **Iterative deepening, not one-shot generation.** After the initial pass, the skill proposes at least three directions to deepen (uncovered domains, low-confidence constraints, unverified mechanisms) and lets the user pick. Each direction runs in parallel where possible.

Use when entering a project with no doc structure, or when the global instruction file lacks the documentation-management standard.

---

#### `doc-compact` — Documentation Compaction & Governance

Audits and compresses project documentation without losing behavioral information. The central design principle: **the only valid reason to keep a sentence is that it changes a reader's action or judgment**.

`doc-compact` runs a five-step pipeline:

1. **Global governance check** — same as `doc-init` Phase 1; ensures the instruction file is current before restructuring anything.

2. **Read-only audit** — `audit.sh` runs a battery of mechanical checks: CLAUDE.md single-line convention, dead links, orphan documents (files in `docs/` not reachable from root `AGENTS.md`), naming convention violations, and — crucially — detection of the `doc-init` domain map segment (which must be preserved untouched through all compaction).

3. **Two-level index decision** — by default, documentation stays flat (everything reachable from root `AGENTS.md` in one hop). A second-level index is only introduced when the navigation section itself has grown large enough to crowd out the behavioral rules. Two independent triggers: scale-driven (navigation takes up ≥ half of `AGENTS.md`) and type-driven (≥ 3 troubleshooting records or review logs).

4. **Structure repair** — fixes mechanical issues: CLAUDE.md back to single line, document naming to `SCREAMING_SNAKE_CASE` (knowledge bases) or `kebab-case` (design/review docs), navigation descriptions rewritten from "what this file contains" to "when you should read this", dead index entries removed.

5. **Compression (the core step)** — every document in `docs/` is reviewed against a graded set of deletion criteria. Low-risk removals (paraphrase, dead links, historical changelog, duplicate reminders, line-number references that should be method-name anchors) are done directly. High-risk removals (entire files, paragraphs with numbers or boundary conditions, structural changes) are listed for confirmation first. A `<!-- compressed YYYY-MM-DD -->` marker is written to every processed file, which becomes a hard gate in the final audit: any file missing the marker means it was skipped.

Use when docs are bloated, indexes break, `AGENTS.md` balloons past ~200 lines, or `CLAUDE.md` gets polluted with content.

---

#### `doc-update` — End-of-Session Documentation Debrief

Distills reusable findings from a completed session into the right destination. The design centers on a single question: *if a brand-new agent came in right now and only read the existing docs — no session history — could it take over and do the work?*

`doc-update` runs in four steps:

1. **Skip check** — if the session was pure Q&A, all findings already exist in docs, or the information is session-only, the skill exits cleanly. No-op is a valid outcome.

2. **Extract reusable findings** — reviews the session for: new business rules or architectural constraints, bugs hit (root cause + fix), validated patterns, user corrections or preferences, code changes that invalidated existing docs, and (critically) any navigation failures — cases where an agent searched for a document and couldn't find it or found the wrong one. Navigation failures are the most actionable signal: they mean the index description is missing a task-type trigger.

3. **Route to the right destination** — a decision tree maps finding types to target locations:
   - Cross-project patterns / scripts / checklists → the relevant skill file
   - Project-level behavioral constraints (mandatory flows, shutdown checklists, verification requirements) → root `AGENTS.md`
   - Domain knowledge / business rules / architecture → `docs/<DOMAIN>_KNOWLEDGE_BASE.md`
   - Design decisions → `docs/design/`
   - Troubleshooting records → `docs/troubleshooting/YYYY-MM-DD-*.md`

   For each touched document, the skill also checks the index entry: does the description cover the task type the agent actually used to find it? If the session surfaced a "can't find the doc for X" failure, that task type gets added to the description.

4. **Conflict resolution** — if the session established or corrected a fact that contradicts existing docs, the skill updates all affected documents in the current session scope. It does not do a full-repo consistency sweep (that's `doc-compact`'s job); it only fixes what this session actually touched.

Use at the end of any session where something worth persisting was discovered.

---

### How the three skills fit together

```
New project, no docs
        │
        ▼
   doc-init ──────────────────► AGENTS.md + docs/*.md (full domain map)
        │                              │
        │                    ongoing code changes
        │                              │
        ▼                              ▼
 each session ends              doc-update ──► incremental updates to docs/
                                       │
                               docs grow over time
                                       │
                                       ▼
                               doc-compact ──► compress, rebuild index, fix structure
```

`doc-init` builds the foundation once (or after a major restructure). `doc-update` keeps it current session by session. `doc-compact` restores readability when the system has grown or degraded.

---

### Project structure

```
doc-init/
├── SKILL.md                        # skill entry point
├── agents/                         # agent definitions (e.g. OpenAI-compatible)
├── references/                     # design guides read by the model at runtime
│   ├── human-intake.md             # how to run the user interview
│   ├── knowledge-network-design.md # KB/Guide boundaries, naming, budget rules
│   ├── scan-and-boundary-report.md # domain map format, coverage review
│   ├── document-templates.md       # KB/Guide templates and quality gates
│   ├── depth-patterns.md           # how to interpret depth_scanner signals
│   ├── sub-agent-prompt-template.md
│   ├── multi-source-evidence.md
│   ├── conflict-resolution.md
│   ├── git-history-mining.md
│   ├── operations-validation.md
│   ├── hidden-semantics/           # language-specific implicit behavior patterns
│   │   ├── java-kotlin.md
│   │   ├── python.md
│   │   ├── go.md
│   │   ├── javascript-typescript.md
│   │   └── csharp-dotnet.md
│   └── database-mining/            # DB catalog workflow and safety rules
│       ├── workflow.md
│       ├── critical-table-analysis.md
│       ├── evidence-pack-format.md
│       ├── config-discovery.md
│       └── safety-and-sampling.md
└── scripts/                        # deterministic fact-collection scripts
    ├── project_inventory.py        # language stack, entry points, submodules
    ├── depth_scanner.py            # state machines, concurrency, idempotency
    ├── doc_coverage.py             # coverage gate (COMPLETE / STALE / NEEDS_INIT)
    ├── doc_nav_lint.py             # navigation consistency check
    ├── upsert_agents_nav.py        # idempotent AGENTS.md nav entry writer
    ├── git_history_miner.py        # hotspots, fix/revert patterns
    ├── db_miner.py                 # database catalog and field semantics
    └── insert_doc_governance.py    # versioned global instruction file installer

doc-compact/
├── SKILL.md
├── references/
│   ├── compression-guide.md        # compression criteria, risk grades, repair scripts
│   └── standard.md                 # the eleven quality standards with full explanation
└── scripts/
    └── audit.sh                    # mechanical audit (dead links, naming, markers)

doc-update/
└── SKILL.md
```

### License

MIT

---

<a id="中文"></a>
## 中文

### 为什么需要它

AI Coding Agent 每次接手项目都要重新摸清同一套上下文——哪个模块归谁管、哪些字段名不能按字面理解、哪些副作用代码里根本看不出来。`doc-skills` 把这些经验沉淀成一套小而精、可导航的文档体系，让任何 Agent 接手都能直接开工，并随代码演进持续保鲜。

### 快速安装

```bash
git clone https://github.com/x0c/doc-skills.git ~/.claude/skills/doc-skills

# 或只复制需要的 skill
cp -r doc-skills/doc-init doc-skills/doc-compact doc-skills/doc-update ~/.claude/skills/
```

重启 Claude Code 即可，每个 skill 的入口是其 `SKILL.md`。

---

### Skills 说明

#### `doc-init` — 项目文档体系初始化

从零为项目搭建完整文档体系。整体设计遵循两阶段原则：**先修复全局 AI 指令文件，再初始化项目文档**。

**阶段一 — 全局规范校验**

在动项目文件之前，先探测生效中的全局 AI 指令文件（`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 等），用版本化脚本（`insert_doc_governance.py`）安装或升级文档管理规范。确保所有未来会话的 Agent 在一致的规则下运行。

**阶段二 — 项目文档初始化**

核心逻辑是一条防止两类典型失败的流水线：产出不反映真实行为的骨架文档，以及建好就烂、代码一变就失效。

关键设计决策：

- **产品真相先于代码拓扑。** Agent 在扫描代码前，先通过 PRD、路线图或用户输入确立"产品北极星"。防止把每个目录当成一个"领域"，产出描述代码结构而非业务行为的文档。

- **多源证据采集。** 并行运行多个专项脚本：`project_inventory.py`（语言栈、入口点、子模块）、`depth_scanner.py`（状态机、并发模式、幂等信号、事件流）、`git_history_miner.py`（热点、历史命名、fix/revert 规律），以及可选的 `db_miner.py`（表目录、字段语义）。脚本负责采集机械事实，模型负责判断业务边界。

- **领域地图阶段的人机交互门。** 扫描完成后，Agent 提出完整领域地图——业务概念维度的领域，不是目录名——并要求用户确认或调整，再开始写文档。

- **结构化 sub-agent 提示词，不是模糊委托。** 并行生成多个领域知识库时，每个 sub-agent 收到结构化提示词：域定义 + 入口清单 + depth scanner 信号 + 主称谓 + Q&A 结果 + 质量闸门。模糊提示词产出骨架，结构化提示词产出可用文档。

- **完成时的覆盖度闸门。** `doc_coverage.py` 对带指纹的基线（文件数、语言分布、子模块数、git SHA）计算覆盖率，代码大幅增长而文档未更新时标记为 `STALE`，缺口被明确列出供定向更新。

- **迭代深化，不是一次性生成。** 初始扫描后提议至少三个可深化方向，每个方向在条件允许时并行执行。

适用场景：项目没有文档体系，或全局指令文件缺少文档管理规范时。

---

#### `doc-compact` — 文档整理与压缩

在不丢失行为信息的前提下审计并压缩项目文档。核心原则：**保留一句话的唯一理由，是它会改变读者的判断或行动**。

五步流水线：

1. **全局规范校验** — 重整结构前先确认指令文件是最新版。
2. **只读审计** — `audit.sh` 检查 CLAUDE.md 单行约定、死链、孤儿文档、命名规范，以及 `doc-init` 领域地图段（必须原样保留）。
3. **二级索引判定** — 默认平铺，只有导航段膨胀到挤压行为规则时才引入二级索引。
4. **结构修复** — CLAUDE.md 还原单行、文档命名规范化、导航描述改写为"带着什么任务该读它"。
5. **压缩（核心步骤）** — 逐篇过删除判据，低风险直接删，高风险先列清单确认，每篇写入压缩标记作为硬闸门。

适用场景：文档膨胀、索引失效、`AGENTS.md` 超过约 200 行、`CLAUDE.md` 被混入杂质内容时。

---

#### `doc-update` — 会话收尾文档复盘

把可复用发现提炼到正确位置。核心问题：*如果全新 Agent 现在进来，只读现有文档、不看会话历史，能顺畅接手吗？*

四步流程：

1. **跳过判定** — 纯问答、发现已存在文档、或信息仅对当前会话有用，则干净退出。
2. **提取可复用发现** — 新业务规则、踩过的坑、代码变动导致的文档失效，以及导航失败（找不到文档或找错文档）。
3. **路由到正确位置** — 跨项目通用模式 → skill 文件；项目行为约束 → `AGENTS.md`；领域知识 → `docs/`。
4. **修正冲突旧文档** — 在当次会话范围内更新所有与本次确立事实相矛盾的文档。

适用场景：每次会话结束时，只要发现了值得沉淀的内容就运行。

---

### 三个 skill 的协作关系

```
新项目，无文档
        │
        ▼
   doc-init ──────────────────► AGENTS.md + docs/*.md（完整领域地图）
        │                              │
        │                    日常代码迭代
        │                              │
        ▼                              ▼
  每次会话结束              doc-update ──► 增量更新 docs/
                                       │
                               文档随时间增长
                                       │
                                       ▼
                               doc-compact ──► 压缩、重建索引、修复结构
```

`doc-init` 一次性建立基础。`doc-update` 逐会话保持同步。`doc-compact` 在文档膨胀或失序后恢复可读性。

---

### 项目结构

```
doc-init/
├── SKILL.md                          # skill 入口
├── agents/
├── references/                       # 模型运行时读取的设计指南
│   ├── human-intake.md               # 用户访谈流程
│   ├── knowledge-network-design.md   # KB/Guide 边界、命名、预算规则
│   ├── scan-and-boundary-report.md   # 领域地图格式、覆盖度复核
│   ├── document-templates.md         # KB/Guide 模板和质量闸门
│   ├── depth-patterns.md             # depth_scanner 信号解读
│   ├── sub-agent-prompt-template.md
│   ├── multi-source-evidence.md
│   ├── conflict-resolution.md
│   ├── git-history-mining.md
│   ├── operations-validation.md
│   ├── hidden-semantics/             # 各语言隐性行为模式
│   └── database-mining/              # 数据库 catalog 工作流与安全规则
└── scripts/                          # 确定性事实采集脚本
    ├── project_inventory.py          # 语言栈、入口点、子模块
    ├── depth_scanner.py              # 状态机、并发、幂等信号
    ├── doc_coverage.py               # 覆盖度闸门
    ├── doc_nav_lint.py               # 导航一致性检查
    ├── upsert_agents_nav.py          # 幂等写入 AGENTS.md 导航条目
    ├── git_history_miner.py          # 热点、fix/revert 规律
    ├── db_miner.py                   # 数据库目录和字段语义
    └── insert_doc_governance.py      # 版本化全局指令文件安装器

doc-compact/
├── SKILL.md
├── references/
│   ├── compression-guide.md          # 压缩判据、风险分级、修复脚本
│   └── standard.md                   # 十一条质量标准完整说明
└── scripts/
    └── audit.sh                      # 机械审计脚本

doc-update/
└── SKILL.md
```

### License

MIT
