# Core And CLI Modules

## 职责

`core/` 提供跨领域共享的论文数据模型、去重、限速、基础验证和外部 API source adapter。`cli.py` 是用户命令入口，负责把 Click 参数转换为领域模块调用。

## 主要文件

- `cli.py`：顶层命令、子命令注册、配置解析、Rich/JSON/Markdown 输出串联。
- `core/models.py`：`PaperResult`、`SearchParams`、`SurveyMeta`、`SearchResult`、query expansion trace 和 metadata issue。
- `core/sources/`：Semantic Scholar、OpenAlex、arXiv 适配器，统一返回 `PaperResult`。
- `core/dedup.py`：跨源论文去重。
- `core/verifier.py`：跨源元数据验证与可信度标记。
- `core/rate_limiter.py`：外部 API 调用节流。

## 设计约束

CLI 层不应持有复杂业务状态。新的领域命令应暴露小型函数或类供 `cli.py` 调用，避免在 CLI 文件内实现完整业务流程。外部 API 返回值必须先规范化为 `PaperResult`，再进入 dedup、verify、hook 或 output。
