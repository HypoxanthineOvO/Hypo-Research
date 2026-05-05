# Hypo-Research Architecture Baseline

## 项目概览

Hypo-Research 是一个面向学术科研流程的 Python 工具包，既作为 `hypo-research` CLI 运行，也作为 Codex/Claude Skill bundle 被安装和调用。核心能力覆盖文献检索、引用图扩展、论文写作检查、引用真实性验证、提交前检查、模拟审稿、rebuttal、科研创意、实验/计划生成、会议纪要和项目追踪。

## 技术栈

- 语言：Python 3.11+
- CLI：Click
- 结构化模型：Pydantic v2
- 终端输出：Rich
- HTTP/API：httpx、feedparser
- 测试：pytest、pytest-asyncio、respx
- 包管理：uv
- 包入口：`hypo-research = hypo_research.cli:main`

## 目录结构

```text
src/hypo_research/
  cli.py              # CLI 聚合入口
  core/               # 论文模型、去重、限速、验证、多源 API 适配
  survey/             # 定向与多 query 文献检索流程
  cite/               # 引用/被引图遍历
  hooks/              # 搜索后 BibTeX、报告、验证自动 hook
  output/             # JSON、Markdown、BibTeX 输出
  writing/            # LaTeX 结构检查、fix、verify、统计、venue 配置
  presubmit/          # 提交前统一检查与报告
  review/             # PDF/LaTeX 解析、审稿 persona、报告和 venue
  ideation/           # idea、challenge、experiment、plan、pilot
  project/            # 多项目科研管理、进度、会议上下文、dashboard
  meeting/            # ASR 会议纪要、模板、术语表
  workbench/          # 交互式工作台/桥接层
  prompts/            # 内置 prompt 模板
skills/               # 对外发布的 Codex/Claude Skills
tests/                # pytest 单元与集成测试
```

## 运行入口

主入口是 `src/hypo_research/cli.py`。该文件集中定义顶层 Click group、参数解析、配置加载、各领域命令注册和输出渲染。领域模块应把业务逻辑放在各自包内，CLI 只负责参数规范化、调用和用户可见输出。

## 架构模式

- 数据以 `core.models.PaperResult`、`SearchParams`、`SurveyMeta`、`SearchResult` 等模型在检索、输出、hook 和验证层间传递。
- 外部数据源通过 `core.sources.BaseSource` 适配，并由检索/引用流程组合调用。
- 写作流程以 LaTeX 项目解析、结构统计、fix 生成、引用验证和报告聚合组成。
- 审稿与创意流程以 prompt/persona/venue 配置和结构化报告模型为主，不直接承担通用 CLI 状态。
- 项目管理和会议模块维护用户科研项目上下文，属于应用层能力，不应污染核心检索模型。

## 关键接口

- `hypo_research.cli:main`：CLI 入口。
- `hypo_research.survey.targeted.TargetedSearch`：单 query 与多 query 文献检索主流程。
- `hypo_research.cite.CitationTraverser`：引用图扩展入口。
- `hypo_research.writing.check.run_check`：论文写作质量流水线。
- `hypo_research.presubmit.run_presubmit`：提交前检查聚合入口。
- `hypo_research.review.*`：论文解析、审稿 persona、meta-review 和报告生成。
- `hypo_research.ideation.cli.IDEATION_COMMANDS`：科研创意相关 CLI 命令集合。
- `hypo_research.project.cli.PROJECT_COMMANDS`：项目管理 CLI 命令集合。

## 维护边界

- 领域逻辑优先落在 `src/hypo_research/<domain>/`，避免继续膨胀 `cli.py`。
- 新外部论文源应实现 `BaseSource`，并返回标准 `PaperResult`。
- 新输出格式应放在 `output/`，不要把文件格式写入检索流程。
- LaTeX 检查规则应通过 `writing/stats.py`、`writing/fixer.py`、`writing/severity.py` 和配置层接入。
- Skill 文档位于 `skills/`，CLI 与 Skill 文档应保持功能名称和参数语义一致。

## 相关文档

- 模块概览：`module-core.md`、`module-literature.md`、`module-writing.md`、`module-review-ideation.md`、`module-project-meeting.md`
- 数据流：`data-flow.md`
- 架构决策：`decisions.md`
