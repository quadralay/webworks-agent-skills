#!/usr/bin/env python3
"""
<tool-name>.py

One-line description of what this tool does.

Template notes (delete this docstring block when copying):
    Start new skill Python tools from this file. It bakes in the UTF-8
    conventions from issue #118 so Unicode content — Japanese output paths,
    CJK landmark IDs like 概要, non-ASCII group names — survives stock
    Windows consoles (cp1252/cp932). The three rules, in one place:

    1. ensure_utf8() runs first thing in main(). Python children spawned
       later start in full UTF-8 mode, and this process's own stdout/stderr
       print Unicode safely regardless of the console codepage.
    2. Text-mode file I/O always names its encoding:
       open(p, encoding='utf-8'), Path.read_text(encoding='utf-8'),
       Path.write_text(..., encoding='utf-8'). The interpreter default
       tracks the locale codepage on Windows until Python 3.15.
    3. subprocess never uses bare text=True — pipe decoding ignores
       PYTHONIOENCODING and falls back to the locale codepage, which
       silently turns a child's UTF-8 output into stdout=None when the
       reader thread dies. Use run_utf8() (or pass encoding='utf-8'
       explicitly).

Usage:
    python <tool-name>.py <input> [options]

Exit codes:
    0 - Success.
    1 - Usage error or recoverable failure (bad arguments, lookup miss).
    2 - Parse failure or IO failure (file missing, malformed input).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ANSI color codes (shared house style across skill tools)
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

DEBUG = os.environ.get('DEBUG', '0') == '1'


def ensure_utf8() -> None:
    """Make this tool Unicode-safe regardless of the caller's environment.

    UTF-8 mode is read at interpreter startup, so the setdefault cannot fix
    the *current* process — it guarantees every Python child spawned later
    starts in full UTF-8 mode. The reconfigure handles this process's own
    stdio, which Windows otherwise initializes to the console codepage and
    which raises UnicodeEncodeError on the first non-ASCII path or ID
    printed. The try/except keeps redirected or captured streams (which may
    lack reconfigure) from breaking the tool.
    """
    os.environ.setdefault('PYTHONUTF8', '1')
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass


def debug_log(message: str) -> None:
    """Print debug message to stderr when DEBUG=1."""
    if DEBUG:
        print(f"{YELLOW}[DEBUG]{NC} {message}", file=sys.stderr)


def error_log(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def warn_log(message: str) -> None:
    """Print warning message to stderr (unconditional, unlike debug_log)."""
    print(f"{YELLOW}[WARN]{NC} {message}", file=sys.stderr)


def run_utf8(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run with UTF-8 pipes. Use this instead of text=True.

    Bare text=True decodes child pipes with the locale codepage on Windows
    (PYTHONIOENCODING does not change this). errors='replace' keeps
    diagnostics flowing even if a child emits a stray byte; drop it via
    kwargs when byte-exact output matters.
    """
    kwargs.setdefault('encoding', 'utf-8')
    kwargs.setdefault('errors', 'replace')
    return subprocess.run(cmd, **kwargs)


def read_input(path: Path) -> str:
    """Example file read — text-mode I/O always names its encoding."""
    return path.read_text(encoding='utf-8')


def main() -> int:
    ensure_utf8()

    parser = argparse.ArgumentParser(
        description='One-line description of what this tool does.',
    )
    parser.add_argument('input', help='Path to the input file')
    args = parser.parse_args()

    source = Path(args.input)
    if not source.is_file():
        error_log(f"not a file: {source}")
        return 2

    try:
        text = read_input(source)
    except (OSError, UnicodeDecodeError) as e:
        error_log(f"{source}: {e}")
        return 2

    debug_log(f"read {len(text)} characters from {source}")
    print(f"{GREEN}OK{NC} {source}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
