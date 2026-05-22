"""Shared constants for AutoMap scripts."""

# Exit codes
EXIT_SUCCESS = 0
EXIT_FILE_ERROR = 1
EXIT_ARG_ERROR = 2
EXIT_VALIDATION_ERROR = 3
EXIT_PARSE_ERROR = 3
EXIT_NO_FORMATS = 3
EXIT_NO_TARGETS = 3
EXIT_CANCELLED = 4

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

# XML namespaces
EPUBLISHER_NS = {'ep': 'urn:WebWorks-Publish-Project'}
