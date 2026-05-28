# optimize

A Claude Code plugin that audits your installed skills by session history, classifies unused ones, and prunes them via `skillOverrides` — cutting 8–12k tokens per turn on a typical install.

## The problem

113 installed CC skills inject ~13k tokens into the system prompt every turn. ~80% are never invoked. `skillOverrides` in `~/.claude/settings.json` lets you disable or hide skills without uninstalling them.

## Install

```bash
claude plugin marketplace add codeprakhar25/optimize
claude plugin install optimize@codeprakhar25
```

## Usage

In any Claude Code session:

```
/skill-optimize
```

The skill will:
1. Scan your `~/.claude/projects/**/*.jsonl` session history (last 60 days)
2. Classify each installed skill as dead (0 uses), situational (1–2 uses), or kept (3+)
3. Show a summary with estimated token savings
4. Ask you to apply all, review per category, or cancel
5. Back up `settings.json` before writing anything

## Undo

```bash
python3 ~/.claude/plugins/cache/codeprakhar25/optimize/*/scripts/restore.py
```

Or list backups:
```bash
python3 ~/.claude/plugins/cache/codeprakhar25/optimize/*/scripts/restore.py --list
```

## Risks

- `skillOverrides` is undocumented. Works in CC 2.1.153+; could drift in future versions.
- Dead classification misses implicit triggers (model invokes skill via description match with no slash command or Skill tool call). Mitigated by defaulting borderline skills to `name-only` rather than `off`, and by protected-skill detection from `~/.claude/CLAUDE.md`.
- Session jsonl files contain your prompts. Processing is fully local — no network calls, no temp files written.
- If two CC sessions run simultaneously, `apply.py` uses a lockfile to prevent concurrent writes.

## Self-cost

When installed but idle: ≤30 tokens/turn (one line in skill list, no hooks, no agents).

## License

MIT
