#!/usr/bin/env bash
# install-skills.sh — install all Hypo-Research skills for Claude Code and Codex CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
LEGACY_SKILLS=("survey" "quick-search" "review-results")

CLAUDE_SKILLS_DIR="$SCRIPT_DIR/.claude/skills"
mkdir -p "$CLAUDE_SKILLS_DIR"
for legacy_name in "${LEGACY_SKILLS[@]}"; do
    rm -rf "$CLAUDE_SKILLS_DIR/$legacy_name"
done
for skill_dir in "$SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    target="$CLAUDE_SKILLS_DIR/$skill_name"
    rm -rf "$target"
    ln -sf "../../skills/$skill_name" "$target"
    echo "Claude Code: linked $skill_name"
done

CODEX_PROMPTS_DIR="$HOME/.codex/prompts"
mkdir -p "$CODEX_PROMPTS_DIR"
for legacy_name in "${LEGACY_SKILLS[@]}"; do
    rm -f "$CODEX_PROMPTS_DIR/$legacy_name.md"
done
for skill_dir in "$SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    source_file="$skill_dir/SKILL.md"
    if [ -f "$source_file" ]; then
        cp "$source_file" "$CODEX_PROMPTS_DIR/$skill_name.md"
        echo "Codex CLI: copied $skill_name.md to ~/.codex/prompts/"
    fi
done

echo "Done. Skills installed for both Claude Code and Codex CLI."
