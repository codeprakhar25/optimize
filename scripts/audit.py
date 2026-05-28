#!/usr/bin/env python3
"""
Scan installed CC skills against session history and classify by usage.

Exit codes: 0 success, 1 error.
JSON output (--json flag): written to stdout.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=60, help="lookback window in days")
    p.add_argument("--json", action="store_true", help="emit JSON to stdout")
    p.add_argument("--dead-threshold", type=int, default=0,
                   help="max invocations to classify as dead (default 0)")
    p.add_argument("--situational-threshold", type=int, default=2,
                   help="max invocations to classify as situational (default 2)")
    return p.parse_args()


def load_protected_skills():
    """Skills mentioned in ~/.claude/CLAUDE.md should never be overridden."""
    claude_md = Path.home() / ".claude" / "CLAUDE.md"
    if not claude_md.exists():
        return set()
    text = claude_md.read_text(errors="replace")
    # match /skill-name patterns inside backticks or slash-command references
    found = set()
    for m in re.finditer(r"`/([a-zA-Z0-9_-]+)`", text):
        found.add(m.group(1))
    for m in re.finditer(r"/([a-zA-Z0-9_-]+)", text):
        found.add(m.group(1))
    return found


def installed_skills():
    """Return dict of skill_name -> source_label for all enabled installed skills."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return {}

    try:
        settings = json.loads(settings_path.read_text())
    except Exception as e:
        print(f"ERROR reading settings.json: {e}", file=sys.stderr)
        sys.exit(1)

    result = {}

    # user skills
    for p in (Path.home() / ".claude" / "skills").glob("*/SKILL.md"):
        result[p.parent.name] = "user"

    # plugin skills (only enabled plugins)
    enabled = settings.get("enabledPlugins", {})
    for plugin_id, on in enabled.items():
        if not on:
            continue
        try:
            name, marketplace = plugin_id.split("@", 1)
        except ValueError:
            continue
        plugin_root = Path.home() / ".claude" / "plugins" / "cache" / marketplace / name
        if not plugin_root.exists():
            continue
        for p in plugin_root.rglob("SKILL.md"):
            # skip agent/IDE sub-directories
            if any(seg in str(p) for seg in ["/.agents/", "/.roo/", "/.junie/", "/.kiro/"]):
                continue
            result[p.parent.name] = f"plugin:{plugin_id}"

    return result


