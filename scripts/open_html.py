#!/usr/bin/env python3
"""Open a generated HTML file when a browser session is available."""

import argparse
import os
import sys
import webbrowser
from pathlib import Path


def browser_session_available() -> bool:
    if os.environ.get("BROWSER"):
        return True
    if sys.platform in {"darwin", "win32"}:
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="project-map.html")
    parser.add_argument(
        "--print-path",
        action="store_true",
        help="Only print the absolute file path.",
    )
    args = parser.parse_args()

    abs_path = Path(args.path).expanduser().resolve()
    if not abs_path.exists():
        print(f"File not found: {abs_path}", file=sys.stderr)
        return 1

    if args.print_path:
        print(abs_path)
        return 0

    url = abs_path.as_uri()
    if not browser_session_available():
        print(abs_path)
        print("No browser session detected; open the file manually.")
        return 0

    opened = webbrowser.open(url)
    if not opened:
        print(abs_path)
        print("Browser launch was unavailable; open the file manually.")
        return 0

    print(f"Opening {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
