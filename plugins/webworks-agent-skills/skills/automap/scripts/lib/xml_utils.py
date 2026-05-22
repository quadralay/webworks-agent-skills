"""XML parsing utilities for AutoMap scripts."""
from typing import Optional
# Use defusedxml to prevent XXE attacks (CWE-611)
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element  # For type hints only
from .constants import EPUBLISHER_NS
from .logging import log_error

def parse_xml_file(file_path: str) -> Optional[Element]:
    """Parse XML file and return root element."""
    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except ET.ParseError as e:
        log_error(f"Failed to parse XML: {e}")
        return None
    except Exception as e:
        log_error(f"Failed to read file: {e}")
        return None

def find_elements_any_ns(root: Element, tag: str) -> list:
    """Find elements with or without namespace."""
    # Try with namespace first
    found = root.findall(f'.//ep:{tag}', EPUBLISHER_NS)
    if not found:
        # Try without namespace
        found = list(root.iter(tag))
    return found
