#!/usr/bin/env python3
"""Pre-push guard: warns and blocks if any Softspaceg shared-library git pin in
this repo is behind the latest tag on GitHub, so an update never gets forgotten."""

import re
import subprocess
import sys
from pathlib import Path

PIN_PATTERN = re.compile(
    r"git\+https://github\.com/(Softspaceg/[\w.-]+?)\.git@v(\d+)\.(\d+)\.(\d+)"
)
TAG_PATTERN = re.compile(r"refs/tags/v(\d+)\.(\d+)\.(\d+)$")


def find_pins():
    """Yield (file_name, repo_path, pinned_version) for every Softspaceg pin found."""
    seen = set()
    for name in ("requirements.txt", "pyproject.toml"):
        path = Path(name)
        if not path.exists():
            continue
        for match in PIN_PATTERN.finditer(path.read_text()):
            repo_path = match.group(1)
            version = tuple(int(match.group(i)) for i in (2, 3, 4))
            if repo_path in seen:
                continue
            seen.add(repo_path)
            yield name, repo_path, version


def latest_tag(repo_path):
    url = f"https://github.com/{repo_path}.git"
    try:
        output = subprocess.run(
            ["git", "ls-remote", "--tags", url],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    versions = [
        tuple(int(p) for p in m.groups())
        for m in map(TAG_PATTERN.search, output.splitlines())
        if m
    ]
    return max(versions) if versions else None


def main() -> int:
    pins = list(find_pins())
    if not pins:
        return 0

    stale = []
    for file_name, repo_path, pinned in pins:
        latest = latest_tag(repo_path)
        if latest is None:
            msg = f"version check: couldn't reach GitHub for {repo_path}, skipping"
            print(msg, file=sys.stderr)
            continue
        if pinned < latest:
            stale.append((file_name, repo_path, pinned, latest))

    if not stale:
        return 0

    for file_name, repo_path, pinned, latest in stale:
        pinned_str = ".".join(map(str, pinned))
        latest_str = ".".join(map(str, latest))
        print(
            f"\nWARNING: {file_name} pins {repo_path} to v{pinned_str}, but "
            f"v{latest_str} is available.\n"
            f"  https://github.com/{repo_path}/releases",
            file=sys.stderr,
        )
    print(
        "\nUpdate the pin(s) before pushing, or `git push --no-verify` to push anyway.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
