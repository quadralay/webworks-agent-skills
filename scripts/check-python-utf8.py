#!/usr/bin/env python3
"""
check-python-utf8.py

Static check that every Python tool follows the UTF-8 conventions from
CONTRIBUTING.md "New Python Tools" (issue #118). Run from the repo root;
exits 1 with file:line findings when a tool would break on a Windows
locale-codepage (cp1252/cp932) console.

Rules:
    entry-point-preamble   A file with a __main__ guard must reconfigure
                           sys.stdout/sys.stderr to UTF-8 (the template's
                           ensure_utf8()).
    subprocess-encoding    No text=True / universal_newlines=True without
                           encoding= — pipe decoding otherwise uses the
                           locale codepage (PYTHONIOENCODING is ignored).
    open-encoding          Builtin text-mode open() must pass encoding=.
    read-write-text        Path.read_text()/write_text() must pass encoding=.

Usage:
    python scripts/check-python-utf8.py [root ...]

Roots default to plugins/, templates/, and scripts/ (this checker holds
itself to the same rules).

Exit codes:
    0 - Clean.
    1 - Findings reported.
    2 - IO or parse failure (file unreadable, syntax error).
"""

import ast
import os
import sys
from pathlib import Path

# ANSI color codes (shared house style across skill tools)
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

SKIP_DIRS = {'__pycache__', 'node_modules', '.git'}

DEFAULT_ROOTS = ['plugins', 'templates', 'scripts']


def ensure_utf8() -> None:
    """Make this tool Unicode-safe regardless of the caller's environment.

    UTF-8 mode is read at interpreter startup, so the setdefault only
    affects Python children spawned later; the reconfigure handles this
    process's own stdio on locale-codepage consoles (Windows cp1252).
    """
    os.environ.setdefault('PYTHONUTF8', '1')
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass


def _is_true_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _open_mode_is_binary(call: ast.Call) -> bool:
    """True when an open() call's mode argument is a constant containing 'b'."""
    mode_node = None
    if len(call.args) >= 2:
        mode_node = call.args[1]
    for keyword in call.keywords:
        if keyword.arg == 'mode':
            mode_node = keyword.value
    if mode_node is None:
        return False
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return 'b' in mode_node.value
    # Dynamic mode expression: cannot prove binary, treat as text so the
    # call still needs an explicit encoding.
    return False


def check_file(path: Path) -> list:
    """Return (line, rule, message) findings for one Python file."""
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text, filename=str(path))
    findings: list = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        keyword_names = {k.arg for k in node.keywords if k.arg}

        for keyword in node.keywords:
            if (
                keyword.arg in ('text', 'universal_newlines')
                and _is_true_constant(keyword.value)
                and 'encoding' not in keyword_names
            ):
                findings.append((
                    node.lineno, 'subprocess-encoding',
                    f"{keyword.arg}=True without encoding= — pipes decode "
                    "with the locale codepage on Windows",
                ))

        if isinstance(node.func, ast.Name) and node.func.id == 'open':
            if not _open_mode_is_binary(node) and 'encoding' not in keyword_names:
                findings.append((
                    node.lineno, 'open-encoding',
                    "text-mode open() without encoding=",
                ))

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in ('read_text', 'write_text')
            and 'encoding' not in keyword_names
        ):
            findings.append((
                node.lineno, 'read-write-text',
                f"{node.func.attr}() without encoding=",
            ))

    if "__main__" in text and 'reconfigure(encoding' not in text:
        findings.append((
            1, 'entry-point-preamble',
            "entry point never reconfigures stdout/stderr to UTF-8 — "
            "add the template's ensure_utf8() (see CONTRIBUTING.md)",
        ))

    return findings


def iter_python_files(roots: list) -> list:
    result = []
    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob('*.py')):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            result.append(path)
    return result


def main() -> int:
    ensure_utf8()

    roots = sys.argv[1:] or DEFAULT_ROOTS
    files = iter_python_files(roots)
    if not files:
        print(f"{RED}[ERROR]{NC} no Python files found under: {', '.join(roots)}",
              file=sys.stderr)
        return 2

    total = 0
    for path in files:
        try:
            findings = check_file(path)
        except (OSError, UnicodeDecodeError, SyntaxError) as e:
            print(f"{RED}[ERROR]{NC} {path}: {e}", file=sys.stderr)
            return 2
        for line, rule, message in findings:
            total += 1
            print(f"{YELLOW}{path}:{line}{NC} [{rule}] {message}")

    if total:
        print(f"\n{RED}FAIL:{NC} {total} finding(s) across {len(files)} file(s)")
        return 1
    print(f"{GREEN}OK:{NC} {len(files)} file(s) follow the UTF-8 conventions")
    return 0


if __name__ == '__main__':
    sys.exit(main())
