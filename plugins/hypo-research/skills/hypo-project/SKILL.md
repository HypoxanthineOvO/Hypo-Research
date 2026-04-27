---
name: hypo-project
description: >
  Manage persistent research projects with multi-paper tracking, project
  context injection, milestones, meeting notes, dashboard, and imports.
license: MIT
---

# /hypo-project — 科研项目管理

为一个大方向建立持久化项目，把 survey、idea、challenge、experiment、plan、meeting 和 rebuttal 串起来。

## 适用场景

- 需要在一个方向下管理多篇论文
- 希望已有 survey、已否决 idea、导师会议决策影响下一次 idea 生成
- 需要项目级进度追踪、里程碑和 dashboard
- 需要把会议纪要转成上下文和 action items

## CLI

```bash
uv run hypo-research project create "Cryo Computing" --direction "低温 CMOS 架构加速"
uv run hypo-research project paper add cryo-computing "近似计算框架" --slug approx --venue ISCA
uv run hypo-research project status cryo-computing
```

## 工作流

1. 创建项目和论文。
2. 导入已有 survey / idea / challenge / experiment / plan。
3. 添加会议纪要，提取关键决策和 action items。
4. 使用 `project idea/challenge/experiment/plan/pilot` 注入项目上下文。
5. 用 `project status` 查看进度和风险。

## 数据位置

默认保存在：

```text
~/.hypo-research/projects/
```

可通过环境变量覆盖：

```bash
export HYPO_RESEARCH_PROJECTS_DIR=/path/to/projects
```
