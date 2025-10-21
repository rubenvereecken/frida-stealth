#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


def run_git_command(
    repo_dir: Path, args: list[str], capture_output: bool = True, check: bool = False
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


def get_stealth_branches(repo_dir: Path) -> list[str]:
    """Get all stealth/* branches sorted."""
    result = run_git_command(repo_dir, ["branch", "--list", "stealth/*"], check=True)
    branches = [
        line.strip().lstrip("* ")
        for line in result.stdout.strip().split("\n")
        if line.strip()
    ]
    return sorted(branches)


def branch_exists(repo_dir: Path, branch: str) -> bool:
    """Check if branch exists in repository."""
    result = run_git_command(
        repo_dir, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]
    )
    return result.returncode == 0


def update_submodules_for_branch(frida_root: Path, branch: str) -> bool:
    """Update submodule refs for a specific branch. Returns True if changes were made."""
    print(f"  Processing {branch}...", end=" ", flush=True)

    # Checkout the branch in top-level frida
    run_git_command(frida_root, ["checkout", branch], check=True)

    # Update submodules to their corresponding branch
    submodules = ["subprojects/frida-core", "subprojects/frida-gum"]
    changes_made = False

    for submodule in submodules:
        submodule_path = frida_root / submodule

        # Check if branch exists in submodule
        if not branch_exists(submodule_path, branch):
            continue

        # Checkout the branch in submodule
        result = run_git_command(submodule_path, ["checkout", branch], check=False)
        if result.returncode != 0:
            continue

        # Get the new commit hash
        result = run_git_command(submodule_path, ["rev-parse", "HEAD"], check=True)
        new_commit = result.stdout.strip()

        # Stage the submodule update
        run_git_command(frida_root, ["add", submodule], check=True)
        changes_made = True

    # Check if there are changes to commit
    result = run_git_command(frida_root, ["diff", "--cached", "--quiet"], check=False)
    if result.returncode == 0:
        # No changes
        print("⊙ (no changes)")
        return False

    # Commit the submodule updates
    run_git_command(
        frida_root, ["commit", "-m", f"update submodule refs for {branch}"], check=True
    )
    print("✓")
    return True


def main():
    script_dir = Path(__file__).parent
    frida_root = script_dir.parent

    print(f"\n{'='*60}")
    print("Updating submodule references in top-level frida")
    print(f"{'='*60}\n")

    if not frida_root.exists():
        raise RuntimeError(f"Frida root not found: {frida_root}")

    if not (frida_root / ".git").exists():
        raise RuntimeError(f"Not a git repository: {frida_root}")

    # Get current branch to restore later
    result = run_git_command(
        frida_root, ["rev-parse", "--abbrev-ref", "HEAD"], check=True
    )
    original_branch = result.stdout.strip()

    branches = get_stealth_branches(frida_root)
    if not branches:
        print("  No stealth/* branches found")
        return

    print(f"Found {len(branches)} branches")
    print(f"Starting from: {original_branch}\n")

    updated_count = 0
    skipped_count = 0

    try:
        for branch in branches:
            if update_submodules_for_branch(frida_root, branch):
                updated_count += 1
            else:
                skipped_count += 1

        print(f"\n✓ Updated: {updated_count}, Skipped: {skipped_count}")

    finally:
        # Always restore original branch
        print(f"\nRestoring original branch: {original_branch}")
        run_git_command(frida_root, ["checkout", original_branch], check=False)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)
