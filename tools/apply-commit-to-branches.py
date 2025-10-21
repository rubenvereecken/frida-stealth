#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path
from typing import List


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


def commit_exists_in_branch(repo_dir: Path, branch: str, commit: str) -> bool:
    """Check if commit is already in the branch's history."""
    result = run_git_command(
        repo_dir, ["merge-base", "--is-ancestor", commit, branch], check=False
    )
    return result.returncode == 0


def cherry_pick_commit(repo_dir: Path, branch: str, commit: str) -> bool:
    """Cherry-pick commit onto branch. Returns True if applied, False if already exists."""
    # Checkout branch
    run_git_command(repo_dir, ["checkout", branch], check=True)

    # Check if commit already exists in branch
    if commit_exists_in_branch(repo_dir, branch, commit):
        return False

    # Cherry-pick
    result = run_git_command(repo_dir, ["cherry-pick", commit], check=False)

    if result.returncode != 0:
        # Check if it's an empty cherry-pick (commit already applied)
        if "empty" in result.stderr.lower():
            run_git_command(repo_dir, ["cherry-pick", "--abort"], check=False)
            return False

        # Real conflict - abort and raise
        run_git_command(repo_dir, ["cherry-pick", "--abort"], check=False)
        raise RuntimeError(
            f"Cherry-pick failed on branch {branch}\n"
            f"Commit: {commit}\n"
            f"Error: {result.stderr.strip()}"
        )

    return True


def apply_commit_to_all_branches(repo_dir: Path, repo_name: str, commit: str):
    print(f"\n{'='*60}")
    print(f"Applying commit to: {repo_name}")
    print(f"Commit: {commit}")
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
        print("  No stealth/* branches found")
        return

    print(f"\nFound {len(branches)} branches")
    print(f"Starting from: {original_branch}")
    print()

    applied_count = 0
    skipped_count = 0

    try:
        for i, branch in enumerate(branches, 1):
            print(f"  [{i}/{len(branches)}] {branch}...", end=" ", flush=True)
            was_applied = cherry_pick_commit(repo_dir, branch, commit)
            if was_applied:
                print("✓")
                applied_count += 1
            else:
                print("⊙ (already exists)")
                skipped_count += 1

        print(f"\n✓ Applied: {applied_count}, Skipped: {skipped_count}")

    finally:
        # Always restore original branch
        print(f"\nRestoring original branch: {original_branch}")
        run_git_command(repo_dir, ["checkout", original_branch], check=False)


def main():
    if len(sys.argv) < 3:
        print("Usage: apply-commit-to-branches.py <repo> <commit>")
        print()
        print("Repo options:")
        print("  frida-core")
        print("  frida-gum")
        print()
        print("Example:")
        print("  ./apply-commit-to-branches.py frida-core abc123def")
        sys.exit(1)

    repo_arg = sys.argv[1]
    commit = sys.argv[2]

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
        apply_commit_to_all_branches(repo_dir, repo_name, commit)
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
