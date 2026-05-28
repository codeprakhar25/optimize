#!/usr/bin/env bash
set -euo pipefail

REPO="codeprakhar25/optimize"
BRANCH="main"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
INSTALL_DIR="${HOME}/.local/share/skill-optimize"
SKILL_DIR="${HOME}/.claude/skills/skill-optimize"

echo "Installing skill-optimize..."

# create dirs
mkdir -p "${INSTALL_DIR}/scripts"
mkdir -p "${SKILL_DIR}"

# download scripts
for f in audit.py apply.py restore.py; do
  curl -fsSL "${RAW}/scripts/${f}" -o "${INSTALL_DIR}/scripts/${f}"
  chmod +x "${INSTALL_DIR}/scripts/${f}"
done

# download SKILL.md into ~/.claude/skills/
curl -fsSL "${RAW}/skills/skill-optimize/SKILL.md" -o "${SKILL_DIR}/SKILL.md"

echo ""
echo "Done."
echo "  Scripts: ${INSTALL_DIR}/scripts/"
echo "  Skill:   ${SKILL_DIR}/SKILL.md"
echo ""
echo "Restart Claude Code, then run /skill-optimize"
echo ""
echo "To uninstall:"
echo "  rm -rf ${INSTALL_DIR} ${SKILL_DIR}"
