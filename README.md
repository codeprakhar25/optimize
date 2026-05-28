# optimize

A Claude Code skill that audits your installed skills by session history and prunes unused ones via `skillOverrides` — cutting 8–12k tokens per turn on a typical install.

## The problem

113 installed CC skills inject ~13k tokens into the system prompt every turn. ~80% are never invoked. `skillOverrides` in `~/.claude/settings.json` lets you disable or hide skills without uninstalling them.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/codeprakhar25/optimize/main/install.sh | bash
```

Restart Claude Code, then run `/skill-optimize`.

## Usage

```
/skill-optimize
```

The skill will:
1. Scan your `~/.claude/projects/**/*.jsonl` session history (last 60 days)
2. Classify each user skill as dead (0 uses), situational (1–2 uses), or kept (3+)
3. Show a summary with estimated token savings
4. Ask you to apply all, review per category, or cancel
5. Back up `settings.json` before writing anything

> **Note:** Plugin skills (installed via `claude plugin install`) are not controllable via `skillOverrides` — the audit lists them separately. Use `/plugin` to disable unused plugins instead.

## Alternative: manual toggle

In any CC session, run `/skills`, highlight a skill, and press `Space` to cycle `on → name-only → off`. Press `Enter` to save to `.claude/settings.local.json`. Use this for one-off toggles without running the full audit.

## Undo

```bash
python3 ~/.claude/skills/skill-optimize/scripts/restore.py
```

List available backups:
```bash
python3 ~/.claude/skills/skill-optimize/scripts/restore.py --list
```

## Uninstall

```bash
rm -rf ~/.claude/skills/skill-optimize
```

## Risks

- Dead classification misses implicit triggers (model invokes skill via description match with no slash command or Skill tool call). Mitigated by defaulting borderline skills to `name-only` rather than `off`, and by protected-skill detection from `~/.claude/CLAUDE.md`.
- Session jsonl files contain your prompts. Processing is fully local — no network calls, no temp files written.
- If two CC sessions run simultaneously, `apply.py` uses a lockfile to prevent concurrent writes.

## Self-cost

When installed but idle: ≤30 tokens/turn (one line in skill list, no hooks, no agents).

## License

MIT
