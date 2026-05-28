---
name: skill-optimize
description: Audit installed CC skills by session history and prune unused ones via skillOverrides to cut per-turn token cost. Use when invoked as /skill-optimize, or user says "audit skills", "prune unused skills", "optimize skills", "too many skills", "reduce context".
---

You are running the `skill-optimize` workflow. Follow these steps exactly.

## Step 1 — Run audit

```
python3 "${CLAUDE_SKILL_DIR}/scripts/audit.py" --days 60 --json
```

Parse the JSON output. It contains:
- `installed_count`: total installed skills
- `dead_count`: skills with 0 uses in window
- `situational_count`: skills with 1-2 uses
- `kept_count`: skills with 3+ uses (no override proposed)
- `estimated_tokens_saved`: estimated tokens removed per turn
- `dead`: list of skill names → recommend `"off"`
- `situational`: list of skill names → recommend `"name-only"`
- `kept`: list of skill names (no action)

If audit exits with error or `installed_count == 0`: report the error and stop.

If `dead_count + situational_count == 0`: tell user "No pruning candidates found — all installed skills used recently." Stop.

## Step 2 — Show summary

Report in this format (no extra prose):

```
Skill audit (last 60 days)
  Installed:     <installed_count> (<plugin_count> plugin skills excluded — use /plugin to manage those)
  Dead (→ off):  <dead_count>
  Situational (→ name-only): <situational_count>
  Kept:          <kept_count>
  Est. tokens saved/turn: ~<estimated_tokens_saved>
```

Then use AskUserQuestion with these options:
- **Apply all** — write all proposed overrides to settings.json now (after backup)
- **Review by category** — show per-category tables and pick what to exclude
- **Cancel** — do nothing

## Step 3a — If "Apply all"

Run:
```
python3 "${CLAUDE_SKILL_DIR}/scripts/apply.py" --off '<JSON array of dead names>' --name-only '<JSON array of situational names>'
```

Pass the exact lists from the audit JSON. Report the backup path and override count from stdout.

## Step 3b — If "Review by category"

Show dead skills table first:
```
Dead skills (proposed: off)
  <name> [source]
  ...
```

Use AskUserQuestion (multiSelect=true): "Which dead skills should be EXCLUDED from override (kept as-is)?"
Options = one per dead skill name. Allow selecting none.

Then show situational table:
```
Situational skills (1-2 uses, proposed: name-only)
  <name> [uses] [source]
  ...
```

Use AskUserQuestion (multiSelect=true): "Which situational skills should be EXCLUDED from override?"
Options = one per situational skill name.

Then confirm: AskUserQuestion single-select: "Apply <N> overrides to settings.json?"
- Yes, apply
- Cancel

On Yes: run apply.py with the filtered lists (user exclusions removed).

## Step 4 — Confirm

After apply.py succeeds, print:
```
Done. Backup: <backup_path>
<N> overrides written.
Restart Claude Code to apply changes.
To undo: python3 "${CLAUDE_SKILL_DIR}/scripts/restore.py"
```

## Rules

- Never write to settings.json without explicit user confirmation (step 3).
- If apply.py exits non-zero, show stderr and stop — do not retry.
- Never propose overriding a skill mentioned in ~/.claude/CLAUDE.md (the audit handles this, but double-check).
- `name-only` means the skill stays slash-invokable but its description is not injected every turn — correct tradeoff for situational skills.
