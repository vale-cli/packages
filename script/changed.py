#!/usr/bin/env python3
"""Print the packages a change actually needs to re-check.

Usage: changed.py <base library.json> <head library.json>

Only entries that are new, or whose `url` now points somewhere else, are
printed. A description or logo edit does not change what gets downloaded, and
re-running every package for one of those means executing sixteen third-party
archives to check a typo.
"""

import json
import sys


def load(path):
    """Read a library, tolerating a base revision that has none yet."""
    try:
        with open(path) as f:
            return {e["name"]: e for e in json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def changed(base, head):
    """Return the names whose downloadable content may differ."""
    out = []
    for name, entry in head.items():
        before = base.get(name)
        if before is None or before.get("url") != entry.get("url"):
            out.append(name)
    return sorted(out)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)

    for name in changed(load(sys.argv[1]), load(sys.argv[2])):
        print(name)


if __name__ == "__main__":
    main()
