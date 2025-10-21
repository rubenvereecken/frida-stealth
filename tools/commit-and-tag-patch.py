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


def commit_and_tag_patch(repo_dir: Path, repo_name: str, patch_name: str):
    print(f"\n{'='*60}")
    print(f"Committing and tagging patch: {repo_name}")
    print(f"Patch: {patch_name}")
    print(f"{'='*60}\n")

    if not repo_dir.exists():
        raise RuntimeError(f"Repository not found: {repo_dir}")

    if not (repo_dir / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_dir}")

    # Verify patch file exists
    patch_file = repo_dir / "patches" / patch_name
    if not patch_file.exists():
        raise RuntimeError(f"Patch file not found: {patch_file}")

    # Extract patch ID (e.g., "001-obfuscate-threads" from "001-obfuscate-threads.patch")
    patch_id = patch_name.replace(".patch", "")

    # Add patch file
    print(f"Adding {patch_file.relative_to(repo_dir)}...")
    run_git_command(repo_dir, ["add", f"patches/{patch_name}"], check=True)

    # Commit with formulaic message
    commit_msg = f"generated patch {patch_id}"
    print(f"Committing: {commit_msg}")
    run_git_command(repo_dir, ["commit", "-m", commit_msg], check=True)

    # Create tag
    tag_name = f"stealth-patch/{patch_id}"
    print(f"Tagging: {tag_name}")
    run_git_command(repo_dir, ["tag", tag_name], check=True)

    print(f"\n✓ Patch committed and tagged successfully")


def main():
    if len(sys.argv) < 3:
        print("Usage: commit-and-tag-patch.py <repo> <patch-name>")
        print()
        print("Repo options:")
        print("  frida-core")
        print("  frida-gum")
        print()
        print("Example:")
        print("  ./commit-and-tag-patch.py frida-core 001-obfuscate-threads.patch")
        sys.exit(1)

    repo_arg = sys.argv[1]
    patch_name = sys.argv[2]

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
        commit_and_tag_patch(repo_dir, repo_name, patch_name)
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
