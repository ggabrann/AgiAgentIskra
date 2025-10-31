# -*- coding: utf-8 -*-
"""Утилита аудита и структуризации артефактов Искры."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".rst",
    ".txt",
    ".ini",
    ".cfg",
    ".env",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".graphql",
    ".proto",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".less",
    ".dockerfile",
}

COG_KEYS = [
    ("perception", ["ingest", "observe", "parse", "sensor", "extract"]),
    ("memory.short_term", ["buffer", "scratch", "cache", "context", "window"]),
    ("memory.long_term", ["vector", "embedding", "sqlite", "persist", "kv", "chroma", "faiss"]),
    ("planning", ["plan", "decompose", "task", "strategy", "tree", "htn"]),
    ("tool_use", ["tool", "action", "skill", "api", "executor", "browser", "code"]),
    ("reflection", ["critic", "review", "reflect", "feedback", "verify", "selfcheck"]),
    ("learning", ["learn", "update", "fine_tune", "train", "adapt"]),
    ("control", ["loop", "orchestrator", "manager", "controller"]),
]


def now_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sh(cmd: Iterable[str], cwd: Optional[Path] = None, timeout: Optional[int] = None):
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except Exception as exc:  # noqa: BLE001 - диагностика важнее
        return 1, "", f"{type(exc).__name__}: {exc}"


def read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > limit:
            with path.open("rb") as handle:
                data = handle.read(limit)
            return data.decode("utf-8", errors="replace")
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return ""


def is_text_file(path: Path) -> bool:
    if path.name.lower() == "dockerfile":
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


@dataclass
class Source:
    root: Path
    label: str


def unpack_archive(archive: Path, dest: Path) -> Optional[Source]:
    if not archive.exists():
        return None

    ensure_dir(dest)
    try:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive, "r") as zf:
                zf.extractall(dest)
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive, "r:*") as tf:
                tf.extractall(dest)
        elif archive.is_dir():
            shutil.copytree(archive, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(archive, dest / archive.name)
    except Exception as exc:
        print(f"[WARN] Ошибка распаковки {archive}: {exc}", file=sys.stderr)
        return None

    return Source(dest, f"archive:{archive.name}")


def clone_repo(url: str, dest: Path) -> Optional[Source]:
    ensure_dir(dest.parent)
    code, _, _ = sh(["git", "clone", "--depth", "1", url, str(dest)])
    if code == 0:
        return Source(dest, f"git:{url}")
    return None


def attach_local(path: Path, label: str) -> Optional[Source]:
    if path.exists():
        return Source(path, label)
    return None


@dataclass
class FileInfo:
    path: Path
    rel: str
    size: int
    sha256: str
    type_hint: str
    first_line: str


def detect_type(path: Path) -> str:
    if path.name.lower() == "dockerfile":
        return "dockerfile"

    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".md": "docs",
        ".rst": "docs",
        ".txt": "docs",
        ".toml": "toml",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
    }
    if path.suffix.lower() in mapping:
        return mapping[path.suffix.lower()]
    return "text" if is_text_file(path) else "binary"


def inventory(source: Source) -> List[FileInfo]:
    items: List[FileInfo] = []
    for path in source.root.rglob("*"):
        if not path.is_file():
            continue
        first_line = ""
        if is_text_file(path):
            first_line = next(iter(read_text(path, 4096).splitlines()), "")
        items.append(
            FileInfo(
                path=path,
                rel=str(path.relative_to(source.root)),
                size=path.stat().st_size,
                sha256=hash_file(path),
                type_hint=detect_type(path),
                first_line=first_line,
            )
        )
    return items


@dataclass
class Issue:
    severity: str
    kind: str
    file: str
    line: int
    message: str
    suggestion: Optional[str] = None


def scan_text(fi: FileInfo, content: str) -> List[Issue]:
    patterns = [
        (r"\bTODO\b", "INFO", "TODO", "Создайте задачу и ссылку."),
        (r"\bFIXME\b", "WARN", "FIXME", "Исправьте либо опишите причину."),
        (r"\bSTUB\b|\bPLACEHOLDER\b|\bDUMMY\b|\bMOCK\b", "WARN", "Stub", "Замените реализацией."),
        (r"NotImplementedError", "WARN", "NotImplemented", "Реализуйте или удалите."),
        (r"\bpass\b\s*(#.*)?$", "INFO", "EmptyBranch", "Добавьте реализацию/исключение."),
        (r"\bexec\(", "WARN", "Exec", "Избегайте exec."),
        (r"\beval\(", "WARN", "Eval", "Избегайте eval."),
        (r"except\s*:\s*$", "WARN", "BareExcept", "Укажите тип исключения."),
        (r"AKIA[0-9A-Z]{16}", "ERROR", "AWSKey", "Отзовите ключ."),
        (
            r"-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----",
            "ERROR",
            "PrivateKey",
            "Удалите из репозитория.",
        ),
        (
            r"(?i)password\s*=\s*[\"'][^\"']+[\"']",
            "ERROR",
            "HardcodedPassword",
            "Вынесите секреты.",
        ),
        (
            r"(?i)api[_-]?key\s*[:=]\s*[\"'][^\"']+[\"']",
            "ERROR",
            "APIKey",
            "Вынесите секреты.",
        ),
    ]

    issues: List[Issue] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        for pattern, severity, kind, suggestion in patterns:
            if re.search(pattern, line):
                issues.append(
                    Issue(
                        severity=severity,
                        kind=kind,
                        file=fi.rel,
                        line=idx,
                        message=line.strip()[:300],
                        suggestion=suggestion,
                    )
                )
    return issues


def analyze_python(fi: FileInfo, content: str) -> List[Issue]:
    issues: List[Issue] = []
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        issues.append(
            Issue(
                "ERROR",
                "PythonSyntaxError",
                fi.rel,
                exc.lineno or 1,
                str(exc),
                "Исправьте синтаксис.",
            )
        )
        return issues

    if ast.get_docstring(tree) in (None, ""):
        issues.append(
            Issue("INFO", "MissingModuleDoc", fi.rel, 1, "Нет докстринга.", "Добавьте описание."),
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(
                        Issue(
                            "WARN",
                            "MutableDefault",
                            fi.rel,
                            node.lineno,
                            "Мутируемый аргумент по умолчанию.",
                            "Используйте None и инициализируйте внутри.",
                        )
                    )
            if ast.get_docstring(node) in (None, ""):
                issues.append(
                    Issue(
                        "INFO",
                        "MissingFuncDoc",
                        fi.rel,
                        node.lineno,
                        f"Функция {node.name} без докстринга.",
                        "Опишите контракт.",
                    )
                )
        if isinstance(node, ast.ClassDef) and ast.get_docstring(node) in (None, ""):
            issues.append(
                Issue(
                    "INFO",
                    "MissingClassDoc",
                    fi.rel,
                    node.lineno,
                    f"Класс {node.name} без докстринга.",
                    "Опишите назначение.",
                )
            )
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                Issue(
                    "WARN",
                    "BareExcept",
                    fi.rel,
                    node.lineno,
                    "Голый except.",
                    "Уточните исключение.",
                )
            )

    return issues


def analyze_js_ts(fi: FileInfo, content: str) -> List[Issue]:
    issues: List[Issue] = []
    for idx, line in enumerate(content.splitlines(), start=1):
        if "console.log" in line and not fi.rel.startswith("scripts/"):
            issues.append(
                Issue(
                    "INFO",
                    "ConsoleLog",
                    fi.rel,
                    idx,
                    "console.log в исходниках.",
                    "Используйте централизованный логгер.",
                )
            )
        if ": any" in line:
            issues.append(
                Issue(
                    "WARN",
                    "AnyType",
                    fi.rel,
                    idx,
                    "Тип any в TS.",
                    "Уточните тип.",
                )
            )
        if "eval(" in line:
            issues.append(
                Issue("WARN", "EvalJS", fi.rel, idx, "Используется eval().", "Избегайте eval."),
            )
        if re.search(r"TODO|FIXME|STUB|PLACEHOLDER", line):
            issues.append(
                Issue(
                    "INFO",
                    "Note",
                    fi.rel,
                    idx,
                    "Обнаружена пометка в коде.",
                    "Создайте задачу.",
                )
            )
    return issues


@dataclass
class CognitiveSignal:
    component: str
    file: str
    line: int
    snippet: str


def scan_cognitive(fi: FileInfo, content: str) -> List[CognitiveSignal]:
    signals: List[CognitiveSignal] = []
    lowered = content.lower()
    lines = content.splitlines()
    for component, keys in COG_KEYS:
        for key in keys:
            for match in re.finditer(re.escape(key), lowered):
                line_no = lowered[: match.start()].count("\n") + 1
                snippet = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
                signals.append(
                    CognitiveSignal(component=component, file=fi.rel, line=line_no, snippet=snippet[:180])
                )
    return signals


def apply_safe_fixes(path: Path) -> Dict[str, int]:
    stats = {"trimmed": 0, "final_newline": 0, "black": 0, "isort": 0, "prettier": 0}
    for item in path.rglob("*"):
        if not (item.is_file() and is_text_file(item)):
            continue
        try:
            original = item.read_text(encoding="utf-8", errors="replace")
            normalized = "\n".join(line.rstrip() for line in original.splitlines()) + "\n"
            if normalized != original:
                item.write_text(normalized, encoding="utf-8")
                stats["trimmed"] += 1
                stats["final_newline"] += 1
        except Exception:
            continue

    code, _, _ = sh(["python", "-m", "black", "."], cwd=path)
    if code == 0:
        stats["black"] += 1
    code, _, _ = sh(["python", "-m", "isort", ".", "--profile", "black"], cwd=path)
    if code == 0:
        stats["isort"] += 1
    code, _, _ = sh(["npx", "-y", "prettier", "-w", "."], cwd=path)
    if code == 0:
        stats["prettier"] += 1
    return stats


def write_report(report_path: Path, context: Dict):
    buffer = io.StringIO()
    write = buffer.write

    write(f"# Аудит Искры — {now_iso()}\n\n")
    write("## Источники\n\n")
    for source in context["sources"]:
        write(f"- **{source['label']}** → `{source['root']}`\n")

    write("\n## Инвентаризация\n\n")
    write(
        f"- Всего файлов: **{context['stats']['files']}**, текстовых: **{context['stats']['text_files']}**\n"
    )
    types_line = ", ".join(f"{key}:{value}" for key, value in context["stats"]["types"].items())
    write(f"- Типы: {types_line}\n\n")

    write("## Найденные проблемы\n\n")
    for severity in ("ERROR", "WARN", "INFO"):
        items = [issue for issue in context["issues"] if issue.severity == severity]
        write(f"### {severity} ({len(items)})\n\n")
        for issue in items[:2000]:
            write(f"- `{issue.file}:{issue.line}` — **{issue.kind}**: {issue.message}")
            if issue.suggestion:
                write(f" → _{issue.suggestion}_")
            write("\n")
        write("\n")

    write("## Когнитивные сигналы\n\n")
    for component, signals in sorted(context["cognitive"].items()):
        write(f"### {component} ({len(signals)})\n")
        for signal in signals[:500]:
            write(f"- `{signal.file}:{signal.line}` — {signal.snippet}\n")
        write("\n")

    write("## Рекомендации по структуре\n\n")
    write(
        """```text
/src
  /iskra
    /agents
    /cognitive
    /memory
    /tools
    /planning
/tests
/docs
scripts/
configs/
```

