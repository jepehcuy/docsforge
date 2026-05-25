"""Codebase scanner — file tree, language detection, basic AST extraction.

Scans a directory tree, detects languages by extension, extracts
basic structural info (imports, classes, functions) via Python ast
and regex for other languages. Output feeds specialist agents.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Extension → language mapping
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c_header",
    ".hpp": "cpp_header",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".sql": "sql",
    ".dockerfile": "dockerfile",
    ".proto": "protobuf",
    ".tf": "terraform",
}

# Files to always skip
SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules",
    ".tox", ".venv", "venv", "env", ".env",
    "dist", "build", ".eggs", "*.egg-info",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target",  # Rust
    ".next", ".nuxt",  # JS frameworks
}

SKIP_FILES = {
    ".DS_Store", "Thumbs.db", ".gitkeep",
    "poetry.lock", "package-lock.json", "yarn.lock",
}

# Max file size to analyze (bytes)
MAX_FILE_SIZE = 500_000  # 500KB
MAX_FILES = 10_000


@dataclass
class FileInfo:
    """Metadata for a single file."""
    path: str
    language: str
    size_bytes: int
    line_count: int = 0
    # AST-level info for supported languages
    imports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    docstrings: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Complete scan result for a codebase."""
    root: str
    files: list[FileInfo] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)  # lang → file count
    total_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    config_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_bytes": self.total_bytes,
            "languages": self.languages,
            "config_files": self.config_files,
            "doc_files": self.doc_files,
            "files": [
                {
                    "path": f.path,
                    "language": f.language,
                    "size_bytes": f.size_bytes,
                    "line_count": f.line_count,
                    "classes": f.classes,
                    "functions": f.functions,
                    "imports": f.imports,
                    "exports": f.exports,
                }
                for f in self.files
            ],
        }

    def source_files(self) -> list[FileInfo]:
        """Return only source code files (not config/docs)."""
        return [f for f in self.files if f.language not in ("json", "yaml", "toml", "markdown", "rst", "text")]

    def by_language(self, lang: str) -> list[FileInfo]:
        return [f for f in self.files if f.language == lang]


def detect_language(path: str) -> str:
    """Detect language from file extension."""
    ext = Path(path).suffix.lower()
    basename = Path(path).name.lower()
    if basename == "dockerfile":
        return "dockerfile"
    return EXTENSION_MAP.get(ext, "unknown")


def count_lines(content: str) -> int:
    """Count non-empty, non-comment lines."""
    count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
            count += 1
    return count


