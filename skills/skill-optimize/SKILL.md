---
name: skill-optimize
description: Audit CC skills by usage, prune dead ones via skillOverrides. Saves 8-12k tokens/turn. Use for /skill-optimize, "audit skills", "prune unused skills", "optimize skills", "too many skills".
---

You are running the `skill-optimize` workflow. Follow these steps exactly. Do not skip steps.

## Step 1 — Run audit

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/audit.py" --days 60 --json
```

If the command fails: show the error and stop.

Parse the JSON. Key fields:
- `installed_count`, `has_history`, `dead_count`, `situational_count`, `kept_count`
- `plugin_count`, `disableable_plugin_count`
- `estimated_tokens_saved`
- `dead[]`, `situational[]`, `kept[]`
- `plugins[]` — all plugins with usage info
- `disableable_plugins[]` — plugins where every skill has 0 uses

## Step 2 — Edge case checks (stop early if nothing to do)

**If `installed_count == 0`:**
Tell user: "No skills installed — nothing to optimize." Stop.

**If `has_history == false` AND `installed_count < 10`:**
Tell user: "Looks like a fresh install with no session history yet. Come back after using Claude Code for a few days — the audit works best with real usage data." Stop.

**If `has_history == false` AND `installed_count >= 10`:**
Warn: "No session history found in the last 60 days. Usage counts will be 0 for everything — results may not reflect real usage. Proceed with caution."
Continue but note this warning in the summary.

**If `dead_count + situational_count == 0` AND `disableable_plugin_count == 0`:**
Tell user: "Everything's active — no pruning candidates. All your skills have been used recently." Stop.

## Step 3 — Show Phase 1 summary (skills)

Only show if `dead_count + situational_count > 0`. Report:

```
── Phase 1: User skills ──────────────────────────────
  Installed:              <installed_count> user skills
  Dead (→ off):           <dead_count>
  Situational (→ name-only): <situational_count>
  Kept (used 3+ times):   <kept_count>
  Est. tokens saved/turn: ~<estimated_tokens_saved>
```

Use AskUserQuestion (single-select):
- **Apply all** — write all proposed overrides now (backup first)
- **Review by category** — show tables, pick exclusions
- **Skip to plugin audit** — skip skills, go straight to Phase 2
- **Cancel** — do nothing, stop

## Step 4a — If "Apply all"

Run:
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/apply.py" \
  --off '<JSON array of dead names>' \
  --name-only '<JSON array of situational names>'
```

Pass the exact `dead[].name` and `situational[].name` arrays from the audit JSON.

Print the backup path and override count from stdout. Then proceed to Step 5 (plugin phase).

## Step 4b — If "Review by category"

Show dead skills:
```
Dead skills (0 uses — proposed: off)
  <name>
  ...
```

AskUserQuestion (multiSelect=true): "Exclude any dead skills from override?"
Options = one per dead skill name. User selects ones to KEEP as-is. None = apply all.

Show situational skills:
```
Situational skills (1-2 uses — proposed: name-only)
  <name>  [<uses> uses]
  ...
```

AskUserQuestion (multiSelect=true): "Exclude any situational skills from override?"
Options = one per situational skill name.

Build filtered lists (remove user exclusions). Show final count.

AskUserQuestion (single-select): "Apply <N> overrides to settings.json?"
- **Yes, apply**
- **Cancel**

On Yes: run apply.py with filtered lists. Print backup path + count. Proceed to Step 5.
On Cancel: stop.

## Step 5 — Phase 2: Plugin audit

Only run this phase if `disableable_plugin_count > 0`. If not, skip to Step 6.

Show header:
```
── Phase 2: Plugins ──────────────────────────────────
  <disableable_plugin_count> plugin(s) have ZERO usage in the last 60 days.
  Disabling a plugin removes ALL its skills and agents. This is reversible.
```

Then for EACH disableable plugin, one at a time, ask individually:

Show plugin info:
```
Plugin: <plugin_id>
  Skills: <skill_count> (<list skill names, comma-separated>)
  Usage:  0 invocations in last 60 days
```

AskUserQuestion (single-select): "Disable plugin <plugin_id>?"
- **Yes, disable it**
- **No, keep it**

Collect all "yes" responses into a list.

After all plugins asked: if any selected for disable, run:
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/apply.py" \
  --off '[]' \
  --name-only '[]' \
  --disable-plugins '<JSON array of selected plugin_ids>'
```

Print backup path and disabled count.

## Step 6 — Wrap up

If nothing was applied across both phases: tell user so clearly.
Otherwise: confirm everything is done, remind user to restart Claude Code.

## Rules

- Never write to settings.json without explicit per-phase confirmation.
- If apply.py exits non-zero: show stderr and stop — do not retry.
- Never propose overriding a skill mentioned in ~/.claude/CLAUDE.md (audit excludes them, but double-check).
- Plugin phase is always separate from skills phase — never merge into one confirmation.
- If skills phase was skipped/cancelled, still offer plugin phase if disableable_plugin_count > 0.