def collect_usage(days: int):
    """Count invocations per skill name from session jsonl files."""
    proj_root = Path.home() / ".claude" / "projects"
    if not proj_root.exists():
        return Counter()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: Counter = Counter()

    for jsonl_path in proj_root.rglob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(jsonl_path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if mtime < cutoff:
            continue

        try:
            with open(jsonl_path, errors="replace") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        d = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    msg_type = d.get("type")

                    # slash-command signal: <command-name>/foo</command-name> in user/system content
                    if msg_type in ("user", "system"):
                        msg = d.get("message", {}) if msg_type == "user" else {}
                        content = msg.get("content", "") if msg else d.get("content", "")
                        if isinstance(content, list):
                            content = " ".join(
                                b.get("text", "") for b in content if isinstance(b, dict)
                            )
                        if isinstance(content, str):
                            for m in re.finditer(r"<command-name>/([a-zA-Z0-9_-]+)", content):
                                counts[m.group(1)] += 1

                    # Skill tool signal: tool_use blocks with name=="Skill"
                    elif msg_type == "assistant":
                        msg = d.get("message", {})
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if not isinstance(block, dict):
                                    continue
                                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                                    skill_name = block.get("input", {}).get("skill", "")
                                    # strip plugin: prefix and leading slash
                                    skill_name = skill_name.lstrip("/").split(":")[-1]
                                    if skill_name:
                                        counts[skill_name] += 1
        except OSError:
            continue

    return counts


def read_skill_description(name: str, skills: dict) -> str:
    """Read the description frontmatter from a skill's SKILL.md, or return empty string."""
    source = skills.get(name, "user")
    settings_path = Path.home() / ".claude" / "settings.json"

    if source == "user":
        skill_md = Path.home() / ".claude" / "skills" / name / "SKILL.md"
    else:
        # plugin:name@marketplace
        try:
            plugin_id = source.split(":", 1)[1]
            pname, marketplace = plugin_id.split("@", 1)
            plugin_root = Path.home() / ".claude" / "plugins" / "cache" / marketplace / pname
            skill_md = next(plugin_root.rglob(f"{name}/SKILL.md"), None)
            if skill_md is None:
                return ""
        except Exception:
            return ""

    if not skill_md or not skill_md.exists():
        return ""

    try:
        text = skill_md.read_text(errors="replace")
        m = re.search(
            r"^description:\s*[>|]?\s*\n?(.*?)(?=\n\w|\n---|\Z)",
            text, re.DOTALL | re.MULTILINE
        )
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    except OSError:
        pass
    return ""


def estimate_tokens(skill_names, skills: dict) -> int:
    """Estimate tokens removed per turn by pruning skill_names."""
    total = 0
    for name in skill_names:
        desc = read_skill_description(name, skills)
        # "- name: description\n"
        line = f"- {name}: {desc}\n" if desc else f"- {name}\n"
        total += len(line) // 4
    return total


def main():
    args = parse_args()

    skills = installed_skills()
    if not skills:
        if args.json:
            print(json.dumps({
                "installed_count": 0,
                "dead_count": 0,
                "situational_count": 0,
                "kept_count": 0,
                "estimated_tokens_saved": 0,
                "dead": [],
                "situational": [],
                "kept": [],
            }))
        else:
            print("No installed skills found.")
        return

    usage = collect_usage(args.days)
    protected = load_protected_skills()

    dead = []
    situational = []
    kept = []
    plugin_only = []  # plugin skills: skillOverrides has no effect on them

    for name in sorted(skills):
        source = skills[name]
        count = usage.get(name, 0)
        is_plugin = source.startswith("plugin:")

        if is_plugin:
            # skillOverrides does not affect plugin skills (docs confirmed); surface separately
            plugin_only.append({"name": name, "uses": count, "source": source})
        elif name in protected:
            kept.append({"name": name, "uses": count, "source": source, "protected": True})
        elif count <= args.dead_threshold:
            dead.append({"name": name, "uses": count, "source": source})
        elif count <= args.situational_threshold:
            situational.append({"name": name, "uses": count, "source": source})
        else:
            kept.append({"name": name, "uses": count, "source": source})

    tokens_saved = estimate_tokens(
        [s["name"] for s in dead] + [s["name"] for s in situational],
        skills
    )

    if args.json:
        print(json.dumps({
            "installed_count": len(skills),
            "dead_count": len(dead),
            "situational_count": len(situational),
            "kept_count": len(kept),
            "plugin_count": len(plugin_only),
            "estimated_tokens_saved": tokens_saved,
            "dead": dead,
            "situational": situational,
            "kept": kept,
            "plugin_skills": plugin_only,
        }, indent=2))
    else:
        print(f"Installed skills: {len(skills)}")
        print(f"  User skills:     {len(skills) - len(plugin_only)}")
        print(f"  Plugin skills:   {len(plugin_only)} (not controllable via skillOverrides — use /plugin)")
        print(f"Dead (0 uses in {args.days}d):       {len(dead)}")
        print(f"Situational (1-{args.situational_threshold} uses): {len(situational)}")
        print(f"Kept (>{args.situational_threshold} uses):         {len(kept)}")
        print(f"Est. tokens saved/turn:    ~{tokens_saved}")
        if dead:
            print("\nDead skills:")
            for s in dead:
                print(f"  {s['name']:<40} [{s['source']}]")
        if situational:
            print("\nSituational skills:")
            for s in situational:
                print(f"  {s['name']:<40} {s['uses']:>2} uses [{s['source']}]")
        if plugin_only:
            print(f"\nPlugin skills (manage via /plugin, not shown above):")
            for s in sorted(plugin_only, key=lambda x: x["uses"]):
                print(f"  {s['name']:<40} {s['uses']:>2} uses [{s['source']}]")


if __name__ == "__main__":
    main()
