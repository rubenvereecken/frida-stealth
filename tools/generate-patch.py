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


def generate_patch_from_commit(
    repo_dir: Path, branch: str, commit: str, output_file: Path
) -> bool:
    """Generate patch from commit~..commit on branch. Returns True if patch has content."""
    # Checkout branch
    run_git_command(repo_dir, ["checkout", branch], check=True)

    # Generate diff for just this commit
    result = run_git_command(repo_dir, ["diff", f"{commit}~", commit], check=True)

    if not result.stdout.strip():
        return False

    # Write patch
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(result.stdout)
    return True


def generate_patch_for_repo(
    repo_dir: Path, repo_name: str, commit: str, patch_name: str
):
    print(f"\n{'='*60}")
    print(f"Generating patch for: {repo_name}")
    print(f"Commit: {commit}")
    print(f"Patch name: {patch_name}")
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

    patches_dir = repo_dir / "patches"
    output_file = patches_dir / patch_name

    branches = get_stealth_branches(repo_dir)
    if not branches:
        print("  No stealth/* branches found")
        return

    print(f"\nFound {len(branches)} branches")
    print(f"Starting from: {original_branch}")
    print()

    try:
        # Generate patch from first branch
        first_branch = branches[0]
        print(f"Generating from {first_branch}...")
        if not generate_patch_from_commit(repo_dir, first_branch, commit, output_file):
            print(f"  No changes found in commit")
            return

        base_patch = output_file.read_text()

        # Verify patch is identical across all branches
        print(f"Verifying patch applies to all branches...")
        applies_count = 1

        for branch in branches[1:]:
            run_git_command(repo_dir, ["checkout", branch], check=True)
            result = run_git_command(
                repo_dir, ["diff", f"{commit}~", commit], check=True
            )

            if result.stdout.strip():
                if result.stdout == base_patch:
                    applies_count += 1
                else:
                    print(f"  ⚠️  Branch {branch} has different changes!")
                    temp_output = output_file.with_suffix(
                        f".{branch.replace('stealth/', '')}.patch"
                    )
                    temp_output.write_text(result.stdout)
                    print(f"     Saved to: {temp_output.name}")

        print(f"\n✓ Patch applies to {applies_count}/{len(branches)} branches")
        print(f"✓ Saved to: {output_file.relative_to(repo_dir.parent.parent)}")

    finally:
        # Always restore original branch
        print(f"\nRestoring original branch: {original_branch}")
        run_git_command(repo_dir, ["checkout", original_branch], check=False)


def main():
    if len(sys.argv) < 4:
        print("Usage: generate-patch.py <repo> <commit> <patch-name>")
        print()
        print("Repo options:")
        print("  frida-core")
        print("  frida-gum")
        print()
        print("Patch name format: 00x-description.patch")
        print()
        print("Example:")
        print("  ./generate-patch.py frida-core abc123def 001-obfuscate-threads.patch")
        sys.exit(1)

    repo_arg = sys.argv[1]
    commit = sys.argv[2]
    patch_name = sys.argv[3]

    if not patch_name.endswith(".patch"):
        print("Error: patch name must end with .patch", file=sys.stderr)
        sys.exit(1)

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
        generate_patch_for_repo(repo_dir, repo_name, commit, patch_name)
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
