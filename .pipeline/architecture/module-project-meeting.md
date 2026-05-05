# Project, Meeting, And Workbench Modules

## 职责

项目模块管理多论文/多方向科研项目的持久上下文、进度、会议记录和 dashboard。会议模块把 ASR 转写整理为结构化会议纪要，并维护术语表。Workbench 提供交互式或桥接型使用界面。

## 主要文件

- `project/manager.py`、`project/models.py`：项目实体、持久化和生命周期管理。
- `project/progress.py`：项目进度记录与展示。
- `project/context.py`、`project/meetings.py`：项目上下文注入和会议资料关联。
- `project/dashboard.py`：项目状态展示。
- `meeting/processor.py`、`meeting/templates.py`、`meeting/glossary.py`、`meeting/inference.py`：会议纪要生成、模板、术语纠正和主题推断。
- `workbench/`：工作台模型、注册表、动作、TUI/Web/bridge。

## 设计约束

项目状态默认存放在用户级目录或配置指定目录，不应混入一次性检索输出。会议术语表属于用户/项目上下文，不能替代论文引用或检索结果事实来源。
