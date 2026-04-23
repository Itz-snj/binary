"""
SlothOps Engine — Code Fetcher
Downloads relevant source files from the target GitHub repository
using PyGithub so the LLM has context for generating fixes.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from github import Github, GithubException

logger = logging.getLogger("slothops.code_fetcher")

# Max number of import files to fetch alongside the main file
_MAX_IMPORT_FILES = 3
_MAX_TOTAL_FILES = 7


TEST_CONVENTIONS = {
    "javascript": {"src_dir": "src/", "test_dir": "tests/", "suffix": ".test", "exts": [".js"]},
    "typescript": {"src_dir": "src/", "test_dir": "tests/", "suffix": ".test", "exts": [".ts"]},
    "python": {"src_dir": "", "test_dir": "tests/", "prefix": "test_", "exts": [".py"]},
    "go": {"src_dir": "", "test_dir": "", "suffix": "_test", "exts": [".go"]},
    "java": {"src_dir": "src/main/java/", "test_dir": "src/test/java/", "suffix": "Test", "exts": [".java"]},
    "rust": None,
    "ruby": {"src_dir": "lib/", "test_dir": "spec/", "suffix": "_spec", "exts": [".rb"]},
}


def _get_test_path(file_path: str, language: str = "javascript") -> Optional[str]:
    """
    Derive the conventional test file path from a source file path.

    Convention varies by language:
      - JS/TS: src/routes/users.ts → tests/routes/users.test.ts
      - Python: app.py → tests/test_app.py
      - Go: main.go → main_test.go
      - Java: src/main/java/Foo.java → src/test/java/FooTest.java
    """
    if not file_path:
        return None

    conv = TEST_CONVENTIONS.get(language)
    if conv is None:
        return None

    test_path = file_path

    if conv["src_dir"] and test_path.startswith(conv["src_dir"]):
        test_path = conv["test_dir"] + test_path[len(conv["src_dir"]):]
    elif conv["test_dir"] and not test_path.startswith(conv["test_dir"]):
        parts = test_path.split("/")
        if conv["src_dir"]:
            for src in parts:
                if src and src != conv["src_dir"].rstrip("/"):
                    test_path = conv["test_dir"] + test_path
                    break

    base_name = test_path.rsplit("/", 1)[-1] if "/" in test_path else test_path
    dir_path = test_path.rsplit("/", 1)[0] + "/" if "/" in test_path else ""

    for ext in conv["exts"]:
        if base_name.endswith(ext):
            base_name = base_name[: -len(ext)]
            break

    prefix = conv.get("prefix", "")
    suffix = conv["suffix"]
    final_ext = conv["exts"][0] if conv["exts"] else ""

    test_path = dir_path + prefix + base_name + suffix + final_ext

    if test_path == file_path:
        return None

    return test_path


def _resolve_relative_path(rel: str, base_dir: str) -> str:
    """Resolve relative import path against base directory."""
    parts = base_dir.rstrip("/").split("/")
    for segment in rel.split("/"):
        if segment == "..":
            if parts:
                parts.pop()
        elif segment != ".":
            parts.append(segment)
    return "/".join(parts)


def _extract_js_imports(source: str, base_dir: str) -> list[str]:
    """Parse local import paths from TypeScript / JavaScript source."""
    pattern = r"""(?:import\s+.*?\s+from\s+['"](\.[^'"]+)['"]|require\(\s*['"](\.[^'"]+)['"]\s*\))"""
    matches = re.findall(pattern, source)

    paths: list[str] = []
    for groups in matches:
        rel = groups[0] or groups[1]
        if not rel:
            continue

        resolved = _resolve_relative_path(rel, base_dir)

        if not resolved.endswith((".ts", ".js", ".tsx", ".jsx")):
            resolved += ".ts"

        if resolved not in paths:
            paths.append(resolved)

    return paths


def _extract_python_imports(source: str, base_dir: str) -> list[str]:
    """Parse Python: import x / from x import y"""
    pattern = r"(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"
    matches = re.findall(pattern, source)
    paths = []
    for groups in matches:
        module = groups[0] or groups[1]
        if not module:
            continue
        parts = module.split(".")
        rel_path = "/".join(parts) + ".py"
        resolved = _resolve_relative_path(rel_path, base_dir)
        if resolved not in paths:
            paths.append(resolved)
    return paths


def _extract_go_imports(source: str, base_dir: str) -> list[str]:
    """Parse Go: import \"pkg/path\" — only local (relative) imports."""
    pattern = r'import\s+(?:\(\s*([\s\S]*?)\s*\)|"([^"]+)")'
    matches = re.findall(pattern, source)
    paths = []
    for groups in matches:
        import_block = groups[0] or groups[1]
        if not import_block:
            continue
        single_pattern = r'"([^"]+)"'
        single_matches = re.findall(single_pattern, import_block)
        for pkg in single_matches:
            if pkg.startswith(".") or (not pkg.startswith("/") and "." not in pkg):
                rel_path = pkg + ".go"
                resolved = _resolve_relative_path(rel_path, base_dir)
                if resolved not in paths:
                    paths.append(resolved)
    return paths


