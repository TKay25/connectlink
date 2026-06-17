#!/usr/bin/env python3
"""
Artifacto search launcher — find which files to read (no LLM, no repo-wide grep).

Usage:
    python artifacts/search.py boss level
    python artifacts/search.py --path data/levels/L042.json
    python artifacts/search.py --letter L
    python artifacts/search.py --kind code

Run this BEFORE opening many JSON/data files. Use only paths listed under READ.
"""
import subprocess, sys, os, glob


def find_search_script() -> str:
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(home, ".cursor", "extensions", "*artifacto*", "scripts", "search_catalog.py"),
        os.path.join(home, ".vscode", "extensions", "*artifacto*", "scripts", "search_catalog.py"),
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    local = os.path.join(os.path.dirname(__file__), "..", "scripts", "search_catalog.py")
    if os.path.exists(local):
        return os.path.abspath(local)
    return ""


def main() -> int:
    script = find_search_script()
    if not script:
        print("ERROR: search_catalog.py not found.", file=sys.stderr)
        return 1
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [sys.executable, script, "--dir", workspace] + sys.argv[1:]
    return subprocess.run(cmd, cwd=workspace).returncode


if __name__ == "__main__":
    sys.exit(main())
