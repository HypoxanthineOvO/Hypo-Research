# M02 - Instruction and Entry Information Architecture Review

## Objective

Redesign Hypo-Research's user-facing entry model so users can start from a few natural research scenarios instead of memorizing many `$hypo-xxx` skill names.

## 需求

- Review the current Skill list, CLI command surface, README usage, and agent-facing instructions.
- Design a small set of fixed high-level entry scenarios, such as:
  - 调研
  - 读论文
  - 写论文
  - 审论文
  - 管理项目
- Map each entry scenario to intent categories, follow-up questions, and underlying skills/CLI modules.
- Decide which current skills should be visible user entries and which should become hidden sub-capabilities.
- Include sample dialogues showing how a PhD/graduate researcher or independent researcher would enter the system.

## Boundaries

- In scope: instruction taxonomy, router/guide concept, scenario IA, skill-to-entry mapping.
- In scope: natural language user journey and prompt design recommendations.
- Out of scope: implementing the router, rewriting all SKILL.md files, changing CLI commands.

## Non-Goals

- Do not preserve every existing skill as a top-level concept by default.
- Do not optimize primarily for expert users who already memorize commands.
- Do not create an over-complex intent ontology that is harder than the current skill list.

## 预期测试

- The proposed IA covers current major capabilities without requiring 19 top-level entries.
- The IA includes routing questions for ambiguous user requests.
- The report identifies naming/category changes and compatibility strategy.
- Example dialogues demonstrate less command memorization.

## Validation Commands

- `find skills -maxdepth 2 -name SKILL.md -print | sort`
- `uv run hypo-research --help`
- Read README and selected skill files for current user-facing wording.

## Evidence

- Write `.pipeline/reports/01-instruction-and-entry-information-architecture-review.report.md`.
- Include a current-to-proposed mapping table.
- Include sample user utterances and selected route outcomes.

## Human QA

- User reviews whether the fixed scenarios feel natural enough.
- User confirms whether any current skill must remain directly exposed.

## 预期产出

- `.pipeline/reports/01-instruction-and-entry-information-architecture-review.report.md`
- Proposed top-level entry IA.
- Intent routing tree and skill mapping.
- Follow-up implementation candidates for a router/guide Cycle.
