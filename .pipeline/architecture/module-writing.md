# Writing, Verification, And Presubmit Modules

## 职责

写作模块维护 LaTeX 项目解析、结构 lint、自动修复预览/应用、BibTeX 元数据验证、venue profile 和提交前聚合检查。

## 主要文件

- `writing/project.py`：解析单文件或多文件 LaTeX 项目。
- `writing/stats.py`：提取章节、float、label/ref/citation、BibTeX 等结构统计。
- `writing/check.py`：聚合 lint、fix、verify 和报告保存。
- `writing/fixer.py`：生成并应用可自动修复项。
- `writing/verify.py`、`writing/bib_parser.py`：BibTeX 解析与真实性/元数据验证。
- `writing/config.py`、`writing/venue.py`、`writing/severity.py`：项目配置、venue profile、规则严重度。
- `presubmit/runner.py`、`presubmit/report.py`：提交前 PASS/WARNING/FAIL 报告。

## 数据流

CLI 或 Skill 输入定位 LaTeX 主文件，`resolve_project` 构建项目上下文，`extract_stats` 生成结构事实，lint/fix/verify 阶段分别消费这些事实，最后由 `CheckReport` 或 presubmit report 输出人类可读和机器可读摘要。

## 设计约束

自动修复默认应支持 dry-run；真实写入需要显式参数。规则严重度和 venue 限制应通过配置层解析，避免散落在 CLI 或报告渲染中。
