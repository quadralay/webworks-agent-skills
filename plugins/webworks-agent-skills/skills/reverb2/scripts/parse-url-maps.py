#!/usr/bin/env python3
"""
parse-url-maps.py

Parses url_maps.xml from Reverb output to extract Context Sensitive Help (CSH)
link mappings. Returns JSON with all CSH entries.

Usage:
    python parse-url-maps.py <url-maps-file> [format]

Arguments:
    url-maps-file - Path to url_maps.xml from Reverb output
    format        - Output format: json (default) or table

Output:
    JSON array of CSH mappings with topic_id, url, static_url, and title

Example url_maps.xml structure:
    <URLMaps>
        <TopicMap>
            <Topic topic="whats_new" path="Getting Started\\whats_new.html"
                   href="#context/whats_new" title="What's New" />
            <Topic topic="advanced" path="Advanced\\advanced.html"
                   href="#context/advanced" title="Advanced Features" />
        </TopicMap>
    </URLMaps>
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

DEBUG = os.environ.get('DEBUG', '0') == '1'


def debug_log(message: str) -> None:
    """Print debug message to stderr."""
    if DEBUG:
        print(f"{YELLOW}[DEBUG]{NC} {message}", file=sys.stderr)


def error_log(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def success_log(message: str) -> None:
    """Print success message to stderr."""
    print(f"{GREEN}[SUCCESS]{NC} {message}", file=sys.stderr)


def parse_url_maps(url_maps_file: str) -> list[dict]:
    """Parse url_maps.xml and extract CSH topic mappings."""
    debug_log(f"Parsing url_maps.xml: {url_maps_file}")

    # Check if file exists
    if not Path(url_maps_file).exists():
        error_log(f"url_maps.xml not found: {url_maps_file}")
        return []

    try:
        tree = ET.parse(url_maps_file)
        root = tree.getroot()
    except ET.ParseError as e:
        error_log(f"Failed to parse XML: {e}")
        return []
    except Exception as e:
        error_log(f"Failed to read file: {e}")
        return []

    # Handle namespace - Reverb uses this namespace in url_maps.xml
    ns = {'ww': 'urn:WebWorks-Reports-Schema'}

    # Find TopicMap element (with and without namespace)
    topic_map = root.find('.//ww:TopicMap', ns)
    if topic_map is None:
        topic_map = root.find('.//TopicMap')
    if topic_map is None:
        debug_log("No TopicMap section found in url_maps.xml")
        return []

    # Extract Topic elements (with and without namespace)
    topics = []
    topic_elements = topic_map.findall('ww:Topic', ns)
    if not topic_elements:
        topic_elements = topic_map.findall('Topic')
    for topic_elem in topic_elements:
        topic_id = topic_elem.get('topic', '')
        url = topic_elem.get('href', '')
        path = topic_elem.get('path', '')
        title = topic_elem.get('title', '')

        # Convert backslashes to forward slashes for web URLs
        static_url = path.replace('\\', '/')

        if topic_id and url and static_url:
            topics.append({
                'topic_id': topic_id,
                'url': url,
                'static_url': static_url,
                'title': title
            })

    count = len(topics)
    if count > 0:
        success_log(f"Found {count} CSH topics")
    else:
        debug_log("TopicMap is empty (no CSH links configured)")

    return topics


def format_as_table(topics: list[dict]) -> str:
    """Format topics as a human-readable table."""
    if not topics:
        return "No Context Sensitive Help links configured"

    lines = [
        "Context Sensitive Help Links:",
        "\u2501" * 95,
        f"{'Topic ID':<21} {'URL':<29} {'Static URL (no javascript)':<30} Title",
        "\u2500" * 95
    ]

    for topic in topics:
        lines.append(
            f"{topic['topic_id']:<21} {topic['url']:<29} {topic['static_url']:<30} {topic['title']}"
        )

    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Parse url_maps.xml from Reverb output to extract CSH link mappings.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Output CSH links as JSON (default)
    %(prog)s output/url_maps.xml

    # Output CSH links as table
    %(prog)s output/url_maps.xml table
"""
    )

    parser.add_argument('url_maps_file', metavar='url-maps-file',
                        help='Path to url_maps.xml from Reverb output')
    parser.add_argument('format', nargs='?', default='json',
                        choices=['json', 'table'],
                        help='Output format: json (default) or table')

    args = parser.parse_args()

    # Parse url_maps.xml
    topics = parse_url_maps(args.url_maps_file)

    # Output based on format
    if args.format == 'json':
        print(json.dumps(topics, indent=2))
    elif args.format == 'table':
        print(format_as_table(topics))

    return 0


if __name__ == '__main__':
    sys.exit(main())
