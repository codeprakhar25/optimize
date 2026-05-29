# optimize

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-black)](skills/skill-optimize/SKILL.md)
[![Python](https://img.shields.io/badge/python-3.x-3776AB.svg)](scripts/audit.py)
[![Install](https://img.shields.io/badge/install-curl%20%7C%20bash-2ea44f.svg)](#install)

Reduce Claude Code token overhead by auditing your installed skills, finding the ones you rarely use, and safely moving them to `name-only` or `off`.

`optimize` is a Claude Code skill that keeps your skills installed, but trims how much unused skill context gets injected into every turn. Less repeated context means fewer wasted tokens, which can help your usage last longer before you run into usage limits.

## Demo

![Sanitized terminal demo of optimize usage](assets/demo.gif)

The recording uses sample output and shows both prompts: applying the user-skill patch, then deciding whether to disable an unused plugin. No local Claude Code history or prompts are shown.

## Why this exists

Claude Code skills are useful, but every installed skill can add metadata to the model context. As your skill library grows, unused or rarely used skills can quietly spend tokens on every prompt.

`optimize` helps you answer:

- Which skills have I actually used recently?
- Which skills can be hidden from the prompt without uninstalling them?
- How many tokens could I save per turn?
- Which plugin skills appear unused and may be worth disabling separately?

Your savings depend on how many skills you have installed and how large their descriptions are. Small setups may save very little. Larger skill-heavy setups can save thousands of tokens per turn.

## How it works

`/skill-optimize` runs a local audit over your Claude Code data:

1. Reads installed user skills from `~/.claude/skills/`.
2. Reads enabled plugin skills from Claude Code plugin cache.
3. Scans recent session history in `~/.claude/projects/**/*.jsonl`.
4. Counts direct slash-command usage and Skill tool invocations.
5. Groups user skills as:
   - `dead`: 0 uses in the lookback window, proposed as `off`
   - `situational`: 1-2 uses, proposed as `name-only`
   - `kept`: 3+ uses, left unchanged
6. Shows estimated token savings before changing anything.
7. Asks for confirmation before writing to `~/.claude/settings.json`.

Plugin skills are reported separately because Claude Code does not expose them through `skillOverrides` in the same way as user skills. If a plugin appears completely unused, the workflow can ask whether to disable that plugin.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/codeprakhar25/optimize/main/install.sh | bash
```

Restart Claude Code, then run:

```text
/skill-optimize
```

## Requirements

- Claude Code with skills enabled
- Python 3
- `curl` for the installer
- A Unix-like shell environment

No Python packages are required.

## Usage

```text
/skill-optimize
```

The workflow will:

- scan the last 60 days of Claude Code session history
- estimate token savings from hiding unused skill context
- show separate summaries for user skills and plugin skills
- ask whether to apply all recommendations, review them, skip, or cancel
- create a backup before writing any changes

Nothing is changed until you explicitly confirm.

## What Gets Changed

For user skills, `optimize` updates `skillOverrides` in:

```text
~/.claude/settings.json
```

Example:

```json
{
  "skillOverrides": {
    "rarely-used-skill": "name-only",
    "unused-skill": "off"
  }
}
```

For fully unused plugins, `optimize` may update `enabledPlugins` only after a separate confirmation.

## Modes

| Mode | Meaning | When it is used |
| --- | --- | --- |
| `name-only` | Keep the skill available, but remove its description from the prompt | Skills used rarely |
| `off` | Hide the skill from Claude Code context | Skills with no detected recent usage |
| unchanged | Leave the skill exactly as it is | Skills used regularly or protected by your config |

## Undo

Every apply creates a timestamped backup of `~/.claude/settings.json`.

Restore the latest backup:

```bash
python3 ~/.claude/skills/skill-optimize/scripts/restore.py
```

List available backups:

```bash
python3 ~/.claude/skills/skill-optimize/scripts/restore.py --list
```

Restore a specific backup:

```bash
python3 ~/.claude/skills/skill-optimize/scripts/restore.py --backup settings.json.bak-YYYY-MM-DDTHH:MM:SS
```

Restart Claude Code after restoring.

## Manual Alternative

For one-off changes, you can use Claude Code's built-in skill picker:

1. Run `/skills`.
2. Highlight a skill.
3. Press `Space` to cycle between `on`, `name-only`, and `off`.
4. Press `Enter` to save.

Use the manual flow when you already know which skill to change. Use `/skill-optimize` when you want an audit based on usage history.

## Safety

- Fully local: session history is read from disk and is not sent anywhere.
- Reversible: settings are backed up before every write.
- Reviewable: recommendations are shown before they are applied.
- Conservative defaults: rarely used skills are moved to `name-only`, not immediately disabled.
- Protected skills: skills referenced in `~/.claude/CLAUDE.md` are kept.
- Write lock: concurrent runs are guarded by a lock file.

## Risks and Limits

`optimize` is useful, but it is still an audit based on detectable usage. Review the recommendations before applying them.

| Risk | What it means | How to handle it |
| --- | --- | --- |
| Implicit usage may be missed | Claude may use a skill because its description matched your prompt, without an obvious slash command in history | Keep borderline skills as `name-only`, or exclude them during review |
| Fresh installs have weak history | If you recently started using Claude Code, many skills may look unused | Wait a few days or review each recommendation carefully |
| Plugin disables are broader | Disabling a plugin can remove all of its skills and agents from context | Plugin changes are shown separately and require separate confirmation |
| Local prompts are scanned | The audit reads local session `.jsonl` files that may include your prompts | Processing stays local and no network calls are made |
| Token savings are estimates | Savings are calculated from skill names and descriptions, not from Claude's exact internal tokenizer | Treat the number as a directional estimate |

If a skill you need becomes hidden, restore from backup or turn it back on with `/skills`.

## Uninstall

```bash
rm -rf ~/.claude/skills/skill-optimize
```

Uninstalling removes the `skill-optimize` command. It does not remove any `skillOverrides` already written to `~/.claude/settings.json`; use the restore command first if you want to undo applied changes.

## Development

Run the audit script directly:

```bash
python3 scripts/audit.py --days 60
```

Emit JSON:

```bash
python3 scripts/audit.py --days 60 --json
```

The project is intentionally small:

- `skills/skill-optimize/SKILL.md`: Claude Code workflow
- `scripts/audit.py`: usage audit and token estimate
- `scripts/apply.py`: settings patcher with backup and lockfile
- `scripts/restore.py`: backup restore helper
- `scripts/record-demo.sh`: regenerate the README demo GIF
- `install.sh`: curl installer

## License

[MIT](LICENSE)
