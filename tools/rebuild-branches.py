#!/usr/bin/env python3
"""
Rebuild all stealth version branches by applying commits from stealth/main.

This script takes all commits that exist on stealth/main but not on upstream/main,
and applies them cleanly to each stealth/X.Y.Z version branch. Each version branch
is reset to its corresponding upstream tag (X.Y.Z) and then the stealth commits
are cherry-picked onto it.

Usage:
    ./rebuild-branches.py frida-core           # Rebuild frida-core branches
    ./rebuild-branches.py frida-gum            # Rebuild frida-gum branches
    ./rebuild-branches.py frida-core --dry-run # Preview without making changes

This is useful after:
- Adding new stealth commits to stealth/main
- Modifying existing stealth commits (via amend/rebase)
- Creating new version branches

Note: This will FORCE RESET all version branches. Use --dry-run first to preview.
"""

import subprocess
import sys
import re
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


def get_stealth_branches(repo_dir: Path) -> List[str]:
    """Get all stealth/* branches sorted by version."""
    result = run_git_command(repo_dir, ["branch", "--list", "stealth/*"], check=True)
    branches = [
        line.strip().lstrip("* ")
        for line in result.stdout.strip().split("\n")
        if line.strip()
    ]
    return sorted(branches)


def get_stealth_commits(repo_dir: Path) -> List[str]:
    """Get commits on stealth/main that aren't on upstream/main."""
    result = run_git_command(
        repo_dir,
        ["log", "--reverse", "--format=%H", "stealth/main", "--not", "upstream/main"],
        check=True,
    )
    commits = [
        line.strip() for line in result.stdout.strip().split("\n") if line.strip()
    ]
    return commits


def parse_version(branch_name: str) -> Tuple[int, int, int] | None:
    """Extract version from branch name like stealth/17.3.2."""
    match = re.match(r"stealth/(\d+)\.(\d+)\.(\d+)$", branch_name)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def rebuild_branch(repo_dir: Path, branch: str, base_tag: str, commits: List[str]):
    """Rebuild a branch by resetting to base and applying commits."""
    print(f"  {branch}...", end=" ", flush=True)

    # Checkout branch
    run_git_command(repo_dir, ["checkout", branch], check=True)

    # Reset to base tag
    result = run_git_command(repo_dir, ["reset", "--hard", base_tag], check=False)
    if result.returncode != 0:
        print(f"✗ (tag {base_tag} not found)")
        return False

    # Apply commits
    applied = 0
    for commit in commits:
        result = run_git_command(repo_dir, ["cherry-pick", commit], check=False)
        if result.returncode != 0:
            # Check if empty (already applied)
            if "empty" in result.stderr.lower():
                run_git_command(repo_dir, ["cherry-pick", "--skip"], check=False)
                continue

            # Check for modify/delete conflict (e.g., README removal)
            if "modify/delete" in result.stderr or "CONFLICT" in result.stderr:
                # Try to auto-resolve by accepting changes from cherry-picked commit
                # Get list of conflicted files
                status_result = run_git_command(
                    repo_dir, ["status", "--porcelain"], check=False
                )
                resolved = True
                for line in status_result.stdout.split("\n"):
                    if line.startswith(
                        "DU "
                    ):  # Deleted by us, Updated by them - keep deletion
                        file = line[3:].strip()
                        run_git_command(repo_dir, ["rm", file], check=False)
                    elif line.startswith(
                        "UD "
                    ):  # Updated by us, Deleted by them - keep deletion
                        file = line[3:].strip()
                        run_git_command(repo_dir, ["rm", file], check=False)
                    elif line.startswith("AU ") or line.startswith(
                        "UA "
                    ):  # Addition conflict - keep addition
                        file = line[3:].strip()
                        run_git_command(repo_dir, ["add", file], check=False)
                    elif line.startswith("AA ") or line.startswith(
                        "UU "
                    ):  # Both added/modified - can't auto-resolve
                        resolved = False
                        break

                if resolved:
                    result = run_git_command(
                        repo_dir,
                        ["cherry-pick", "--continue"],
                        check=False,
                        capture_output=False,
                    )
                    if result.returncode == 0:
                        applied += 1
                        continue

            # Real conflict we can't auto-resolve
            run_git_command(repo_dir, ["cherry-pick", "--abort"], check=False)
            print(f"✗ (conflict at {commit[:8]})")
            return False
        applied += 1

    print(f"✓ ({applied} commits)")
    return True


