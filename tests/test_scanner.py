"""Tests for DocsForge scanner module."""

import os
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.scanner import (
    scan_codebase, detect_language, count_lines,
    extract_python_ast, extract_js_ts_info, is_config_file, is_doc_file,
)


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("main.py") == "python"
        assert detect_language("foo/bar.py") == "python"

    def test_javascript(self):
        assert detect_language("index.js") == "javascript"
        assert detect_language("app.jsx") == "javascript"

    def test_typescript(self):
        assert detect_language("main.ts") == "typescript"
        assert detect_language("app.tsx") == "typescript"

    def test_go(self):
        assert detect_language("main.go") == "go"

    def test_rust(self):
        assert detect_language("main.rs") == "rust"

    def test_dockerfile(self):
        assert detect_language("Dockerfile") == "dockerfile"

    def test_unknown(self):
        assert detect_language("foo.xyz") == "unknown"

    def test_config_files(self):
        assert detect_language("package.json") == "json"
        assert detect_language("Cargo.toml") == "toml"


class TestCountLines:
    def test_basic(self):
        assert count_lines("hello\nworld\n") == 2

    def test_empty_lines(self):
        assert count_lines("hello\n\n\nworld") == 2

    def test_comments(self):
        assert count_lines("# comment\nhello\n// another") == 1


class TestExtractPythonAST:
    def test_imports(self):
        code = "import os\nfrom pathlib import Path\n"
        info = extract_python_ast(code)
        assert "os" in info["imports"]

    def test_classes(self):
        code = "class MyClass:\n    pass\n"
        info = extract_python_ast(code)
        assert "MyClass" in info["classes"]

    def test_functions(self):
        code = "def hello():\n    pass\nasync def world():\n    pass\n"
        info = extract_python_ast(code)
        assert "hello" in info["functions"]
        assert "world" in info["functions"]

    def test_syntax_error(self):
        info = extract_python_ast("def broken(:\n")
        assert info["classes"] == []


class TestExtractJSInfo:
    def test_imports(self):
        code = 'import React from "react";\nimport { useState } from "react";\n'
        info = extract_js_ts_info(code)
        assert len(info["imports"]) >= 1

    def test_exports(self):
        code = "export function foo() {}\nexport default class Bar {}\n"
        info = extract_js_ts_info(code)
        assert "foo" in info["exports"]
        assert "Bar" in info["exports"]


class TestIsConfigFile:
    def test_package_json(self):
        assert is_config_file("package.json") is True

    def test_pyproject(self):
        assert is_config_file("pyproject.toml") is True

    def test_not_config(self):
        assert is_config_file("main.py") is False


class TestIsDocFile:
    def test_readme(self):
        assert is_doc_file("README.md") is True

    def test_changelog(self):
        assert is_doc_file("CHANGELOG.md") is True

    def test_not_doc(self):
        assert is_doc_file("main.py") is False


class TestScanCodebase:
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_codebase(tmpdir)
            assert result.total_files == 0

    def test_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Python file
            py_file = os.path.join(tmpdir, "main.py")
            with open(py_file, "w") as f:
                f.write("import os\n\ndef hello():\n    pass\n")

            # Create config file
            json_file = os.path.join(tmpdir, "package.json")
            with open(json_file, "w") as f:
                f.write('{"name": "test"}')

            result = scan_codebase(tmpdir)
            assert result.total_files == 2
            assert "python" in result.languages
            assert result.languages["python"] == 1

    def test_excludes_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = os.path.join(tmpdir, ".git")
            os.makedirs(git_dir)
            with open(os.path.join(git_dir, "config"), "w") as f:
                f.write("git config")

            py_file = os.path.join(tmpdir, "main.py")
            with open(py_file, "w") as f:
                f.write("x = 1\n")

            result = scan_codebase(tmpdir)
            assert result.total_files == 1

    def test_nested_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "src", "pkg")
            os.makedirs(nested)
            with open(os.path.join(nested, "mod.py"), "w") as f:
                f.write("x = 1\n")

            result = scan_codebase(tmpdir)
            assert result.total_files == 1
            assert result.files[0].path == os.path.join("src", "pkg", "mod.py")

    def test_excludes_node_modules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nm = os.path.join(tmpdir, "node_modules", "pkg")
            os.makedirs(nm)
            with open(os.path.join(nm, "index.js"), "w") as f:
                f.write("console.log('hi')")

            main = os.path.join(tmpdir, "main.py")
            with open(main, "w") as f:
                f.write("x = 1\n")

            result = scan_codebase(tmpdir)
            assert result.total_files == 1

    def test_to_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "a.py"), "w") as f:
                f.write("x = 1\n")
            result = scan_codebase(tmpdir)
            d = result.to_dict()
            assert "total_files" in d
            assert "files" in d
            assert len(d["files"]) == 1

    def test_source_files_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "a.py"), "w") as f:
                f.write("x = 1\n")
            with open(os.path.join(tmpdir, "data.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# Test")
            result = scan_codebase(tmpdir)
            source = result.source_files()
            assert len(source) == 1
            assert source[0].language == "python"
