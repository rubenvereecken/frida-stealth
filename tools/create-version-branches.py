#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_git_command(
    repo_dir: Path, args: List[str], capture_output: bool = True, check: bool = False
) -> subprocess.CompletedProcess:
    """If check=True, raises RuntimeError on non-zero exit code."""
    cmd = ["git", "-C", str(repo_dir)] + args
    result = subprocess.run(cmd, capture_output=capture_output, text=True, check=False)

    if check and result.returncode != 0:
        error_msg = (
            result.stderr.strip() if result.stderr else f"Exit code {result.returncode}"
        )
        raise RuntimeError(f"Git command failed: {' '.join(args)}\n{error_msg}")

    return result


def get_tags(repo_dir: Path) -> List[str]:
    result = run_git_command(repo_dir, ["tag"], check=True)
    if not result.stdout.strip():
        return []
    return [tag.strip() for tag in result.stdout.strip().split("\n") if tag.strip()]


def parse_version(tag: str) -> Tuple[int, int, int] | None:
    """Returns None if not valid semver."""
    parts = tag.split(".")
    if len(parts) != 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def branch_exists(repo_dir: Path, branch_name: str) -> bool:
    result = run_git_command(
        repo_dir, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"]
    )
    return result.returncode == 0


def create_branch(repo_dir: Path, branch_name: str, tag: str) -> None:
    run_git_command(repo_dir, ["branch", branch_name, tag], check=True)


def fetch_upstream_tags(repo_dir: Path) -> None:
    run_git_command(
        repo_dir, ["fetch", "upstream", "--tags"], capture_output=False, check=True
    )


def process_repository(repo_dir: Path, repo_name: str, min_major_version: int = 17):
    print(f"\n{'='*60}")
    print(f"Processing: {repo_name}")
    print(f"{'='*60}")

    if not repo_dir.exists():
        raise RuntimeError(f"Repository not found: {repo_dir}")

    if not (repo_dir / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_dir}")

    # Check if upstream remote exists
    result = run_git_command(repo_dir, ["remote", "get-url", "upstream"])
    if result.returncode == 0:
        print(f"Fetching tags from upstream...")
        fetch_upstream_tags(repo_dir)
    else:
        print(f"No upstream remote found, using local tags")

    print(f"\nCreating branches for tags >= {min_major_version}.0.0...")

    tags = get_tags(repo_dir)
    if not tags:
        print(f"  No tags found in repository")
        return

    version_tags = []

    for tag in tags:
        version = parse_version(tag)
        if version and version[0] >= min_major_version:
            version_tags.append((tag, version))

    if not version_tags:
        print(f"  No tags >= {min_major_version}.0.0 found")
        return

    # Sort by version
    version_tags.sort(key=lambda x: x[1])

    created_count = 0
    skipped_count = 0

    for tag, version in version_tags:
        branch_name = f"stealth/{tag}"

        if branch_exists(repo_dir, branch_name):
            print(f"  ✓ {branch_name:30} (already exists)")
            skipped_count += 1
        else:
            create_branch(repo_dir, branch_name, tag)
            print(f"  → {branch_name:30} (created)")
            created_count += 1

    print(f"\nSummary: {created_count} created, {skipped_count} skipped")


def main():
    script_dir = Path(__file__).parent
    frida_root = script_dir.parent

    repositories = [
        (frida_root, "frida (main)"),
        (frida_root / "subprojects" / "frida-core", "frida-core"),
        (frida_root / "subprojects" / "frida-gum", "frida-gum"),
    ]

    print("Creating version branches for Frida repositories")
    print(f"Minimum version: 17.0.0")

    try:
        for repo_dir, repo_name in repositories:
            process_repository(repo_dir, repo_name)

        print(f"\n{'='*60}")
        print("Done!")
        print(f"{'='*60}")
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
