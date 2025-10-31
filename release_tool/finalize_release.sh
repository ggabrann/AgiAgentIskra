#!/usr/bin/env bash
# ===================================================================================
# Финализация и проверка релиза для Codespaces (одной командой)
# - Проверяет: наличие репо локально, ветки release/*, тега vX.Y.Z, PR, GitHub Release
# - При необходимости создаёт PR/Release (если доступен gh и GITHUB_TOKEN)
# - Проверяет отчёт аудита
# Переменные (опционально): REPO_URL, REPO_DIR, BRANCH, RELEASE_BRANCH_PREFIX
# ===================================================================================

set -Eeuo pipefail

REPO_URL="${REPO_URL:-https://github.com/ggabrann/AgiAgentIskra.git}"
REPO_DIR="${REPO_DIR:-AgiAgentIskra}"
BRANCH="${BRANCH:-main}"
RELEASE_BRANCH_PREFIX="${RELEASE_BRANCH_PREFIX:-release}"

# --- Клонирование, если нет локальной копии ---
if [ ! -d "${REPO_DIR}/.git" ]; then
  echo "[INFO] Клонирую репозиторий: ${REPO_URL} → ${REPO_DIR}"
  git clone --depth 1 "${REPO_URL}" "${REPO_DIR}"
fi
cd "${REPO_DIR}"

# --- Базовая инфо ---
ORIGIN_URL="$(git remote get-url origin || true)"
REPO_SLUG="$(printf "%s" "${ORIGIN_URL}" | sed -E "s#(git@github.com:|https://github.com/)##; s/\\.git$//")"
echo "[INFO] Репозиторий: ${REPO_SLUG}"
git fetch --all --tags >/dev/null 2>&1 || true

# --- Поиск релизной ветки ---
REL_BRANCH="$(git for-each-ref --format='%(refname:short)' "refs/heads/${RELEASE_BRANCH_PREFIX}/*" | tail -n 1 || true)"
if [ -z "${REL_BRANCH:-}" ]; then
  REL_BRANCH="$(git for-each-ref --format='%(refname:short)' "refs/remotes/origin/${RELEASE_BRANCH_PREFIX}/*" | sed 's#^origin/##' | tail -n 1 || true)"
fi
if [ -n "${REL_BRANCH:-}" ]; then
  echo "[INFO] Найдена релизная ветка: ${REL_BRANCH}"
else
  echo "[WARN] Релизных веток ${RELEASE_BRANCH_PREFIX}/* не найдено. Это не ошибка, но PR создать нечего."
fi

# --- Последний тег версии ---
LATEST_TAG="$(git tag --list 'v*.*.*' --sort=-v:refname | head -n 1 || true)"
if [ -n "${LATEST_TAG}" ]; then
  echo "[INFO] Последний тег: ${LATEST_TAG}"
  if git ls-remote --tags origin | grep -q "refs/tags/${LATEST_TAG}$"; then
    echo "[OK] Тег ${LATEST_TAG} присутствует на origin"
  else
    echo "[WARN] Тег ${LATEST_TAG} отсутствует на origin; публикую…"
    git push origin "${LATEST_TAG}" || echo "[WARN] Не удалось запушить тег ${LATEST_TAG}"
  fi
else
  echo "[WARN] Теги v*.*.* не найдены."
fi

# --- PR из release/* в main (gh при наличии) ---
if command -v gh >/dev/null 2>&1 && [ -n "${REL_BRANCH:-}" ]; then
  set +e
  PR_LINE="$(gh pr list --base "${BRANCH}" --head "${REL_BRANCH}" --state open --json number,title --jq '.[0].number' 2>/dev/null)"
  set -e
  if [ -n "${PR_LINE}" ]; then
    echo "[OK] Открытый PR #${PR_LINE} уже существует: ${REL_BRANCH} → ${BRANCH}"
  else
    echo "[INFO] Создаю PR: ${REL_BRANCH} → ${BRANCH}"
    gh pr create --base "${BRANCH}" --head "${REL_BRANCH}" --title "chore(release): $(date -u +%Y-%m-%d)" --body "Automated release PR" || echo "[WARN] Не удалось создать PR (возможно нет прав или TOKEN)."
  fi
else
  if [ -n "${REL_BRANCH:-}" ]; then
    echo "[HINT] Установите GitHub CLI (gh) и экспортируйте GITHUB_TOKEN для авто-PR, иначе создайте вручную: ${REL_BRANCH} → ${BRANCH}"
  fi
fi

# --- GitHub Release по последнему тегу (gh при наличии) ---
if command -v gh >/dev/null 2>&1 && [ -n "${LATEST_TAG:-}" ]; then
  set +e
  gh release view "${LATEST_TAG}" >/dev/null 2>&1
  rc=$?
  set -e
  if [ ${rc} -eq 0 ]; then
    echo "[OK] GitHub Release для ${LATEST_TAG} уже существует."
  else
    echo "[INFO] Создаю GitHub Release: ${LATEST_TAG}"
    gh release create "${LATEST_TAG}" --title "${LATEST_TAG}" --notes "Automated release ${LATEST_TAG}" || echo "[WARN] Не удалось создать Release."
  fi
else
  [ -n "${LATEST_TAG:-}" ] && echo "[HINT] Для создания GitHub Release используйте gh CLI: gh release create \"${LATEST_TAG}\" --title \"${LATEST_TAG}\" --notes \"…\""
fi

# --- Проверка наличия отчёта аудита ---
if [ -f "iskra_audit_tool/report.md" ]; then
  echo "[OK] Найден отчёт аудита: iskra_audit_tool/report.md (первые строки ниже)"
  sed -n '1,20p' iskra_audit_tool/report.md || true
else
  echo "[INFO] Отчёт аудита не найден. Для генерации запустите:"
  echo "      (cd iskra_audit_tool && ARCHIVE_PATH=\"../Iskra_Prod_FINAL.zip\" CONFIRM=YES bash ./run_audit.sh)"
fi

# --- Проверка GitHub Actions файлов (минимальный набор) ---
CI_OK=true
[ -f '.github/workflows/ci.yml' ] || CI_OK=false
[ -f '.github/workflows/release.yml' ] || CI_OK=false
if ${CI_OK}; then
  echo "[OK] Найдены workflow-файлы: .github/workflows/ci.yml и release.yml"
else
  echo "[WARN] Workflow-файлы CI/Release отсутствуют или в другом месте. Рекомендуется добавить."
fi

# --- Резюме ---
echo
echo "==================== РЕЗЮМЕ ===================="
echo "Репозиторий:       ${REPO_SLUG}"
echo "Релизная ветка:    ${REL_BRANCH:-<нет>}"
echo "Последний тег:     ${LATEST_TAG:-<нет>}"
echo "PR:                см. выше (gh) или создайте вручную"
echo "Release:           см. выше (gh) или создайте вручную"
echo "Отчёт аудита:      ${PWD}/iskra_audit_tool/report.md (если был создан)"
echo "CI/Release WF:     $( ${CI_OK} && echo OK || echo MISSING )"
echo "================================================"
