---
name: hypo-research
description: >
  Aggregate Codex skill bundle for academic literature search, screening,
  citation traversal, research ideation, experiment planning, LaTeX lint/fix,
  bibliography verification, polishing, translation, and one-command paper checks.
license: MIT
---

# hypo-research — 学术科研辅助工具链

## 概述

这个 bundle 打包了 Hypo-Research 的科研工作流，适合通过 Codex 的 GitHub skill 安装流程一次性安装。

一线入口是 `hypo-guide`、`hypo-check`、`hypo-review`、`hypo-read`：

- 不确定路径时先用 `hypo-guide`，再进入直接命令。
- 论文快投优先 `hypo-check` / `check --full`。
- 模拟审稿用 `hypo-review` / `review`。
- PDF 结构化阅读用 `hypo-read` / `read ingest|outline|extract`。

其他 expert skills 仍然是一等入口，适合明确任务或深度串联。

## 安装

当前 Codex `skill-installer` 的稳定安装方式是 GitHub repo/path，而不是仓库外部的裸名字注册。

推荐安装命令：

```text
$skill-installer https://github.com/HypoxanthineOvO/Hypo-Research/tree/main/.agents/skills/hypo-research
```

如果使用底层脚本，对应等价命令是：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo HypoxanthineOvO/Hypo-Research \
  --path .agents/skills/hypo-research
```

## Skills

本 bundle 内嵌 skill 文档，位于 `skills/` 目录：

- `skills/hypo-guide/SKILL.md` — 自然语言路由入口
- `skills/hypo-read/SKILL.md` — PDF 结构化阅读和 evidence cards
- `skills/hypo-survey/SKILL.md` — 综合调研
- `skills/hypo-search/SKILL.md` — 快速检索
- `skills/hypo-screen/SKILL.md` — 筛选分类
- `skills/hypo-cite/SKILL.md` — 引文图遍历
- `skills/hypo-idea/SKILL.md` — Research idea 生成
- `skills/hypo-challenge/SKILL.md` — Idea 苏格拉底式拷打
- `skills/hypo-experiment/SKILL.md` — 实验设计
- `skills/hypo-plan/SKILL.md` — 科研工作规划
- `skills/hypo-pilot/SKILL.md` — 娄萌萌全流程研究领航
- `skills/hypo-project/SKILL.md` — 持久化科研项目管理
- `skills/hypo-rebuttal/SKILL.md` — Rebuttal 生成
- `skills/hypo-lint/SKILL.md` — LaTeX lint + auto-fix
- `skills/hypo-verify/SKILL.md` — 引用验证
- `skills/hypo-polish/SKILL.md` — 英文润色
- `skills/hypo-translate/SKILL.md` — 双语维护
- `skills/hypo-check/SKILL.md` — 一键检查 pipeline
- `skills/hypo-presubmit/SKILL.md` — 兼容/legacy 提交前检查 wrapper
- `skills/hypo-meeting/SKILL.md` — ASR 转写会议纪要 + 术语知识库
- `skills/hypo-review/SKILL.md` — 多角色模拟审稿

## 使用方式

当任务落在以下类别时，先读取对应子 skill，再执行：

- 路由入口：`hypo-guide`
- PDF 阅读：`hypo-read`
- 文献调研：`hypo-survey` / `hypo-search` / `hypo-screen` / `hypo-cite`
- 创意与规划：`hypo-idea` / `hypo-challenge` / `hypo-experiment` / `hypo-plan` / `hypo-pilot`
- 项目管理：`hypo-project`
- 投稿回复：`hypo-rebuttal`
- 论文写作：`hypo-lint` / `hypo-verify` / `hypo-polish` / `hypo-translate` / `hypo-check` / `hypo-presubmit`
- 会议纪要：`hypo-meeting`
- 模拟审稿：`hypo-review`

## CLI

```bash
uv run hypo-research <subcommand> [options]
```

可用子命令：`guide`, `read`, `search`, `cite`, `idea`, `challenge`, `experiment`, `plan`, `pilot`, `project`, `rebuttal`, `lint`, `verify`, `check`, `presubmit`, `review`, `meeting`, `glossary`, `init`
