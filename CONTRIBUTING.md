# Contributing to Frida Stealth

This document explains the repository structure, key concepts, and complete workflow for contributing stealth patches.

## Table of Contents

- [Repository Architecture](#repository-architecture)
- [Key Concepts](#key-concepts)
- [Helper Scripts](#helper-scripts)
- [Complete Development Workflow](#complete-development-workflow)
- [Adding New Upstream Versions](#adding-new-upstream-versions)
- [Troubleshooting](#troubleshooting)

## Repository Architecture

### Repository Structure

This project consists of three interconnected git repositories:

1. **Top-level `frida`** - Main repository that users clone
2. **`frida-core` submodule** - Core Frida functionality (where most stealth patches go)
3. **`frida-gum` submodule** - Low-level instrumentation engine

Each repository has its own set of `stealth/*` branches that correspond to Frida versions.

### Branch Structure

**Development branches:**

- `stealth/main` - Main development branch, tracks upstream Frida main
- This is where you make all new changes first

**Version branches:**

- `stealth/17.3.2`, `stealth/17.3.1`, `stealth/17.0.0`, etc.
- Each corresponds to an upstream Frida release tag
- All stealth patches are applied to these branches
- Users can checkout specific versions for compatibility

### Patch Storage

Patches are stored as `.patch` files in the submodule repositories:

- `subprojects/frida-core/patches/001-obfuscate-threads.patch`
- `subprojects/frida-gum/patches/002-example.patch`

**Naming convention:** `00X-short-description.patch`

Each patch is:

1. Generated from actual commits on the stealth branches
2. Committed to the repository with message: `generated patch 00X-description`
3. Tagged as: `stealth-patch/00X-description`

## Key Concepts

### 1. Code Changes vs Patch Files

- **Code changes**: The actual modifications (e.g., renaming "frida" to "banana" in thread names)
- **Patch files**: Unified diff format that can be applied to fresh upstream code

Both are stored in the repository:

- Code changes live as commits on `stealth/*` branches
- Patch files live in `patches/` directories

### 2. Submodule References

The top-level `frida` repository doesn't contain code from `frida-core` and `frida-gum` directly. Instead, it stores **commit pointers** that say "use this specific commit from frida-core."

When you update code in a submodule, you must also update the parent repository's pointer. This ensures users get the correct patched versions when cloning.

### 3. Multi-Version Support

Every change must be applied to **all** version branches (36+ branches). This allows users to use stealth Frida with any supported version.

The helper scripts automate this process.

## Helper Scripts

All scripts are in `tools/` and designed to be run from the top-level frida directory:

| Script                        | Purpose                                                    |
| ----------------------------- | ---------------------------------------------------------- |
| `create-version-branches.py`  | Create `stealth/X.Y.Z` branches for all versions >= 17.0.0 |
| `apply-commit-to-branches.py` | Cherry-pick a commit onto all version branches             |
| `generate-patch.py`           | Generate a `.patch` file from a commit                     |
| `commit-and-tag-patch.py`     | Commit and tag a generated patch file                      |
| `update-submodule-refs.py`    | Update parent repo's submodule pointers                    |

## Complete Development Workflow

This is the end-to-end process for adding a new stealth modification.

### Prerequisites

Ensure you're in the top-level frida directory and have all submodules initialized.

### Step 1: Make Your Changes

Work on the `stealth/main` branch of the relevant submodule:

```bash
cd subprojects/frida-core
git checkout stealth/main

# Make your changes
vim lib/agent/agent.vala

# Commit with a descriptive message
git add lib/agent/agent.vala
git commit -m "Obfuscate thread names to avoid detection"
```

Note the commit hash (e.g., `37ca12d8`).

### Step 2: Apply to All Version Branches

Use the helper script to cherry-pick your commit onto all `stealth/*` version branches:

```bash
cd /path/to/frida  # Top-level directory
./tools/apply-commit-to-branches.py frida-core 37ca12d8
```

This will:

- Iterate through all 36+ version branches
- Cherry-pick the commit onto each
- Stop immediately if conflicts occur (for manual resolution)
- Restore your original branch when done

**For frida-gum:**

```bash
./tools/apply-commit-to-branches.py frida-gum abc123
```

### Step 3: Generate Patch File

Create a unified `.patch` file from your commit:

```bash
./tools/generate-patch.py frida-core 37ca12d8 001-obfuscate-threads.patch
```

This will:

- Generate a diff from `commit~..commit`
- Verify the patch is identical across all version branches
- Save to `subprojects/frida-core/patches/001-obfuscate-threads.patch`
- Warn if any branch has different changes

**Patch naming:**

- Use sequential numbers: `001-`, `002-`, `003-`
- Keep descriptions short and hyphenated
- Always end with `.patch`

### Step 4: Commit and Tag the Patch

Commit the patch file to the repository and create a tag:

```bash
./tools/commit-and-tag-patch.py frida-core 001-obfuscate-threads.patch
```

This automatically:

- Adds `patches/001-obfuscate-threads.patch`
- Commits with message: `generated patch 001-obfuscate-threads`
- Tags as: `stealth-patch/001-obfuscate-threads`

Note the new commit hash (e.g., `80540048`).

### Step 5: Apply Patch Commit to All Branches

Apply the commit that _added the patch file_ to all version branches:

```bash
./tools/apply-commit-to-branches.py frida-core 80540048
```

This ensures every version branch has the `.patch` file in its `patches/` directory.

### Step 6: Update Submodule References

Update the top-level `frida` repository to point to the new submodule commits:

```bash
./tools/update-submodule-refs.py
```

This will:

- Go through each `stealth/*` branch in top-level frida
- Update the submodule pointers to the matching branch commits
- Commit changes with message: `update submodule refs for stealth/X.Y.Z`

### Step 7: Push Everything

Push all changes to your remote repositories:

**Push frida-core branches and tags:**

```bash
cd subprojects/frida-core

# Push all stealth branches (in order)
python3 -c "
import subprocess, re
result = subprocess.run(['git', 'branch', '--list', 'stealth/*'], capture_output=True, text=True)
branches = [line.strip().lstrip('* ') for line in result.stdout.strip().split('\n') if line.strip()]
version_branches = []
for branch in branches:
    match = re.match(r'stealth/(\d+)\.(\d+)\.(\d+)$', branch)
    if match:
        version_branches.append((int(match.group(1)), int(match.group(2)), int(match.group(3)), branch))
version_branches.sort()
for _, _, _, branch in version_branches:
    subprocess.run(['git', 'push', 'origin', branch])
subprocess.run(['git', 'push', 'origin', 'stealth/main'])
"

# Push only stealth-patch tags (not upstream version tags)
git push origin 'refs/tags/stealth-patch/*'
```

**Push frida-gum branches (if modified):**

```bash
cd subprojects/frida-gum
# Same push commands as frida-core
```

**Push top-level frida branches:**

```bash
cd /path/to/frida  # Top-level
# Same push commands
```

## Adding New Upstream Versions

When Frida releases a new version (e.g., `17.5.0`):

### 1. Fetch Upstream Tags

```bash
cd subprojects/frida-core
git fetch upstream --tags

cd subprojects/frida-gum
git fetch upstream --tags

cd ../..  # Back to top-level
git fetch upstream --tags
```

### 2. Create Version Branches

```bash
./tools/create-version-branches.py
```

This creates `stealth/17.5.0` branches in all three repositories.

### 3. Apply Existing Patches

For frida-core:

```bash
cd subprojects/frida-core
git checkout stealth/17.5.0

# Apply all existing patches
git apply patches/*.patch

# Commit
git add .
git commit -m "applied stealth patches to 17.5.0"
```

Repeat for frida-gum if it has patches.

### 4. Update Submodule References

```bash
cd /path/to/frida
./tools/update-submodule-refs.py
```

### 5. Test and Push

```bash
# Test build the new version
make

# Push everything (see Step 7 above)
```

## Workflow Summary Diagram

```
stealth/main (frida-core)
    ↓ (1. Make changes)
commit 37ca12d8
    ↓ (2. apply-commit-to-branches.py)
stealth/17.0.0...stealth/17.3.2 (35 branches)
    ↓ (3. generate-patch.py)
patches/001-name.patch
    ↓ (4. commit-and-tag-patch.py)
commit 80540048 [tag: stealth-patch/001-name]
    ↓ (5. apply-commit-to-branches.py)
patches/ on all branches
    ↓ (6. update-submodule-refs.py)
Top-level frida updated
    ↓ (7. Push)
GitHub ✓
```

## Troubleshooting

### Cherry-pick Conflicts

If `apply-commit-to-branches.py` fails with conflicts:

1. The script reports which branch failed (e.g., `stealth/17.2.3`)
2. Manually resolve:
   ```bash
   cd subprojects/frida-core
   git checkout stealth/17.2.3
   git cherry-pick <commit>
   # Resolve conflicts
   git cherry-pick --continue
   ```
3. Re-run the script - it skips already-applied branches

### Patch Doesn't Apply to All Versions

If `generate-patch.py` warns about different changes:

- Some file might not exist in older versions
- Code structure might be different

Options:

- Create version-specific patches: `001-name.17.2.1.patch`
- Document unsupported versions in patch comments
- Modify your changes to work across all versions

### Submodule Pointer Not Updated

If users report getting old code after cloning:

1. Check if `update-submodule-refs.py` was run
2. Verify top-level commit shows updated submodule:
   ```bash
   git diff HEAD~1 HEAD -- subprojects/frida-core
   ```
3. Should show: `-Subproject commit oldsha` / `+Subproject commit newsha`

### Wrong Branch Order on GitHub

If branches appear in the wrong order:

1. Delete remote branches:

   ```bash
   git branch -r | grep 'origin/stealth/[0-9]' | sed 's|origin/||' | xargs git push origin --delete
   ```

2. Re-push in order (see Step 7 above)

## Best Practices

1. **Always work on `stealth/main` first** - Never make changes directly on version branches
2. **Test before bulk-applying** - Test your changes on at least one version branch before applying to all 36+
3. **Keep patches focused** - One logical change per patch
4. **Document detection vectors** - Explain in commit messages what detection method the patch addresses
5. **Version compatibility** - Consider whether changes work across all supported versions
6. **Regular syncing** - Fetch upstream tags regularly to stay up-to-date with new releases

## Repository Remotes

### frida (top-level)

- `origin` - Your stealth fork: `https://github.com/yourname/frida-stealth.git`
- `upstream` - Official Frida: `https://github.com/frida/frida.git`

### frida-core

- `origin` - Your stealth fork: `https://github.com/yourname/frida-core-stealth.git`
- `upstream` - Official Frida: `https://github.com/frida/frida-core.git`

### frida-gum

- `origin` - Your stealth fork: `https://github.com/yourname/frida-gum-stealth.git`
- `upstream` - Official Frida: `https://github.com/frida/frida-gum.git`

## Questions?

Open an issue or discussion if you need help with the workflow.
