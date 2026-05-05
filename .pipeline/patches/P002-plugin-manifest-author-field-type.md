# P002: plugin.json manifest author 字段类型错误
- 严重级: critical
- 状态: closed
- 发现于: C2 post-release (v0.7.0)
- 创建时间: 2026-05-05T23:20:00+08:00
- 修复时间: 2026-05-05T23:20:21+08:00
- 改动: plugins/hypo-research/.claude-plugin/plugin.json — author 从字符串 "HypoxanthineOvO" 改为对象 {"name": "HypoxanthineOvO"}；移除无效的 $schema 和 tags 字段；添加 skills 字段
- 测试: N/A（manifest 格式修复，不涉及代码逻辑）
- commit: 2dabd9a
- 关联: v0.7.0 插件安装失败
- resolved_by: null
- related: []
- supersedes: []

## 描述

Hypo-Research v0.7.0 安装时报错：

```
✘ Failed to install plugin "hypo-research@hypo-research":
Plugin has an invalid manifest file at .claude-plugin/plugin.json
Validation errors: author: Invalid input: expected object, received string
```

根因：`plugin.json` 中 `author` 字段为字符串 `"HypoxanthineOvO"`，但 Claude Code 插件清单 schema 要求 `author` 为对象 `{"name": "..."}`。

## 结果

已在 commit `2dabd9a` 中修复：将 `author` 从字符串改为对象格式，同时移除了 manifest 中不被识别的 `$schema` 和 `tags` 字段，并补上了缺失的 `skills` 字段。
