#!/usr/bin/env python3
"""
Patch skillOverrides and/or enabledPlugins into ~/.claude/settings.json.

Backs up settings.json to settings.json.bak-{iso8601} first.
Atomic write via tmp file + rename.
Acquires ~/.claude/.skill-optimize.lock to guard against concurrent CC sessions.

Usage:
  apply.py --off '["a","b"]' --name-only '["c"]'
  apply.py --off '[]' --name-only '[]' --disable-plugins '["caveman@caveman"]'
  apply.py --off '["a"]' --name-only '[]' --disable-plugins '["x@y"]'
"""
import argparse
import fcntl
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


SETTINGS = Path.home() / ".claude" / "settings.json"
LOCKFILE = Path.home() / ".claude" / ".skill-optimize.lock"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--off", required=True, help="JSON array of skill names to set off")
    p.add_argument("--name-only", required=True, dest="name_only",
                   help="JSON array of skill names to set name-only")
    p.add_argument("--disable-plugins", default="[]", dest="disable_plugins",
                   help="JSON array of plugin_ids (name@marketplace) to disable")
    return p.parse_args()


def atomic_write(path: Path, content: str):
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix=".skill-optimize-tmp-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        try:
            orig_mode = path.stat().st_mode
            os.chmod(tmp_path, orig_mode)
        except OSError:
            pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main():
    args = parse_args()

    try:
        off_list = json.loads(args.off)
        name_only_list = json.loads(args.name_only)
        disable_plugins = json.loads(args.disable_plugins)
    except json.JSONDecodeError as e:
        print(f"ERROR parsing args: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(off_list, list) or not isinstance(name_only_list, list) or not isinstance(disable_plugins, list):
        print("ERROR: --off, --name-only, --disable-plugins must be JSON arrays", file=sys.stderr)
        sys.exit(1)

    if not off_list and not name_only_list and not disable_plugins:
        print("Nothing to apply.", file=sys.stderr)
        sys.exit(0)

    if not SETTINGS.exists():
        print(f"ERROR: {SETTINGS} not found", file=sys.stderr)
        sys.exit(1)

    # acquire lock
    lock_fd = open(LOCKFILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("ERROR: another skill-optimize process is running (lock held)", file=sys.stderr)
        lock_fd.close()
        sys.exit(1)

    try:
        data = json.loads(SETTINGS.read_text())
    except Exception as e:
        print(f"ERROR reading settings.json: {e}", file=sys.stderr)
        lock_fd.close()
        sys.exit(1)

    # backup
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    backup_path = SETTINGS.parent / f"settings.json.bak-{ts}"
    try:
        shutil.copy2(SETTINGS, backup_path)
    except Exception as e:
        print(f"ERROR creating backup: {e}", file=sys.stderr)
        lock_fd.close()
        sys.exit(1)

    # patch skillOverrides (preserve pre-existing entries we didn't touch)
    if off_list or name_only_list:
        overrides = dict(data.get("skillOverrides", {}))
        for name in off_list:
            overrides[name] = "off"
        for name in name_only_list:
            overrides[name] = "name-only"
        data["skillOverrides"] = overrides

    # patch enabledPlugins
    if disable_plugins:
        enabled = dict(data.get("enabledPlugins", {}))
        for plugin_id in disable_plugins:
            enabled[plugin_id] = False
        data["enabledPlugins"] = enabled

    output = json.dumps(data, indent=2) + "\n"
    try:
        json.loads(output)
    except json.JSONDecodeError as e:
        print(f"ERROR: output JSON invalid: {e}", file=sys.stderr)
        lock_fd.close()
        sys.exit(1)

    try:
        atomic_write(SETTINGS, output)
    except Exception as e:
        print(f"ERROR writing settings.json: {e}", file=sys.stderr)
        lock_fd.close()
        sys.exit(1)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        try:
            LOCKFILE.unlink()
        except OSError:
            pass

    skill_total = len(off_list) + len(name_only_list)
    print(f"backup:{backup_path}")
    print(f"overrides:{skill_total}")
    print(f"disabled_plugins:{len(disable_plugins)}")
    print(f"OK: {skill_total} skill overrides ({len(off_list)} off, {len(name_only_list)} name-only), {len(disable_plugins)} plugin(s) disabled")


if __name__ == "__main__":
    main()
