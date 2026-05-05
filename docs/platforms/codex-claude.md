# Codex and Claude Platform Notes

## Codex

Install from the bundle path:

```text
$skill-installer https://github.com/HypoxanthineOvO/Hypo-Research/tree/main/.agents/skills/hypo-research
```

The bundle entrypoint is `.agents/skills/hypo-research/SKILL.md`; individual skill docs live in `.agents/skills/hypo-research/skills/`.

## Claude Code

Local Claude skill links are created by:

```bash
./install-skills.sh
```

Plugin metadata is under `plugins/hypo-research/.claude-plugin/plugin.json` and marketplace metadata is under `.claude-plugin/marketplace.json`.

## Source of Truth

- Edit `skills/` first.
- Sync to `.agents/skills/hypo-research/skills/` and `plugins/hypo-research/skills/`.
- Keep README and `docs/` aligned with actual CLI commands.