def _extract_java_imports(source: str, base_dir: str) -> list[str]:
    """Parse Java: import com.pkg.Class → src/main/java/com/pkg/Class.java"""
    pattern = r"import\s+([\w.]+);"
    matches = re.findall(pattern, source)
    paths = []
    for module in matches:
        parts = module.split(".")
        rel_path = "/".join(parts) + ".java"
        resolved = _resolve_relative_path(rel_path, base_dir)
        if resolved not in paths:
            paths.append(resolved)
    return paths


def _extract_rust_imports(source: str, base_dir: str) -> list[str]:
    """Parse Rust: use crate::module → src/module.rs"""
    pattern = r"use\s+crate::([\w:]+)"
    matches = re.findall(pattern, source)
    paths = []
    for module in matches:
        parts = module.split("::")
        rel_path = "/".join(parts) + ".rs"
        resolved = _resolve_relative_path(rel_path, base_dir)
        if resolved not in paths:
            paths.append(resolved)
    return paths


def _extract_ruby_imports(source: str, base_dir: str) -> list[str]:
    """Parse Ruby: require 'path' / require_relative 'path'"""
    pattern = r"require(?:_relative)?\s+['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern, source)
    paths = []
    for rel in matches:
        if rel.startswith(".") or rel.startswith("/"):
            if not rel.endswith(".rb"):
                rel += ".rb"
            resolved = _resolve_relative_path(rel, base_dir)
            if resolved not in paths:
                paths.append(resolved)
    return paths


def _extract_imports(source: str, base_dir: str, language: str = "javascript") -> list[str]:
    """Parse local import paths based on detected language."""
    extractors = {
        "javascript": _extract_js_imports,
        "typescript": _extract_js_imports,
        "python": _extract_python_imports,
        "go": _extract_go_imports,
        "java": _extract_java_imports,
        "rust": _extract_rust_imports,
        "ruby": _extract_ruby_imports,
    }
    extractor = extractors.get(language, _extract_js_imports)
    return extractor(source, base_dir)[:_MAX_IMPORT_FILES]


def _fetch_file(repo, path: str) -> Optional[str]:
    """Fetch a single file's decoded content from GitHub. Returns None on 404."""
    try:
        content_file = repo.get_contents(path)
        if isinstance(content_file, list):
            return None  # It's a directory
        return content_file.decoded_content.decode("utf-8")
    except GithubException as exc:
        if exc.status == 404:
            logger.debug("File not found on GitHub: %s", path)
        else:
            logger.warning("GitHub error fetching %s: %s", path, exc)
        return None


def fetch_code_context(
    file_path: str | None,
    repo,
    source_content_override: str | None = None,
    language: str = "javascript",
) -> dict[str, str]:
    """
    Fetch code context from GitHub for the failing file.

    Returns a dict mapping file paths to their full content::

        {
            "src/routes/users.ts": "...",
            "tests/routes/users.test.ts": "...",
            "src/services/userService.ts": "...",
        }

    At most 5 files are returned (main + test + up to 3 imports).
    """
    if not file_path:
        return {}

    context: dict[str, str] = {}

    main_content = source_content_override or _fetch_file(repo, file_path)
    if main_content:
        context[file_path] = main_content
    else:
        logger.warning("Could not fetch main file: %s", file_path)
        return context

    test_path = _get_test_path(file_path, language)
    if test_path:
        test_content = _fetch_file(repo, test_path)
        if test_content:
            context[test_path] = test_content

    base_dir = "/".join(file_path.split("/")[:-1])
    import_paths = _extract_imports(main_content, base_dir, language)
    for imp_path in import_paths:
        if imp_path not in context:
            imp_content = _fetch_file(repo, imp_path)
            if imp_content:
                context[imp_path] = imp_content

    return context


def fetch_deep_code_context(
    file_path: str | None,
    call_chain: list[object],
    repo,
    language: str = "javascript",
) -> dict[str, str]:
    """
    Fetch the crash site + all files in the call chain.

    Strategy:
      1. Crash site file (from file_path)
      2. Direct imports of crash site (up to 2)
      3. Every unique file in call_chain (up to 5)
      4. Cap at _MAX_TOTAL_FILES total
    """
    if not file_path:
        return {}

    context: dict[str, str] = {}

    main_content = _fetch_file(repo, file_path)
    if main_content:
        context[file_path] = main_content
    else:
        logger.warning("Could not fetch crash site: %s", file_path)
        return context

    base_dir = "/".join(file_path.split("/")[:-1])
    for imp_path in _extract_imports(main_content, base_dir, language)[:2]:
        if len(context) >= _MAX_TOTAL_FILES:
            break
        if imp_path not in context:
            imp_content = _fetch_file(repo, imp_path)
            if imp_content:
                context[imp_path] = imp_content

    for frame in call_chain:
        if len(context) >= _MAX_TOTAL_FILES:
            break
        if hasattr(frame, "file_path"):
            fp = frame.file_path
            if fp not in context:
                content = _fetch_file(repo, fp)
                if content:
                    context[fp] = content

    logger.debug("Deep fetch returned %d files (cap: %d)", len(context), _MAX_TOTAL_FILES)
    return context


def fetch_requested_files(
    file_paths: list[str],
    repo,
) -> dict[str, str]:
    """
    Fetch a specific list of files requested by the LLM
    for second-pass deep scanning.
    """
    context: dict[str, str] = {}
    for fp in file_paths[:5]:  # cap at 5 additional files
        if fp not in context:
            content = _fetch_file(repo, fp)
            if content:
                context[fp] = content
    return context
