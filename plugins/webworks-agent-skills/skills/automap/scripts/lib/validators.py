"""File validation utilities for AutoMap scripts."""
from pathlib import Path
from .logging import log_error

def validate_file_exists(file_path: str, expected_ext: str) -> bool:
    """Validate that file exists and has expected extension."""
    path = Path(file_path)

    if not path.exists():
        log_error(f"File not found: {file_path}")
        return False

    if path.suffix.lower() != expected_ext.lower():
        log_error(f"Invalid file extension: {path.suffix} (expected {expected_ext})")
        return False

    return True

def validate_stationery_file(stationery_file: str) -> bool:
    """Validate stationery file exists and has .wxsp extension."""
    return validate_file_exists(stationery_file, '.wxsp')

def validate_job_file(job_file: str) -> bool:
    """Validate job file exists and has .waj extension."""
    return validate_file_exists(job_file, '.waj')
