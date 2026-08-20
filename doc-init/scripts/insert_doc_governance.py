#!/usr/bin/env python3
"""
将「项目文档管理」规范插入全局 AI 指令文件真身，支持版本检测与自动升级。

用法：python3 insert_doc_governance.py <真身路径>

幂等行为：
- 若文件已含当前版本 -> 跳过。
- 若文件含旧版本（或无版本标记的旧章节）-> 自动替换为新版。
- 若无「项目文档管理」章节 -> 插入。

插入位置：文件末尾的 @RTK.md 等 @ 引用行之前；若无则追加到末尾。

版本升级方式：修改 STANDARD 后将 CURRENT_VERSION +1 即可；
下次 doc-init 运行时会自动检测并升级已部署的旧版本。

版本历史：
- v8：公司电脑独立演进（强提示规则 + 后果预告示例 + 量化折叠阈值），2026-08-13 推 GitHub。
- v9：家庭侧独立演进（强弱提示审计版），未推 GitHub。
- v10：2026-08-19 融合两线：以 v9 已部署的压缩态为底稿（含 v8 的量化折叠与强提示规则、
  v9 的 _standards/workspace-docs 覆盖范围），合入 v8 的后果预告示例；收工复盘条目内置
  「结论产生即落盘」第一触发点，模板自含、不依赖外部章节。
- v11：2026-08-20 用 prompt-audit 方法论自治理：登记规则三处归一（§2 立法/§4 删迁/§7 查账）、
  目录树 11 行压 1 行、双示例压单例、强度规则四弹合一、收工复盘去口语化；
  2096→1799 字符，语义逐项核对无损。
- v12：2026-08-20 去后果预告 + 导航两级强度：导航默认写内容/作用描述供模型自主判断，
  关键场景加「在 X 前必读」硬约束兑底；不写「不读的后果」——后果预告给模型开了权衡窗口
  （后果可接受 → 不读），反而稀释必读的无条件性。
"""

import sys
import re

CURRENT_VERSION = 12

STANDARD = f"""## 项目文档管理
<!-- doc-governance-version: {CURRENT_VERSION} -->

### 1. 核心规则

* 根 `AGENTS.md` 是项目文档唯一一级入口；长期文档须能从根一跳或两跳找到。
* 涉及业务规则、架构、故障、跨模块或不熟悉领域时，先检索相关项目文档再动手。
* **评审/审视/分析类**：相关规范是评判基准，须先读完再下结论；不得因代码未用某技术就跳过——评审要发现「该用却没用」。
* 禁止用内置记忆功能；需持久化的知识写入项目文档。
* 除 `README.md` 外，项目文档默认中文。
* 项目根 `CLAUDE.md` 默认仅一行：`@AGENTS.md`
* 新建/首次接手：若全局指令声明了跨项目技术规范位置，按主语言查找匹配文档并在根 `AGENTS.md` 顶部引用（未声明则跳过）。

### 2. 文档导航

项目根 `AGENTS.md` 须含「文档导航」，登记全部长期文档。

* 每条一行：路径 + 内容/作用描述（供模型自主判断是否读）；关键场景追加「在 X 前必读」硬约束提升触发率。
* 触发按「任务类型 / 业务领域」门控，不要按「代码是否已用到某技术」——后者会让评审漏掉「该用却没用」。
* **强度须匹配文档价值**：有代价/硬约束/踩坑的文档写「**必读**」，其余不加强调词；禁止弱提示（「涉及 X 前读」「先阅读」）、禁止批量弱导语包列表、同一文档多处引用不得降级（根写「必读」，子指针不许弱化为「前读」）。索引可达 ≠ 会被读取。不写「不读的后果」——后果预告等于告诉模型可以权衡后果决定读不读，反而稀释「必读」的无条件性。
* 强度规则覆盖一切实际入口：项目根导航、`_standards/*.md`、`workspace-docs/*/README.md`、全局指令导航。
* 新写文档立即登记并反向核对，禁止待办占位；指针尽量就近贴在支撑的那条规则旁，底部导航作兜底全集。

示例：

```md
- `docs/BILLING_KNOWLEDGE_BASE.md`：订阅/支付/额度扣减/账单状态流转的领域知识与状态机。改、评审或排查相关模块前必读。
```

`docs/` 布局惯例：`*_KNOWLEDGE_BASE.md`（领域知识库）、`*_GUIDE.md`（指南）、`design/`、`troubleshooting/`。

### 3. 二级索引

默认不建；能平铺就不折。当导航占根文过半，或排查/Review 台账 ≥3 篇时折叠到具名 `<DOMAIN>_INDEX.md`；根只留强路由（含「何时跳过 / 是否权威源」）；禁止三级以上索引。

### 4. 文档变更

* 迁移或重命名：搜全仓引用并同步更新；删除文档同步清导航。
* 新增长期文档类型：在根说明用途、位置与进入路径。

### 5. 单一来源

* 一概念/规则/机制只维护一个权威源；他处相对路径链接，不复制。
* 权威结论或主称谓更新后，所有旧叫法引用须同步改正；当场定不了则标「待确认」。

### 6. 什么该记录

应记：项目级行为规范与强制流程；业务规则/架构/领域知识；代码变动导致的设计与配置变化；可复用故障路径；Review 长期结论与约束。

不应记：代码已清楚表达的信息；git log/blame 能查到的历史；一次性现象；仅当前会话有用的信息；已在他处记录的规则。

### 7. 收工前检查

* 承诺文档是否完成；新增是否已登记；删迁后旧引用是否清理；新规则/机制/踩坑是否落盘。
* 向用户按路径列出新增/修改/删除及一句话说明；无改动须明确「本次未修改文档」。

| 信息类型 | 目标位置 |
|---|---|
| 跨项目通用模式 / 检查清单 / 脚本 | 对应 skill 文件 |
| 项目级行为规范 / 约束 / 强制流程 | 项目根 `AGENTS.md` |
| 项目业务规则 / 架构 / 领域知识 / 代码变动导致文档失效 | `docs/` 中的文档 |

**收工复盘（兜底）**：本会话有可复用发现或代码变动导致文档失效时，**必须调用 `doc-update` skill**；判定无需更新则按其「本次无需更新」收工。落盘不等收工：花搜索/调查/试错换来的可复用结论（根因+解法、选型裁定、工具行为变化等），拿到即记，未验证的标「待用户确认」。本条只接漏网之鱼。
"""

