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
| `rebuild-branches.py`         | Rebuild all version branches from stealth/main commits     |
| `update-submodule-refs.py`    | Update parent repo's submodule pointers                    |
| `generate-patch.py`           | Generate a `.patch` file from a commit (manual use)        |

## Complete Development Workflow

This is the streamlined process for adding a new stealth modification.

### Step 1: Make Your Changes on stealth/main

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

**For frida-gum:** Same process in `subprojects/frida-gum`

### Step 2: Generate Patch File and Update README

In a **separate commit**, generate the patch file and update the patches README:

```bash
# Generate patch from your previous commit
git format-patch -1 HEAD --stdout > patches/002-obfuscate-rpc.patch

# Update patches/README.md to add a row for your new patch
vim patches/README.md

# Commit both together
git add patches/002-obfuscate-rpc.patch patches/README.md
git commit -m "Add patch 002: RPC protocol obfuscation"
```

**Why separate commits?**
- First commit: Your actual code changes (clean, reviewable)
- Second commit: Generated artifacts (patch file + documentation)

### Step 3: Rebuild All Version Branches

From the top-level frida directory, rebuild all version branches with your new commits:

```bash
cd /path/to/frida  # Top-level directory
./tools/rebuild-branches.py frida-core
```

This automatically:
- Resets each version branch to its upstream tag
- Cherry-picks all commits from stealth/main
- Handles all 35+ branches in one command

**For frida-gum:**
```bash
./tools/rebuild-branches.py frida-gum
```

### Step 4: Update Submodule References

Update the top-level repository to point to the new submodule commits:

```bash
./tools/update-submodule-refs.py
```

This updates all parent branches to reference the correct submodule commits.

### Step 5: Push Everything

**Push frida-core:**

```bash
cd subprojects/frida-core
git push origin stealth/main
git branch --list 'stealth/*' | grep -E 'stealth/[0-9]' | xargs -n1 git push origin
```

**Push frida-gum (if modified):**

```bash
cd subprojects/frida-gum
git push origin stealth/main
git branch --list 'stealth/*' | grep -E 'stealth/[0-9]' | xargs -n1 git push origin
```

**Push top-level frida:**

```bash
cd /path/to/frida  # Top-level
git push origin stealth/main
git branch --list 'stealth/*' | grep -E 'stealth/[0-9]' | xargs -n1 git push origin
```

**Note:** Force push should only be needed if you've rewritten history (amended commits, rebased, etc.). Normal workflow just adds new commits on top.

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
    ↓ (1. Make code changes)
commit 6b8eadb6 "Obfuscate RPC protocol identifiers"
    ↓ (2. Generate patch + update README)
commit 7376e04f "Add patch 002"
    ↓ (3. rebuild-branches.py frida-core)
stealth/17.0.0...stealth/17.3.2 (all 35 branches updated)
    ↓ (4. update-submodule-refs.py)
Top-level frida updated (all 36 branches)
    ↓ (5. Push frida-core + parent)
GitHub ✓
```

## Troubleshooting

### Rebuild Conflicts

If `rebuild-branches.py` fails with conflicts on a specific version:

1. The script reports which branch failed (e.g., `stealth/17.2.3`)
2. Manually resolve:
   ```bash
   cd subprojects/frida-core
   git checkout stealth/17.2.3
   git cherry-pick <commit-hash>
   # Resolve conflicts
   git cherry-pick --continue
   ```
3. Continue with remaining steps manually

### Changes Don't Work on Older Versions

If your changes break on older Frida versions:

- Some files/APIs might not exist in older versions
- Code structure might be different

Options:

- Modify changes to work across all versions (preferred)
- Document version requirements in patch comments
- Create version-specific patches: `002-name.17.2.x.patch`

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
