"""Logging utilities for AutoMap scripts."""
import sys
from .constants import RED, BLUE, GREEN, YELLOW, NC

def log_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)

def log_info(message: str) -> None:
    """Print info message."""
    print(f"{BLUE}[INFO]{NC} {message}")

def log_success(message: str) -> None:
    """Print success message."""
    print(f"{GREEN}[SUCCESS]{NC} {message}")

def log_verbose(message: str, verbose: bool) -> None:
    """Print verbose message to stderr."""
    if verbose:
        print(f"[VERBOSE] {message}", file=sys.stderr)
