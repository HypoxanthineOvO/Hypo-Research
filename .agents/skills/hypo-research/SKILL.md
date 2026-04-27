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

这个 bundle 打包了 Hypo-Research 的 17 个子工作流，适合通过 Codex 的 GitHub skill 安装流程一次性安装。

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

本 bundle 内嵌 17 个 skill 文档，位于 `skills/` 目录：

- `skills/hypo-survey/SKILL.md` — 综合调研
- `skills/hypo-search/SKILL.md` — 快速检索
- `skills/hypo-screen/SKILL.md` — 筛选分类
- `skills/hypo-cite/SKILL.md` — 引文图遍历
- `skills/hypo-idea/SKILL.md` — Research idea 生成
- `skills/hypo-challenge/SKILL.md` — Idea 苏格拉底式拷打
- `skills/hypo-experiment/SKILL.md` — 实验设计
- `skills/hypo-plan/SKILL.md` — 科研工作规划
- `skills/hypo-pilot/SKILL.md` — 娄萌萌全流程研究领航
- `skills/hypo-lint/SKILL.md` — LaTeX lint + auto-fix
- `skills/hypo-verify/SKILL.md` — 引用验证
- `skills/hypo-polish/SKILL.md` — 英文润色
- `skills/hypo-translate/SKILL.md` — 双语维护
- `skills/hypo-check/SKILL.md` — 一键检查 pipeline
- `skills/hypo-presubmit/SKILL.md` — 提交前统一检查 pipeline
- `skills/hypo-meeting/SKILL.md` — ASR 转写会议纪要 + 术语知识库
- `skills/hypo-review/SKILL.md` — 多角色模拟审稿

## 使用方式

当任务落在以下类别时，先读取对应子 skill，再执行：

- 文献调研：`hypo-survey` / `hypo-search` / `hypo-screen` / `hypo-cite`
- 创意与规划：`hypo-idea` / `hypo-challenge` / `hypo-experiment` / `hypo-plan` / `hypo-pilot`
- 论文写作：`hypo-lint` / `hypo-verify` / `hypo-polish` / `hypo-translate` / `hypo-check` / `hypo-presubmit`
- 会议纪要：`hypo-meeting`
- 模拟审稿：`hypo-review`

## CLI

```bash
uv run hypo-research <subcommand> [options]
```

可用子命令：`search`, `cite`, `idea`, `challenge`, `experiment`, `plan`, `pilot`, `lint`, `verify`, `check`, `presubmit`, `review`, `meeting`, `glossary`, `init`
