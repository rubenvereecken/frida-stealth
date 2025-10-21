# Contributing to Frida Stealth

This document explains how the repository is organized and how to contribute new stealth patches.

## Repository Organization

### Branch Structure

**Main development:**

- `stealth/main` - Main development branch, tracks upstream Frida

**Version branches:**

- `stealth/17.3.2`, `stealth/17.3.1`, etc.
- Each corresponds to an upstream Frida release tag
- All stealth patches are applied to these branches

### Patch Storage

Patches are stored in the submodule repositories:

- `subprojects/frida-core/patches/` - frida-core patches
- `subprojects/frida-gum/patches/` - frida-gum patches

Patch naming convention: `00X-short-description.patch`

- `001-obfuscate-threads.patch`
- `002-rename-sockets.patch`
- etc.

### Patch Tracking

Each patch file is committed and tagged:

- Commit message: `generated patch 00X-description`
- Git tag: `stealth-patch/00X-description`

This allows easy tracking of when patches were generated and what commit they correspond to.

## Development Workflow

### Prerequisites

Ensure you have Python 3 and git configured. The repository includes helper scripts in `tools/`:

- `create-version-branches.py` - Create stealth branches for all versions
- `apply-commit-to-branches.py` - Apply a commit to all version branches
- `generate-patch.py` - Generate a .patch file from a commit
- `commit-and-tag-patch.py` - Commit and tag a generated patch

### Making a New Stealth Modification

#### 1. Create your changes on stealth/main

Work on `stealth/main` (or the relevant submodule's `stealth/main`):

```bash
cd subprojects/frida-core
git checkout stealth/main

# Make your changes
vim lib/agent/agent.vala

# Commit your changes
git add lib/agent/agent.vala
git commit -m "Obfuscate thread names to avoid detection"
```

Note the commit hash, e.g., `37ca12d8`.

#### 2. Apply to all version branches

Use the `apply-commit-to-branches.py` script to cherry-pick your commit onto all `stealth/*` version branches:

```bash
cd /path/to/frida  # Top-level frida directory
./tools/apply-commit-to-branches.py frida-core 37ca12d8
```

This will:

- Iterate through all `stealth/17.x.x` branches
- Cherry-pick the commit onto each branch
- Abort if any conflicts occur (you'll need to resolve manually)
- Restore your original branch when done

**For frida-gum changes:**

```bash
./tools/apply-commit-to-branches.py frida-gum abc123def
```

#### 3. Generate the patch file

Generate a unified patch file from your commit:

```bash
./tools/generate-patch.py frida-core 37ca12d8 001-obfuscate-threads.patch
```

This will:

- Generate a diff for commit `37ca12d8~..37ca12d8`
- Verify the patch is identical across all version branches
- Save to `subprojects/frida-core/patches/001-obfuscate-threads.patch`

**Important:** The patch is generated from the version branches, not from `stealth/main`. This ensures it applies cleanly to upstream versions.

#### 4. Commit and tag the patch

```bash
./tools/commit-and-tag-patch.py frida-core 001-obfuscate-threads.patch
```

This automates:

- `git add patches/001-obfuscate-threads.patch`
- `git commit -m "generated patch 001-obfuscate-threads"`
- `git tag stealth-patch/001-obfuscate-threads`

#### 5. Push everything

```bash
# Push all branches (main + version branches)
cd subprojects/frida-core
git push origin 'stealth/*'

# Push tags
git push origin --tags
```

### Adding Support for New Upstream Versions

When Frida releases a new version (e.g., `17.4.0`):

#### 1. Fetch upstream tags

```bash
cd subprojects/frida-core
git fetch upstream --tags

cd subprojects/frida-gum
git fetch upstream --tags
```

#### 2. Create version branches

```bash
cd /path/to/frida  # Top-level
./tools/create-version-branches.py
```

This creates `stealth/17.4.0` branches in all three repositories (frida, frida-core, frida-gum).

#### 3. Apply existing patches

For each existing patch, apply it to the new version branch:

```bash
cd subprojects/frida-core
git checkout stealth/17.4.0
git apply patches/001-obfuscate-threads.patch
git apply patches/002-next-patch.patch
# ... etc

git commit -am "applied stealth patches"
```

Or cherry-pick from another version branch:

```bash
git checkout stealth/17.4.0
git cherry-pick stealth/17.3.2  # Cherry-pick the patch commits
```

#### 4. Verify and push

```bash
# Test build the new version
cd /path/to/frida
git checkout stealth/17.4.0
make

# Push if successful
cd subprojects/frida-core
git push origin stealth/17.4.0
```

## Troubleshooting

### Cherry-pick conflicts

If `apply-commit-to-branches.py` fails with conflicts on a specific version:

1. The script will abort and report which branch failed
2. Manually checkout that branch: `git checkout stealth/17.x.x`
3. Manually cherry-pick: `git cherry-pick <commit>`
4. Resolve conflicts, then `git cherry-pick --continue`
5. Re-run the script - it will skip already-applied branches

### Patch doesn't apply to all versions

If `generate-patch.py` warns that some branches have different changes:

1. It will save variant patches as `001-description.17.2.3.patch`
2. Investigate why the diff differs (file might not exist in older versions, etc.)
3. Either:
   - Create version-specific patches if needed
   - Skip unsupported versions
   - Adjust your changes to work across all versions

## Repository Remotes

### frida-core

- `origin` - Your stealth fork: `git@github.com:yourname/frida-core-stealth.git`
- `upstream` - Official Frida: `https://github.com/frida/frida-core.git`

### frida-gum

- `origin` - Your stealth fork: `git@github.com:yourname/frida-gum-stealth.git`
- `upstream` - Official Frida: `https://github.com/frida/frida-gum.git`

## Best Practices

1. **Always work on `stealth/main` first** - Don't make changes directly on version branches
2. **Test thoroughly** - Build and test on at least one version branch before applying to all
3. **Keep patches focused** - One logical change per patch
4. **Document detection vectors** - In commit messages, explain what detection method the patch addresses
5. **Version compatibility** - Consider whether changes work across all supported versions

## Questions?

Open an issue or discussion on the repository if you need help with the workflow.
