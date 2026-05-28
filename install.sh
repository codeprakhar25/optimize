#!/usr/bin/env bash
set -euo pipefail

REPO="codeprakhar25/optimize"
BRANCH="main"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
SKILL_DIR="${HOME}/.claude/skills/skill-optimize"

echo "Installing skill-optimize..."

mkdir -p "${SKILL_DIR}/scripts"

# download SKILL.md
curl -fsSL "${RAW}/skills/skill-optimize/SKILL.md" -o "${SKILL_DIR}/SKILL.md"

# download scripts alongside SKILL.md so \${CLAUDE_SKILL_DIR}/scripts/ resolves correctly
for f in audit.py apply.py restore.py; do
  curl -fsSL "${RAW}/scripts/${f}" -o "${SKILL_DIR}/scripts/${f}"
  chmod +x "${SKILL_DIR}/scripts/${f}"
done

echo ""
echo "Done. Installed to: ${SKILL_DIR}"
echo ""
echo "Restart Claude Code, then run /skill-optimize"
echo ""
echo "To undo applied overrides:"
echo "  python3 ${SKILL_DIR}/scripts/restore.py"
echo ""
echo "To uninstall:"
echo "  rm -rf ${SKILL_DIR}"
