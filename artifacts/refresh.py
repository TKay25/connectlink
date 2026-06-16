#!/usr/bin/env python3
"""
Artifacto refresh launcher — for automated pipelines and CI.

Usage:
    python artifacts/refresh.py           # refresh changed files only
    python artifacts/refresh.py --all     # force-refresh all modules

This script finds the bundled Artifacto extractor and runs it against
the workspace. No human interaction required — safe for CI/CD pipelines,
pre-commit hooks, or AI agent auto-refresh workflows.
"""
import subprocess, sys, os, glob, argparse, json


def find_extractor() -> str:
    """Locate extract_artifacts.py in the installed Artifacto extension."""
    home = os.path.expanduser("~")
    # Cursor and VSCode extension cache locations (Windows / macOS / Linux)
    patterns = [
        os.path.join(home, ".cursor", "extensions", "*artifacto*", "scripts", "extract_artifacts.py"),
        os.path.join(home, ".vscode", "extensions", "*artifacto*", "scripts", "extract_artifacts.py"),
        os.path.join(home, "AppData", "Local", "Programs", "cursor", "resources", "app",
                     "extensions", "*artifacto*", "scripts", "extract_artifacts.py"),
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]  # latest installed version

    # Fallback: maybe the extractor is bundled locally alongside this file
    local = os.path.join(os.path.dirname(__file__), "..", "scripts", "extract_artifacts.py")
    if os.path.exists(local):
        return os.path.abspath(local)

    return ""


def _get_unprocessed_files(changes_path: str) -> list:
    """Read .changes.jsonl and return paths of files not yet processed."""
    if not os.path.exists(changes_path):
        return []
    files = []
    seen: set = set()
    try:
        with open(changes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if not entry.get("processed", True):
                        fp = entry.get("file", "")
                        if fp and fp not in seen and os.path.exists(fp):
                            files.append(fp)
                            seen.add(fp)
                except Exception:
                    pass
    except Exception:
        pass
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Artifacto refresh launcher")
    parser.add_argument("--all", action="store_true", help="Force-refresh all modules, not just changed ones")
    args = parser.parse_args()

    extractor = find_extractor()
    if not extractor:
        print("ERROR: Artifacto extractor not found. Is the Artifacto extension installed?", file=sys.stderr)
        return 1

    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [sys.executable, extractor, "--dir", workspace]

    if args.all:
        cmd.append("--all")
    else:
        changes_path = os.path.join(workspace, "artifacts", ".changes.jsonl")
        unprocessed = _get_unprocessed_files(changes_path)
        if not unprocessed:
            print("Artifacto: no changed files to refresh.")
            return 0
        queue_file = os.path.join(workspace, "artifacts", ".refresh_queue.txt")
        with open(queue_file, "w", encoding="utf-8") as f:
            f.write("\n".join(unprocessed))
        cmd.extend(["--file-list", queue_file])

    print(f"Artifacto: refreshing artifacts in {workspace}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("Artifacto: refresh complete.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