"""
    )

    if "fixes" in context:
        write("## Автоправки\n\n")
        write("```json\n")
        write(json.dumps(context["fixes"], ensure_ascii=False, indent=2))
        write("\n```\n\n")

    report_path.write_text(buffer.getvalue(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Аудит и усиление Искры")
    parser.add_argument("--archive", type=str, default="", help="Путь к архиву Iskra_Prod_FINAL.(zip|tar.*|dir)")
    parser.add_argument("--repo", type=str, default="", help="Git URL репозитория")
    parser.add_argument("--project-dir", type=str, default="", help="Локальная директория проекта")
    parser.add_argument("--mnt", type=str, default="", help="Путь к /mnt (опционально)")
    parser.add_argument("--workdir", type=str, default="./_iskra_work", help="Рабочая директория")
    parser.add_argument("--report", type=str, default="./report.md", help="Путь отчёта")
    parser.add_argument(
        "--apply",
        type=str,
        choices=["yes", "no"],
        default="no",
        help="Применять безопасные автоправки",
    )
    parser.add_argument(
        "--online",
        type=str,
        choices=["yes", "no"],
        default="no",
        help="Онлайн-поиск (может быть недоступен)",
    )
    parser.add_argument("--confirm", type=str, default="", help="YES/NO подтверждение")

    args = parser.parse_args()

    confirm = (args.confirm or "NO").strip().upper()
    full_run = confirm == "YES"
    workdir = ensure_dir(Path(args.workdir))

    sources: List[Source] = []
    if args.archive:
        archive_source = unpack_archive(Path(args.archive), workdir / "archive")
        if archive_source:
            sources.append(archive_source)
    if args.repo:
        repo_source = clone_repo(args.repo, workdir / "repo")
        if repo_source:
            sources.append(repo_source)
    if args.project_dir:
        project_source = attach_local(Path(args.project_dir), "local_project")
        if project_source:
            sources.append(project_source)
    if args.mnt and Path(args.mnt).exists():
        sources.append(Source(Path(args.mnt), "mnt"))

    if not sources:
        print("[ERROR] Нет источников (--archive/--repo/--project-dir/--mnt)", file=sys.stderr)
        sys.exit(2)

    all_files: List[tuple[Source, FileInfo]] = []
    type_stats: Dict[str, int] = {}
    text_files = 0

    for source in sources:
        for file_info in inventory(source):
            all_files.append((source, file_info))
            type_stats[file_info.type_hint] = type_stats.get(file_info.type_hint, 0) + 1
            if is_text_file(file_info.path):
                text_files += 1

    issues: List[Issue] = []
    cognitive_map: Dict[str, List[CognitiveSignal]] = {key: [] for key, _ in COG_KEYS}

    for source, file_info in all_files:
        if not is_text_file(file_info.path):
            continue
        content = read_text(file_info.path)
        issues.extend(scan_text(file_info, content))
        if file_info.type_hint == "python":
            issues.extend(analyze_python(file_info, content))
        elif file_info.type_hint in {"javascript", "typescript"}:
            issues.extend(analyze_js_ts(file_info, content))
        for signal in scan_cognitive(file_info, content):
            cognitive_map.setdefault(signal.component, []).append(signal)

    fixes: Dict[str, Dict[str, int]] = {}
    if full_run and args.apply == "yes":
        for source in sources:
            if source.label == "mnt":
                continue
            fixes[source.label] = apply_safe_fixes(source.root)

    context = {
        "sources": [{"label": src.label, "root": str(src.root)} for src in sources],
        "stats": {
            "files": len(all_files),
            "text_files": text_files,
            "types": dict(sorted(type_stats.items(), key=lambda item: (-item[1], item[0]))),
        },
        "issues": issues,
        "cognitive": cognitive_map,
    }
    if fixes:
        context["fixes"] = fixes

    write_report(Path(args.report), context)

    errors = sum(1 for issue in issues if issue.severity == "ERROR")
    warnings = sum(1 for issue in issues if issue.severity == "WARN")
    infos = sum(1 for issue in issues if issue.severity == "INFO")

    print(
        f"[OK] Источники: {len(sources)} | Файлов: {len(all_files)} | Ошибок: {errors} | Предупр.: {warnings} | Инфо: {infos}"
    )
    print(f"[OK] Отчёт: {Path(args.report).resolve()}")


if __name__ == "__main__":  # pragma: no cover - точка входа CLI
    main()
