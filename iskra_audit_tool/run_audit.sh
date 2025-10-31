#!/usr/bin/env bash
set -euo pipefail
ARCHIVE_PATH="${ARCHIVE_PATH:-./Iskra_Prod_FINAL.zip}"
REPO_URL="${REPO_URL:-}"
PROJECT_DIR="${PROJECT_DIR:-}"
MNT_PATH="${MNT_PATH:-/mnt}"
REPORT_PATH="${REPORT_PATH:-./report.md}"
APPLY="${APPLY:-no}"
ONLINE="${ONLINE:-no}"
CONFIRM="${CONFIRM:-YES}"

python3 -m venv .venv || true
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then pip install -r requirements.txt || true; fi

python iskra_audit.py \
  --archive "${ARCHIVE_PATH}" \
  --repo "${REPO_URL}" \
  --project-dir "${PROJECT_DIR}" \
  --mnt "${MNT_PATH}" \
  --apply "${APPLY}" \
  --report "${REPORT_PATH}" \
  --online "${ONLINE}" \
  --confirm "${CONFIRM}"
