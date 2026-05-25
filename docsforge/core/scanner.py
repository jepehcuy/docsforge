"""Repo Scanner — walks a codebase and extracts structure metadata."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
}

IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "dist", "build", ".pytest_cache", ".mypy_cache", "site",
    ".docsforge", ".idea", ".vscode", "target",
}

CONFIG_FILES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "Gemfile", "pom.xml", "build.gradle",
    "requirements.txt", "Pipfile", "poetry.lock", ".env.example",
    "docker-compose.yml", "Dockerfile", "Makefile", "tsconfig.json",
}


@dataclass
class FileEntry:
    """One file in the repo."""
    path: str           # relative to repo root
    abs_path: str
    language: str
    size: int
    lines: int


@dataclass
class PythonSymbol:
    """A public function or class extracted via AST."""
    name: str
    kind: str           # "function" | "class" | "method"
    file: str
    line: int
    docstring: str | None
    signature: str
    is_async: bool = False


@dataclass
class RepoMeta:
    """Aggregate metadata for the entire repo."""
    root: str
    name: str
    files: list[FileEntry] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)  # lang -> file count
    config_files: list[str] = field(default_factory=list)
    has_git: bool = False
    has_tests: bool = False
    has_examples: bool = False
    readme_path: str | None = None
    python_symbols: list[PythonSymbol] = field(default_factory=list)
    total_loc: int = 0


def scan_repo(repo_path: str | Path, max_file_size: int = 500_000) -> RepoMeta:
    """Walk a repo and return structured metadata."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    meta = RepoMeta(root=str(root), name=root.name)
    meta.has_git = (root / ".git").exists()

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]

        rel_dir = Path(dirpath).relative_to(root)
        rel_str = str(rel_dir).lower()
        if "test" in rel_str:
            meta.has_tests = True
        if "example" in rel_str:
            meta.has_examples = True

        for fname in filenames:
            abs_path = Path(dirpath) / fname
            rel_path = abs_path.relative_to(root)

            # README detection
            if fname.lower().startswith("readme") and meta.readme_path is None:
                meta.readme_path = str(rel_path)

            # Config file detection
            if fname in CONFIG_FILES:
                meta.config_files.append(str(rel_path))

            ext = abs_path.suffix.lower()
            lang = SUPPORTED_EXTENSIONS.get(ext)
            if lang is None:
                continue

            try:
                size = abs_path.stat().st_size
            except OSError:
                continue
            if size > max_file_size:
                continue

            try:
                text = abs_path.read_text(encoding="utf-8", errors="ignore")
                lines = text.count("\n") + 1
            except OSError:
                continue

            entry = FileEntry(
                path=str(rel_path),
                abs_path=str(abs_path),
                language=lang,
                size=size,
                lines=lines,
            )
            meta.files.append(entry)
            meta.languages[lang] = meta.languages.get(lang, 0) + 1
            meta.total_loc += lines

            # Extract Python symbols
            if lang == "python":
                try:
                    tree = ast.parse(text)
                    meta.python_symbols.extend(
                        _extract_python_symbols(tree, str(rel_path))
                    )
                except (SyntaxError, ValueError):
                    pass

    return meta


def _extract_python_symbols(tree: ast.Module, rel_path: str) -> list[PythonSymbol]:
    """Pull top-level functions and classes from a Python AST."""
    out: list[PythonSymbol] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            out.append(PythonSymbol(
                name=node.name,
                kind="function",
                file=rel_path,
                line=node.lineno,
                docstring=ast.get_docstring(node),
                signature=_format_signature(node),
                is_async=isinstance(node, ast.AsyncFunctionDef),
            ))
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            out.append(PythonSymbol(
                name=node.name,
                kind="class",
                file=rel_path,
                line=node.lineno,
                docstring=ast.get_docstring(node),
                signature=f"class {node.name}",
            ))
            # Methods
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if child.name.startswith("_") and child.name != "__init__":
                        continue
                    out.append(PythonSymbol(
                        name=f"{node.name}.{child.name}",
                        kind="method",
                        file=rel_path,
                        line=child.lineno,
                        docstring=ast.get_docstring(child),
                        signature=_format_signature(child),
                        is_async=isinstance(child, ast.AsyncFunctionDef),
                    ))
    return out


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Render a Python function signature as a string."""
    args = []
    for arg in node.args.args:
        if arg.annotation:
            try:
                args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
            except Exception:
                args.append(arg.arg)
        else:
            args.append(arg.arg)

    returns = ""
    if node.returns:
        try:
            returns = f" -> {ast.unparse(node.returns)}"
        except Exception:
            pass

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)}){returns}"


def summarize_repo(meta: RepoMeta) -> str:
    """One-paragraph human-readable summary used for agent prompts."""
    lang_summary = ", ".join(
        f"{lang} ({count} files)" for lang, count in
        sorted(meta.languages.items(), key=lambda kv: -kv[1])
    )
    parts = [
        f"Repository: {meta.name}",
        f"Total files: {len(meta.files)}",
        f"Languages: {lang_summary or 'none detected'}",
        f"Total LOC: {meta.total_loc}",
        f"Has git: {meta.has_git}",
        f"Has tests: {meta.has_tests}",
        f"Has examples: {meta.has_examples}",
        f"README: {meta.readme_path or 'missing'}",
        f"Config files: {len(meta.config_files)} ({', '.join(meta.config_files[:5])})",
        f"Public Python symbols: {len(meta.python_symbols)}",
    ]
    return "\n".join(parts)
