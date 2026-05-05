# Data Flow

## Literature Flow

1. CLI/Skill 接收 query、年份、venue、source、输出目录等参数。
2. 参数规范化为 `SearchParams`，query expansion 记录为 `ExpansionTrace`。
3. `TargetedSearch` 或 `CitationTraverser` 调用 `core.sources` adapter。
4. Source adapter 返回标准 `PaperResult`。
5. Hook 在 search、dedup、verify、output 等阶段运行。
6. Deduplicator 合并跨源重复论文。
7. Verifier 标记 verified、single-source、unverified 或 suspicious。
8. Output 层写入 JSON、Markdown 和 BibTeX。

## Writing Flow

1. CLI/Skill 定位 `.tex` 主文件或项目目录。
2. `writing.project.resolve_project` 建立 LaTeX 项目上下文。
3. `writing.stats.extract_stats` 提取结构事实。
4. Lint 规则、fix 生成、BibTeX verify 和 venue 检查消费同一事实集。
5. `CheckReport` 或 presubmit report 输出摘要和问题列表。

## Review And Ideation Flow

1. 论文文本、PDF/LaTeX 结构或研究方向进入 review/ideation 模块。
2. Venue、severity、reviewer panel 或 idea strategy 决定 prompt 和评价维度。
3. 可选 literature context 调用检索模块补充相关工作。
4. 输出结构化 review、meta-review、revision roadmap、idea list、experiment matrix 或 plan。

## Project And Meeting Flow

1. 用户创建或选择科研项目。
2. 项目上下文聚合方向、论文、会议、进度和 rebuttal 材料。
3. Meeting processor 将 ASR 文本整理为纪要，并通过 glossary 修正术语。
4. Dashboard/status 展示项目进度和下一步。

## 主要外部边界

- Semantic Scholar、OpenAlex、arXiv 等远程文献 API。
- 本地 LaTeX 文件和 BibTeX 文件。
- 用户级项目目录，如 `~/.hypo-research/projects/`。
- Skill 安装目标，如 `.agents/skills/`、`.claude/skills/` 和 `~/.codex/prompts/`。
