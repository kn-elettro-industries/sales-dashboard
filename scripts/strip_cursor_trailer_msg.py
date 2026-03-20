#!/usr/bin/env python3
"""Used by git filter-branch --msg-filter: drop 'Made-with: Cursor' lines from commit messages."""
import sys


def main() -> None:
    data = sys.stdin.read()
    lines = [ln for ln in data.splitlines() if ln.strip() != "Made-with: Cursor"]
    out = "\n".join(lines)
    if data.endswith("\n"):
        out = out + "\n" if out else "\n"
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
