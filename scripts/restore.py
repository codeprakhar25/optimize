#!/usr/bin/env python3
"""
Restore ~/.claude/settings.json from the most recent skill-optimize backup.

Usage:
  python3 restore.py           # restore latest backup
  python3 restore.py --list    # list available backups
  python3 restore.py --backup settings.json.bak-2026-05-28T12:00:00  # restore specific
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path


SETTINGS = Path.home() / ".claude" / "settings.json"


def find_backups():
    return sorted(
        SETTINGS.parent.glob("settings.json.bak-*"),
        key=lambda p: p.name,
        reverse=True,
    )


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true", help="list available backups")
    p.add_argument("--backup", help="specific backup file to restore")
    return p.parse_args()


def main():
    args = parse_args()

    if args.list:
        backups = find_backups()
        if not backups:
            print("No backups found.")
        else:
            print("Available backups (newest first):")
            for b in backups:
                print(f"  {b.name}")
        return

    if args.backup:
        backup_path = Path(args.backup)
        if not backup_path.is_absolute():
            backup_path = SETTINGS.parent / backup_path
    else:
        backups = find_backups()
        if not backups:
            print("ERROR: no skill-optimize backups found", file=sys.stderr)
            sys.exit(1)
        backup_path = backups[0]
        print(f"Restoring from: {backup_path.name}")

    if not backup_path.exists():
        print(f"ERROR: backup not found: {backup_path}", file=sys.stderr)
        sys.exit(1)

    # validate backup is valid JSON before overwriting
    try:
        json.loads(backup_path.read_text())
    except Exception as e:
        print(f"ERROR: backup file is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        orig_mode = SETTINGS.stat().st_mode
    except OSError:
        orig_mode = None

    shutil.copy2(backup_path, SETTINGS)
    if orig_mode is not None:
        os.chmod(SETTINGS, orig_mode)

    print(f"Restored {SETTINGS} from {backup_path.name}")
    print("Restart Claude Code to apply changes.")


if __name__ == "__main__":
    main()