def rebuild_all_branches(repo_dir: Path, repo_name: str, dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"Rebuilding branches: {repo_name}")
    print(f"{'='*60}")

    if not repo_dir.exists():
        raise RuntimeError(f"Repository not found: {repo_dir}")

    if not (repo_dir / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_dir}")

    # Get stealth commits to apply
    stealth_commits = get_stealth_commits(repo_dir)
    if not stealth_commits:
        print("\n  No stealth commits found on stealth/main")
        return

    print(f"\nStealth commits to apply: {len(stealth_commits)}")
    for commit in stealth_commits:
        result = run_git_command(
            repo_dir, ["log", "--format=%s", "-n1", commit], check=True
        )
        print(f"  - {commit[:8]} {result.stdout.strip()}")

    # Get current branch to restore later
    result = run_git_command(
        repo_dir, ["rev-parse", "--abbrev-ref", "HEAD"], check=True
    )
    original_branch = result.stdout.strip()

    branches = get_stealth_branches(repo_dir)
    if not branches:
        print("\n  No stealth/* branches found")
        return

    # Filter out stealth/main and stealth/init
    version_branches = [b for b in branches if parse_version(b) is not None]

    if not version_branches:
        print("\n  No version branches found")
        return

    print(f"\nFound {len(version_branches)} version branches")

    if dry_run:
        print("\n🔍 DRY RUN - No changes will be made\n")
        for branch in version_branches:
            version = parse_version(branch)
            if version:
                tag = f"{version[0]}.{version[1]}.{version[2]}"
                print(f"  Would rebuild: {branch} (base: {tag})")
        return

    print(f"\n⚠️  Rebuilding {len(version_branches)} branches (FORCE RESET)\n")

    success_count = 0
    fail_count = 0

    try:
        for branch in version_branches:
            version = parse_version(branch)
            if not version:
                continue

            tag = f"{version[0]}.{version[1]}.{version[2]}"
            if rebuild_branch(repo_dir, branch, tag, stealth_commits):
                success_count += 1
            else:
                fail_count += 1

        print(f"\n✓ Success: {success_count}, Failed: {fail_count}")

        if fail_count == 0:
            print("\n⚠️  Branches rebuilt locally. Push with:")
            print(f"   cd subprojects/{repo_name}")
            print(f"   git push origin stealth/main")
            print(f"   git branch --list 'stealth/*' | grep -E 'stealth/[0-9]' | xargs -n1 git push origin")

    finally:
        # Always restore original branch
        print(f"\nRestoring original branch: {original_branch}")
        run_git_command(repo_dir, ["checkout", original_branch], check=False)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    dry_run = "--dry-run" in sys.argv

    if len(sys.argv) < 2 or (len(sys.argv) == 2 and dry_run):
        print("Usage: rebuild-branches.py <repo> [--dry-run]")
        print()
        print(
            "Rebuilds all stealth version branches by applying commits from stealth/main."
        )
        print()
        print("Repo options:")
        print("  frida-core")
        print("  frida-gum")
        print()
        print("Examples:")
        print("  ./rebuild-branches.py frida-core --dry-run  # Preview changes")
        print("  ./rebuild-branches.py frida-core            # Execute rebuild")
        print()
        print("Use --help for detailed documentation.")
        sys.exit(1)

    repo_arg = sys.argv[1]

    script_dir = Path(__file__).parent
    frida_root = script_dir.parent

    repos = {
        "frida-core": (frida_root / "subprojects" / "frida-core", "frida-core"),
        "frida-gum": (frida_root / "subprojects" / "frida-gum", "frida-gum"),
    }

    if repo_arg not in repos:
        print(f"Error: Unknown repo '{repo_arg}'", file=sys.stderr)
        print(f"Available: {', '.join(repos.keys())}", file=sys.stderr)
        sys.exit(1)

    repo_dir, repo_name = repos[repo_arg]

    try:
        rebuild_all_branches(repo_dir, repo_name, dry_run=dry_run)
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
