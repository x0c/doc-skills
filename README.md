# doc-skills

A set of [Claude Code](https://claude.ai/code) skills for bootstrapping and maintaining AI-readable project documentation systems.

**Languages:** [English](#english) | [中文](#中文)

---

<a id="english"></a>
## English

### Why this exists

AI coding agents waste time (and make mistakes) re-discovering the same project context every session: which module owns what, which fields lie, which side effects aren't visible in the code. `doc-skills` turns that tribal knowledge into a small, navigable documentation system that any agent can pick up cold — and keeps it from rotting as the codebase changes.

### Skills

#### `doc-init` — Documentation System Initialization

Bootstraps a full documentation system for a project from scratch. Runs a human-assisted intake, scans business domains, identifies hidden mechanics (framework conventions, implicit invariants, async side effects), optionally mines database schema and git history as evidence, and produces a navigable knowledge base usable by AI coding agents.

Use when entering a project with no doc structure, or when the global `AGENTS.md` lacks the documentation-management standard.

#### `doc-compact` — Documentation Compaction & Governance

Audits and compresses project documentation without losing behavioral information. Removes redundancy (duplicate reminders, dead links, historical changelog), rebuilds the root `AGENTS.md` index, enforces the single-line `CLAUDE.md` convention, and installs/upgrades the global documentation-management standard.

Use when docs are bloated, indexes break, `AGENTS.md` balloons, or `CLAUDE.md` gets polluted with extra content.

#### `doc-update` — End-of-Session Documentation Debrief

Distills reusable findings from a completed session into the right destination: skill files (cross-project patterns), project `AGENTS.md` (behavioral rules), or `docs/` (domain knowledge). Runs a relevance check first — no-ops cleanly when nothing worth persisting was found.

Use at the end of a session to persist discoveries so the next agent can hit the ground running.

### What it looks like in practice

**`doc-init` on a project with zero docs**

> Before: a Spring Boot service with no `AGENTS.md`, no `docs/`. New agents re-read the same payment-callback code every session and still miss that retries are idempotent only because of a DB unique constraint, not application logic.
>
> After: `AGENTS.md` has a one-hop "documentation map" routing "payment callback bug" → `docs/PAYMENT_KNOWLEDGE_BASE.md`, which states the idempotency mechanism explicitly as a "things that will surprise you" entry, plus a curl-based verification recipe. The next agent reads one file and can safely touch the callback handler.

**`doc-compact` on a project with bloated docs**

> Before: `AGENTS.md` has grown to 800 lines over a year — half of it a changelog of decisions already superseded, three dead links to deleted files, and the same "remember to update the index" reminder copy-pasted in four places.
>
> After: `AGENTS.md` drops to under 150 lines. Superseded decisions and dead links are gone; the index is regenerated from what's actually in `docs/`; the four duplicate reminders collapse into one. Nothing that changes a reader's action was removed — only the parts that didn't.

**`doc-update` at the end of a session**

> Before: an agent just spent an hour discovering that a feature flag silently disables retries in staging — not written down anywhere.
>
> After: `doc-update` checks whether this is a one-off (skip) or a reusable fact (write it once, to the one file that owns that topic), then appends a single sentence to the relevant knowledge base instead of leaving it to be re-discovered next time.

### Design principles

- **Behavior-preserving compression** — the core test for any sentence in a doc is: *does this change a reader's action or judgment?* If not, delete it.
- **Single source of truth** — volatile facts (version numbers, thresholds, current architecture) live in exactly one place; everything else links to it instead of repeating it.
- **Two-hop navigation** — any document must be reachable from the root `AGENTS.md` in at most two hops; three-level nesting is forbidden.
- **Product truth before code topology** — domain maps are anchored to what the product actually is (PRD, roadmap, or a one-line definition from the user), not to whatever modules happen to exist in the code. Code that doesn't map to a real product concept is flagged as candidate dead code, not promoted into a "domain."
- **Scripts collect facts, models make judgment calls** — anything mechanical (file inventory, coverage checks, nav-link validation) is scripted into a hard gate with a real exit code; business judgment (is this really a domain? is this doc still accurate?) stays with the agent. Soft "please don't be lazy" prose gets ignored by models — deterministic gates don't.
- **Environment-agnostic** — scripts detect which instruction files (`AGENTS.md`, `CLAUDE.md`, etc.) are actually in use rather than hardcoding paths.

### How to install

Copy the skill directories into your Claude Code skills folder (typically `~/.claude/skills/` or configured via `CLAUDE_SKILLS_DIR`), then restart Claude Code.

Each skill's entry point is its `SKILL.md`. The skills reference each other where applicable (`doc-compact` delegates installs to `doc-init`'s scripts), so keeping them together is recommended.

### License

MIT

---

<a id="中文"></a>
## 中文

### 为什么需要它

AI Coding Agent 每次接手项目都要重新摸清同一套上下文——哪个模块归谁管、哪些字段名不能按字面理解、哪些副作用代码里根本看不出来。这些只有老手才知道的经验如果不落盘，就只能靠 Agent 一次次重新踩坑。`doc-skills` 把这些经验沉淀成一套小而精、可导航的文档体系，让任何 Agent 接手都能直接开工，并且随代码演进持续保鲜，而不是写完就过期。

### Skills 说明

#### `doc-init` —— 项目文档体系初始化

从零为项目搭建完整文档体系：通过人机协同 Intake、业务域扫描、隐藏机制识别（框架隐性约定、不显式传参却生效的上下文、异步副作用），可选挖掘数据库结构和 Git 历史作为佐证，最终产出一套 AI Coding Agent 可直接使用的领域知识网络。

适用场景：项目完全没有文档体系，或全局 AI 指令文件缺少文档管理规范时。

#### `doc-compact` —— 文档整理与压缩

在不丢失行为信息的前提下审计并压缩项目文档：删除冗余（重复提醒、死链接、历史变更记录），重建根 `AGENTS.md` 索引，强制 `CLAUDE.md` 单行约定，并检查/安装全局文档管理规范。

适用场景：文档膨胀、索引失效、`AGENTS.md` 越写越长、`CLAUDE.md` 被混入杂质内容。

#### `doc-update` —— 会话收尾文档复盘

把一次会话里发现的可复用信息分流到正确位置：skill 文件（跨项目通用经验）、项目 `AGENTS.md`（行为规范）或 `docs/`（业务知识）。会先做一次相关性判断——如果本次会话没有值得沉淀的内容，会干净地不做任何改动。

适用场景：每次会话结束前，让下一个 Agent 能直接继承本次发现，不必从头摸索。

### 实际效果举例

**`doc-init`：项目从零文档到可被 Agent 直接接手**

> 改造前：一个 Spring Boot 支付服务没有 `AGENTS.md`、没有 `docs/`。每次新 Agent 接手支付回调相关需求，都要重新读一遍同一段代码，还是容易漏掉"重试天然幂等"其实靠的是数据库唯一约束，而不是业务逻辑兜底。
>
> 改造后：`AGENTS.md` 里的文档导航能把"支付回调 bug"一跳路由到 `docs/PAYMENT_KNOWLEDGE_BASE.md`，文档里把这条幂等机制明确写成"容易踩坑的隐性约束"，并配一段基于 curl 的验证方法。下一个 Agent 只读一份文档就能放心改回调逻辑。

**`doc-compact`：文档体系从臃肿到可读**

> 整理前：`AGENTS.md` 一年下来写到 800 行——一半是早就被推翻的历史决策记录，混着三条指向已删除文件的死链接，还有同一条"记得更新索引"的提醒被复制粘贴了四遍。
>
> 整理后：`AGENTS.md` 压缩到 150 行以内，过期决策和死链全部清除，索引按 `docs/` 实际内容重新生成，四份重复提醒合并成一条。删掉的只是不影响读者判断和行动的部分，真正的行为信息一条没丢。

**`doc-update`：会话收尾时把经验落盘**

> 收尾前：某个 Agent 花了一小时才发现某个 feature flag 会在预发环境悄悄关掉重试逻辑——这件事没有写在任何文档里。
>
> 收尾后：`doc-update` 先判断这是一次性现象还是值得沉淀的通用事实，如果值得，就一次性写进归属该主题的那一份文档（只写一句话），下一个 Agent 不用再重新踩这个坑。

### 设计哲学

- **保留行为信息的压缩**——判断一句话该不该留的唯一标准是：*它会不会改变读者的判断或行动？* 如果不会，就删。
- **单一权威来源**——版本号、阈值、当前架构这类易变事实只在一处维护，其余文档用链接引用，不复制粘贴。
- **两跳可达**——任何文档都必须能从根 `AGENTS.md` 在两跳以内到达，禁止三级以上嵌套索引。
- **产品真相先于代码拓扑**——领域地图必须先锚定产品本身是什么（PRD、路线图，或用户一句话给出的产品定义），而不是代码里恰好存在哪些模块。代码里有、但产品定义里找不到依据的功能，会被标记为候选死代码，而不是被坐实成一个业务领域。
- **机械事实交给脚本，业务判断留给模型**——能脚本化的机械检查（文件清单、覆盖度核验、导航链接校验）都做成有明确退出码的硬闸门；"这是不是真业务域""这份文档是否还准确"之类的判断留给 Agent。模型可以无视一段"请认真核查"的提醒文字，但无法无视一个返回非零退出码的脚本结论。
- **环境无关**——脚本会探测当前环境实际使用的指令文件（`AGENTS.md`、`CLAUDE.md` 等），而不是把路径写死。

### 安装方式

把对应 skill 目录复制到 Claude Code 的 skills 目录（通常是 `~/.claude/skills/`，或由 `CLAUDE_SKILLS_DIR` 指定的路径），然后重启 Claude Code。

每个 skill 的入口都是其 `SKILL.md`。三个 skill 之间存在相互引用（`doc-compact` 会调用 `doc-init` 的脚本完成安装动作），建议保持放在一起。

### License

MIT
