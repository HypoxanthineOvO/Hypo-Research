"""Built-in meeting minutes templates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeetingTemplate:
    """A Markdown skeleton for one meeting type."""

    name: str
    display_name: str
    description: str
    skeleton: str


_TEMPLATES: dict[str, MeetingTemplate] = {
    "group_meeting": MeetingTemplate(
        name="group_meeting",
        display_name="组会/周报",
        description="适用于课题组周会、进展汇报和例会。",
        skeleton="""# 组会纪要 — {date}

## 参与者
{participants}

## 各人进展

### {person_1}
- **进展**：
- **问题/困难**：
- **导师反馈**：

### {person_2}
- **进展**：
- **问题/困难**：
- **导师反馈**：

## Action Items
- [ ] {person}: {task} — 截止 {deadline}

## 备忘
""",
    ),
    "paper_discussion": MeetingTemplate(
        name="paper_discussion",
        display_name="论文讨论",
        description="适用于论文精读、组内 paper reading 和相关工作讨论。",
        skeleton="""# 论文讨论 — {paper_title}

## 论文信息
- **标题**：{title}
- **作者**：{authors}
- **场地**：{venue} {year}

## 核心内容
- **问题**：论文要解决什么问题？
- **方法**：怎么做的？
- **结果**：主要结果和贡献

## 讨论要点
- {point_1}
- {point_2}

## 对我们工作的启发

## Action Items
- [ ] {task}
""",
    ),
    "project_discussion": MeetingTemplate(
        name="project_discussion",
        display_name="课题讨论",
        description="适用于课题方案、实验计划和阶段性技术路线讨论。",
        skeleton="""# 课题讨论 — {topic}

## 参与者
{participants}

## 进展回顾

## 讨论内容
### 问题 1：{issue}
- 讨论：
- 结论：

## 下一步计划

## 分工
- {person}: {task}
""",
    ),
    "consultation": MeetingTemplate(
        name="consultation",
        display_name="向学长/合作方请教",
        description="适用于向同门、学长或合作方请教技术问题。",
        skeleton="""# 请教纪要 — {topic}

## 背景
为什么要请教这个问题？

## 问答记录
### Q1：{question}
- **回答**：
- **补充**：

### Q2：{question}
- **回答**：
- **补充**：

## 关键收获

## 后续跟进
- [ ] {task}
""",
    ),
    "advisor_meeting": MeetingTemplate(
        name="advisor_meeting",
        display_name="向导师请教/沟通",
        description="适用于与导师一对一沟通、选题确认和关键决策同步。",
        skeleton="""# 与导师沟通 — {topic}

## 议题

## 问题与讨论
### 议题 1：{topic}
- **我的想法/问题**：
- **导师意见**：
- **结论/后续**：

## 关键决策
- {decision_1}
- {decision_2}

## Action Items
- [ ] {person}: {task} — 截止 {deadline}
""",
    ),
}


def get_template(name: str) -> MeetingTemplate:
    """Return a template by name, falling back to group_meeting."""
    return _TEMPLATES.get(name, _TEMPLATES["group_meeting"])


def list_templates() -> list[str]:
    """List built-in template names."""
    return list(_TEMPLATES)
