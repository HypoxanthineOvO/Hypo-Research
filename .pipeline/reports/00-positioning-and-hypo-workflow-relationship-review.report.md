# M01 报告：Hypo-Research 与 Hypo-Workflow 关系审查

## 结论

推荐路径：**保持 Hypo-Research 独立仓库和独立产品语义，作为 Hypo-Workflow 的 research vertical plugin / vertical package 对接；短期只复用 Hypo-Workflow 的 Cycle、状态、报告、Knowledge、计划与执行规范，不把科研概念融合进 Hypo-Workflow 核心。**

备选路径：Hypo-Research 底层依赖 Hypo-Workflow 的文件契约和规划/执行生命周期，但通过 adapter 封装，避免让业务代码直接耦合 `.pipeline/`。

不推荐短期合并进 Hypo-Workflow。原因不是“研究不重要”，而是 Hypo-Workflow 的核心价值是跨领域 AI coding/workflow lifecycle；把论文、审稿、调研、会议等研究生语义放入核心，会显著污染非研究用户心智模型。

## 本地证据

- Hypo-Research 是宽研究工具包：CLI 顶层已有 `search`、`cite`、`lint`、`check`、`verify`、`review`、`idea`、`challenge`、`experiment`、`plan`、`pilot`、`project`、`meeting`、`glossary`、`presubmit`、`rebuttal` 等入口。
- Skill 层有 19 个顶层能力，覆盖文献调研、论文写作、模拟审稿、rebuttal、科研创意、会议和项目管理。
- Hypo-Workflow V9 架构原则明确：CLI 是 setup/sync 工具，不是 runner；`.pipeline/` 是跨平台 source of truth；宿主 Agent 执行工作；`core/` 只做 deterministic generation 和 contracts。
- Hypo-Research 当前也已经天然有科研项目生命周期：`ProjectStage`、`PaperStage`、`IdeaStatus`、会议、milestone、rebuttal 等模型。

## 四种关系方案评估

评分：5 最优，1 最差。污染风险分数越高代表越不污染非研究用户。

| 方案 | 非研究用户污染 | UX 一致性 | 代码复用 | 维护成本 | 迁移风险 | 研究表达力 | 插件生态 | 总评 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 融合进 Hypo-Workflow 核心 | 1 | 4 | 4 | 2 | 2 | 5 | 3 | 不推荐 |
| 作为 Hypo-Workflow 插件/vertical package | 5 | 4 | 4 | 4 | 4 | 5 | 5 | 推荐 |
| Hypo-Research 底层依赖 Hypo-Workflow | 4 | 3 | 5 | 3 | 3 | 5 | 4 | 可作为第二阶段 |
| 完全独立，仅文档/指令层对接 | 5 | 2 | 1 | 4 | 5 | 4 | 2 | 保守但浪费复用 |

## 为什么不直接合并

Hypo-Workflow 应保留“通用工作流核”：Cycle、Plan、Patch、Audit、Debug、Showcase、Knowledge、Report、adapter、file guard、execution lease。Hypo-Research 的高频概念是论文、领域、实验、venue、reviewer、rebuttal、bib、PDF、figure、claim、dataset。这些概念对研究生很自然，但对普通 coding workflow 用户是噪音。

如果直接合并，Hypo-Workflow 的 guide 和 docs 会被迫解释研究场景；这会降低它作为通用 Agent workflow substrate 的清晰度。

## 哪些可抽象进 Hypo-Workflow

可进入通用层：

- `workflow_kind=research` 作为可选 vertical workflow kind，不默认暴露。
- `evidence_matrix`、`source_bundle`、`artifact_index` 这类通用证据记录结构。
- 多源调研中的“候选池、筛选、证据引用、置信度”模式，可泛化到 audit/debug/research。
- Report template system 和 Knowledge Ledger 的 richer evidence indexing。

应留在 Hypo-Research：

- 论文检索、BibTeX、venue、reviewer persona、LaTeX lint、PDF paper parsing、rebuttal。
- PhD/研究生项目状态机。
- 研究方向、idea、challenge、experiment、paper stage。

## 推荐架构

```text
Hypo-Workflow
  core lifecycle: Cycle / Plan / State / Reports / Knowledge / Adapters
  optional workflow_kind: research

Hypo-Research
  product semantics: literature / read paper / write paper / review / project
  depends on or integrates with Hypo-Workflow through a thin adapter
  writes reports and durable project knowledge using compatible contracts
```

短期：插件/vertical package。  
中期：把 `.hypo-research` 项目记忆映射到 `.pipeline/knowledge` 和 report artifacts。  
长期：如果 research workflow 被证明有通用价值，再把少量 primitives 上移到 Hypo-Workflow。

## 后续决策

1. 定义 `research` vertical 的最小接口：project context、evidence bundle、report pack。
2. 设计 Hypo-Research router，不让用户记 19 个 Skill。
3. 把 PDF/full-text 作为 Hypo-Research 独立能力，不进入 Hypo-Workflow 核心。
4. 将 Hypo-Workflow 只作为 orchestration substrate，而不是科研产品本体。