VERSION_RE = re.compile(r"<!--\s*doc-governance-version:\s*(\d+)\s*-->")
SECTION_RE = re.compile(r"(^|\n)(## 项目文档管理\b.*?)(?=\n## |\Z)", re.S)


def _get_installed_version(content: str) -> int | None:
    """返回文件中已安装的版本号，无版本标记时返回 None。"""
    m = VERSION_RE.search(content)
    return int(m.group(1)) if m else None


def _remove_section(content: str) -> str:
    """删除现有的「项目文档管理」章节（含内容直到下一个同级 ## 标题或文件末尾）。"""
    # 匹配从 ## 项目文档管理 到下一个 ## 同级标题（或文件末尾）
    pattern = re.compile(
        r"\n## 项目文档管理\b.*?(?=\n## |\Z)", re.S
    )
    return pattern.sub("", content)


def insert(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    installed = _get_installed_version(content)

    if installed is not None and installed >= CURRENT_VERSION:
        print(f"[跳过] 「项目文档管理」已是最新版本（v{installed}）：{path}")
        return

    if "## 项目文档管理" in content:
        if installed is None:
            print(f"[升级] 检测到无版本标记的旧章节，替换为 v{CURRENT_VERSION}：{path}")
        else:
            print(f"[升级] v{installed} -> v{CURRENT_VERSION}：{path}")
        content = _remove_section(content)
    else:
        print(f"[新增] 插入「项目文档管理」v{CURRENT_VERSION}：{path}")

    # 找插入点：第一个以 @ 开头的行（@RTK.md 等引用）之前
    m = re.search(r"\n(@\S+.*)", content)
    if m:
        insert_pos = m.start()
        before = content[:insert_pos]
        after = content[insert_pos:]
        new_content = before.rstrip("\n") + "\n\n" + STANDARD.rstrip("\n") + "\n\n" + after.lstrip("\n")
    else:
        new_content = content.rstrip("\n") + "\n\n" + STANDARD.rstrip("\n") + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[完成] 写入成功：{path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"用法：python3 {sys.argv[0]} <AI 指令文件真身路径>", file=sys.stderr)
        sys.exit(1)
    insert(sys.argv[1])