def extract_python_ast(content: str) -> dict[str, list[str]]:
    """Extract imports, classes, functions from Python source."""
    result = {"imports": [], "classes": [], "functions": [], "docstrings": []}
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [a.name for a in node.names]
            result["imports"].append(f"from {module} import {', '.join(names)}")
        elif isinstance(node, ast.ClassDef):
            result["classes"].append(node.name)
            # Extract class docstring
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                doc = node.body[0].value.value if isinstance(node.body[0].value, ast.Constant) else node.body[0].value.s
                if doc:
                    result["docstrings"].append(f"class {node.name}: {doc[:200]}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append(node.name)

    return result


def extract_js_ts_info(content: str) -> dict[str, list[str]]:
    """Extract imports, exports, functions from JS/TS source via regex."""
    result = {"imports": [], "classes": [], "functions": [], "exports": []}

    # Imports
    for m in re.finditer(r'(?:import|from)\s+.*?from\s+["\']([^"\']+)["\']', content):
        result["imports"].append(m.group(1))
    for m in re.finditer(r'import\s*\(\s*["\']([^"\']+)["\']', content):
        result["imports"].append(m.group(1))

    # Exports
    for m in re.finditer(r'export\s+(?:default\s+)?(?:class|function|const|let|var|async)\s+(\w+)', content):
        result["exports"].append(m.group(1))

    # Classes
    for m in re.finditer(r'class\s+(\w+)', content):
        result["classes"].append(m.group(1))

    # Functions (named, not arrow in assignments)
    for m in re.finditer(r'(?:function|async\s+function)\s+(\w+)', content):
        result["functions"].append(m.group(1))

    return result


def extract_go_info(content: str) -> dict[str, list[str]]:
    """Extract imports, types, functions from Go source via regex."""
    result = {"imports": [], "classes": [], "functions": [], "exports": []}

    for m in re.finditer(r'import\s+(?:\(\s*)?(?:"([^"]+)"|(\w+)\s+"([^"]+)")', content):
        result["imports"].append(m.group(1) or m.group(3))

    for m in re.finditer(r'type\s+(\w+)\s+struct', content):
        result["classes"].append(m.group(1))

    for m in re.finditer(r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(', content):
        name = m.group(1)
        result["functions"].append(name)
        if name[0].isupper():
            result["exports"].append(name)

    return result


def extract_structural_info(filepath: str, content: str, language: str) -> dict[str, list[str]]:
    """Extract structural info based on language."""
    if language == "python":
        return extract_python_ast(content)
    elif language in ("javascript", "typescript"):
        return extract_js_ts_info(content)
    elif language == "go":
        return extract_go_info(content)
    return {}


def is_config_file(path: str) -> bool:
    """Check if a file is a configuration file."""
    config_names = {
        "package.json", "tsconfig.json", "pyproject.toml", "setup.py", "setup.cfg",
        "Cargo.toml", "go.mod", "go.sum", "pom.xml", "build.gradle",
        "Makefile", "CMakeLists.txt", "Dockerfile", "docker-compose.yml",
        "docker-compose.yaml", ".env", ".env.example", ".env.local",
        ".eslintrc", ".prettierrc", ".babelrc", "jest.config.js",
        "webpack.config.js", "vite.config.js", "tsconfig.json",
        "requirements.txt", "poetry.lock", "Gemfile", "Gemfile.lock",
        ".github", "tox.ini", "mypy.ini", ".flake8", ".pylintrc",
        "mkdocs.yml", "conf.py",
    }
    basename = Path(path).name
    return basename in config_names or basename.startswith(".")


def is_doc_file(path: str) -> bool:
    """Check if a file is documentation."""
    doc_names = {"README", "CHANGELOG", "CONTRIBUTING", "LICENSE", "AUTHORS", "HISTORY"}
    basename = Path(path).stem.upper()
    ext = Path(path).suffix.lower()
    return basename in doc_names or ext in (".md", ".rst", ".txt") and basename.lower() != "requirements"


def scan_codebase(
    root: str,
    exclude_dirs: set[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> ScanResult:
    """Scan a codebase directory tree.

    Args:
        root: Root directory to scan
        exclude_dirs: Additional directories to exclude
        exclude_patterns: Glob patterns to exclude (unused currently)

    Returns:
        ScanResult with file tree and structural info
    """
    root = os.path.abspath(root)
    exclude = SKIP_DIRS | (exclude_dirs or set())
    result = ScanResult(root=root)

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude and not d.startswith(".")]

        for fname in filenames:
            if len(result.files) >= MAX_FILES:
                break

            if fname in SKIP_FILES:
                continue

            filepath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(filepath, root)

            try:
                stat = os.stat(filepath)
            except OSError:
                continue

            if stat.st_size > MAX_FILE_SIZE:
                continue

            language = detect_language(filepath)

            # Read and analyze source files
            content = ""
            line_count = 0
            info: dict[str, list[str]] = {}

            if language not in ("unknown", "binary") and stat.st_size > 0:
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    line_count = count_lines(content)
                    info = extract_structural_info(filepath, content, language)
                except (OSError, UnicodeDecodeError):
                    pass

            fi = FileInfo(
                path=relpath,
                language=language,
                size_bytes=stat.st_size,
                line_count=line_count,
                imports=info.get("imports", []),
                classes=info.get("classes", []),
                functions=info.get("functions", []),
                exports=info.get("exports", []),
                docstrings=info.get("docstrings", []),
            )
            result.files.append(fi)

            # Track stats
            result.languages[language] = result.languages.get(language, 0) + 1
            result.total_files += 1
            result.total_lines += line_count
            result.total_bytes += stat.st_size

            if is_config_file(relpath):
                result.config_files.append(relpath)
            if is_doc_file(relpath):
                result.doc_files.append(relpath)

    return result
