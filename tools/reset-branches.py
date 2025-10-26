#!/usr/bin/env python3

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


def parse_version(branch_name: str) -> Tuple[int, int, int] | None:
    """Extract version from branch name like stealth/17.3.2."""
    match = re.match(r"stealth/(\d+)\.(\d+)\.(\d+)$", branch_name)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def reset_branch(repo_dir: Path, branch: str, base_tag: str):
    """Reset a branch to its base tag."""
    print(f"  {branch}...", end=" ", flush=True)

    # Checkout branch
    run_git_command(repo_dir, ["checkout", branch], check=True)

    # Reset to base tag
    result = run_git_command(repo_dir, ["reset", "--hard", base_tag], check=False)
    if result.returncode != 0:
        print(f"✗ (tag {base_tag} not found)")
        return False

    print(f"✓ reset to {base_tag}")
    return True


def reset_all_branches(repo_dir: Path, repo_name: str, dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"Resetting branches: {repo_name}")
    print(f"{'='*60}")

    if not repo_dir.exists():
        raise RuntimeError(f"Repository not found: {repo_dir}")

    if not (repo_dir / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_dir}")

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
                print(f"  Would reset: {branch} → {tag}")
        return

    print(f"\n⚠️  WARNING: This will HARD RESET {len(version_branches)} branches!")
    print("   All stealth commits will be REMOVED.")
    print()
    response = input("Continue? [yes/NO]: ")
    if response.lower() != "yes":
        print("Aborted.")
        return

    success_count = 0
    fail_count = 0

    try:
        print()
        for branch in version_branches:
            version = parse_version(branch)
            if not version:
                continue

            tag = f"{version[0]}.{version[1]}.{version[2]}"
            if reset_branch(repo_dir, branch, tag):
                success_count += 1
            else:
                fail_count += 1

        print(f"\n✓ Success: {success_count}, Failed: {fail_count}")

        if fail_count == 0:
            print("\n⚠️  Branches reset locally. Push with:")
            print(f"   git push origin 'stealth/*' --force")

    finally:
        # Always restore original branch
        print(f"\nRestoring original branch: {original_branch}")
        run_git_command(repo_dir, ["checkout", original_branch], check=False)


def main():
    dry_run = "--dry-run" in sys.argv

    if len(sys.argv) < 2 or (len(sys.argv) == 2 and dry_run):
        print("Usage: reset-branches.py <repo> [--dry-run]")
        print()
        print("Repo options:")
        print("  frida-core")
        print("  frida-gum")
        print()
        print("Example:")
        print("  ./reset-branches.py frida-gum --dry-run  # Preview")
        print("  ./reset-branches.py frida-gum            # Execute")
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
        reset_all_branches(repo_dir, repo_name, dry_run=dry_run)
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
