# Architecture Decisions

## ADR-001: 保持 CLI 聚合入口，业务逻辑留在领域模块

`src/hypo_research/cli.py` 是稳定用户入口，但不应继续承载大型业务实现。新增能力应先在领域模块内形成可测试 API，再由 CLI 包装。

## ADR-002: 论文记录统一使用 `PaperResult`

所有文献 source adapter、去重、验证、hook 和 output 通过 `PaperResult` 交换数据。这样可以让多源检索、引用图扩展和报告生成共享同一元数据契约。

## ADR-003: LaTeX 写作检查基于结构事实流水线

写作检查先抽取项目结构事实，再由 lint/fix/verify/report 消费。这样自动修复、venue profile 和提交前检查可以复用同一事实基础。

## ADR-004: Skill 文档与 CLI 功能并存

仓库既发布 Python CLI，也发布 Codex/Claude Skills。Skill 文档可以提供 Agent 工作流，但应与 CLI 参数、模块边界和输出格式保持一致。

## ADR-005: Hypo-Workflow 初始化不创建显式 Cycle

本次 `/hw:init` 只建立 `.pipeline/` 配置、规则、状态模板和架构基线。具体开发目标由后续 `/hw:plan` 或 `/hw:cycle` 创建，避免把初始化误当作业务 Cycle。
