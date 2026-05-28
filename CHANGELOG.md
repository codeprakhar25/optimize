# Changelog

## v0.2.0 — 2026-05-28

- Switch from CC plugin system to curl install (simpler, no undocumented plugin API dependency)
- Scripts now install to `~/.local/share/skill-optimize/scripts/`
- SKILL.md installs to `~/.claude/skills/skill-optimize/` (direct user skill, no plugin wrapper)
- Remove `.claude-plugin/` manifest files

## v0.1.0 — 2026-05-28

- Initial MVP release
- `audit.py`: scan session jsonl, classify skills dead/situational/kept, JSON output
- `apply.py`: backup + atomic patch of skillOverrides in settings.json, lockfile guard
- `restore.py`: revert from timestamped backup
- `SKILL.md`: interactive /skill-optimize workflow with AskUserQuestion review flow
- Protected-skill detection from ~/.claude/CLAUDE.md
