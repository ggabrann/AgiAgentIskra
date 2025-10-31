#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${REPO_URL:-$(git remote get-url origin 2>/dev/null || true)}"
BRANCH="${BRANCH:-main}"
RELEASE_BRANCH_PREFIX="${RELEASE_BRANCH_PREFIX:-release}"
VERSION_BUMP="${VERSION_BUMP:-patch}"   # major|minor|patch|set
VERSION_SET="${VERSION_SET:-}"
GIT_USER_NAME="${GIT_USER_NAME:-Iskra Bot}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-iskra-bot@local}"
PUSH_REMOTE="${PUSH_REMOTE:-origin}"
OPEN_PR="${OPEN_PR:-true}"
CREATE_GH_RELEASE="${CREATE_GH_RELEASE:-true}"
CI_SKIP="${CI_SKIP:-false}"

BUILD_ARCHIVE="${BUILD_ARCHIVE:-./Iskra_Prod_FINAL.zip}"
BUILD_SRC_DIR="${BUILD_SRC_DIR:-}"

main() {
  git fetch --all --tags || true
  git checkout "$BRANCH" || true
  git pull --ff-only "$PUSH_REMOTE" "$BRANCH" || true

  local rel_branch="${RELEASE_BRANCH_PREFIX}/$(date -u +%Y%m%d-%H%M%S)"
  git checkout -b "$rel_branch" || git checkout "$rel_branch"

  git config user.name "$GIT_USER_NAME"
  git config user.email "$GIT_USER_EMAIL"

  local tmp
  tmp=$(mktemp -d)
  trap 'rm -rf "${tmp}"' EXIT

  local src_dir
  if [[ -n "$BUILD_ARCHIVE" && -f "$BUILD_ARCHIVE" ]]; then
    python3 - "$BUILD_ARCHIVE" "${tmp}/src" <<'PY'
import sys
import tarfile
import zipfile
from pathlib import Path

archive = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

if zipfile.is_zipfile(archive):
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(out)
elif tarfile.is_tarfile(archive):
    with tarfile.open(archive, "r:*") as tf:
        tf.extractall(out)
else:
    raise SystemExit(f"Unsupported archive: {archive}")
print(out)
PY
    src_dir="${tmp}/src"
  elif [[ -n "$BUILD_SRC_DIR" && -d "$BUILD_SRC_DIR" ]]; then
    src_dir="$BUILD_SRC_DIR"
  else
    echo "[WARN] Источник сборки не найден (ожидал $BUILD_ARCHIVE или каталог BUILD_SRC_DIR). Релиз пропущен."
    exit 0
  fi

  python3 - "$src_dir" "." <<'PY'
import hashlib
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
dst = Path(sys.argv[2]).resolve()
EXCLUDE = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", "_iskra_work", ".mypy_cache", ".pytest_cache"}


def should_copy(relative: str) -> bool:
    parts = set(relative.split("/"))
    return not (parts & EXCLUDE)


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


copied = updated = skipped = 0
for path in src.rglob("*"):
    if path.is_dir():
        continue
    relative = str(path.relative_to(src)).replace("\\", "/")
    if not should_copy(relative):
        continue
    destination = dst / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_file():
        try:
            if sha256sum(path) == sha256sum(destination):
                skipped += 1
                continue
        except Exception:
            pass
        shutil.copy2(path, destination)
        updated += 1
    else:
        shutil.copy2(path, destination)
        copied += 1
print(f"[sync] copied={copied} updated={updated} skipped={skipped}")
PY

  local current="0.0.0"
  if [[ -f VERSION ]]; then
    current=$(tr -d '\r' < VERSION | head -n 1)
  fi

  local new_version
  if [[ "$VERSION_BUMP" == "set" && -n "$VERSION_SET" ]]; then
    new_version="$VERSION_SET"
  else
    IFS=. read -r major minor patch <<<"$current"
    major=${major:-0}
    minor=${minor:-0}
    patch=${patch:-0}
    case "$VERSION_BUMP" in
      major) new_version="$((major + 1)).0.0" ;;
      minor) new_version="${major}.$((minor + 1)).0" ;;
      *)     new_version="${major}.${minor}.$((patch + 1))" ;;
    esac
  fi
  echo "$new_version" > VERSION

  local today
  today=$(date -u +%F)
  {
    echo "## v${new_version} — ${today}"
    echo "- Automated release"
    echo
    cat CHANGELOG.md 2>/dev/null || true
  } > "${tmp}/CHANGELOG.md"
  mv "${tmp}/CHANGELOG.md" CHANGELOG.md

  local skip_tag=""
  if [[ "$CI_SKIP" == "true" ]]; then
    skip_tag="[skip ci] "
  fi

  git add -A
  if git diff --cached --quiet; then
    echo "[INFO] Нет изменений для коммита"
  else
    git commit -m "${skip_tag}chore(release): v${new_version}"
  fi

  git tag -a "v${new_version}" -m "Release v${new_version}" || true
  git push "$PUSH_REMOTE" "$rel_branch"
  git push "$PUSH_REMOTE" "v${new_version}" || true

  if [[ "$OPEN_PR" == "true" ]] && command -v gh >/dev/null 2>&1; then
    gh pr create \
      --base "$BRANCH" \
      --head "$rel_branch" \
      --title "chore(release): v${new_version}" \
      --body "Automated release v${new_version}" || true
  else
    echo "[INFO] Создайте PR: $rel_branch → $BRANCH"
  fi

  if [[ "$CREATE_GH_RELEASE" == "true" ]] && command -v gh >/dev/null 2>&1; then
    gh release create "v${new_version}" --title "v${new_version}" --notes "Automated release v${new_version}" || true
  fi

  echo "[OK] Готово: ветка $rel_branch, тег v${new_version}"
}

main "$@"
