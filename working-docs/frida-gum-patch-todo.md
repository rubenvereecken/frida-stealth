# Frida Gum Patch TODO

This document categorizes the types of changes from the old frida-gum patch, organized into batches for systematic application.

## Batch 1: Thread Name Feature Removal (Core)

Complete removal of thread name enumeration capability from the core API.

**Files affected:**

- `gum/gumprocess.h` - Struct definition

**Changes:**

- Remove `const gchar * name;` field from `GumThreadDetails` struct

**Pattern:** This is the foundation change that all other thread name removals depend on.

---

## Batch 2: Thread Name Feature Removal (Platform Implementations)

Remove thread name retrieval from all platform-specific backends.

**Files affected:**

- `gum/backend-darwin/gumprocess-darwin.c`
  - Remove `gchar thread_name[64]` declaration
  - Remove pthread name retrieval logic (pthread_from_mach_thread_np, pthread_getname_np)
  - Remove 15 lines of name population code
- `gum/backend-freebsd/gumprocess-freebsd.c`
  - Remove: `details.name = (p->ki_tdname[0] != '\0') ? p->ki_tdname : NULL;`
- `gum/backend-linux/gumprocess-linux.c`
  - Remove `gum_thread_read_name()` function declaration
  - Remove entire `gum_thread_read_name()` implementation (~20 lines)
  - Remove thread name variable and function call in enumeration
  - Remove `g_free (thread_name)` cleanup
- `gum/backend-qnx/gumprocess-qnx.c`
  - Remove `gchar thread_name[_NTO_THREAD_NAME_MAX]` declaration
  - Remove pthread_getname_np call and name assignment logic (~12 lines)
- `gum/backend-windows/gumprocess-windows.c`
  - Remove `GumGetThreadDescriptionFunc` typedef
  - Remove static function pointer and initialization
  - Remove GetThreadDescription API usage (~30 lines)
  - Remove UTF-16 to UTF-8 name conversion
  - Simplify thread handle opening logic
  - Remove memory cleanup for name field

**Pattern:** Each platform has its own method of retrieving thread names; all must be removed.

---

## Batch 3: Thread Name Feature Removal (JavaScript Bindings)

Remove thread name exposure from JS/V8/QuickJS bindings.

**Files affected:**

- `bindings/gumjs/gumquickprocess.c`
  - Remove code block that defines "name" property on thread object (~6 lines)
- `bindings/gumjs/gumv8process.cpp`
  - Remove code that sets "name" property on thread object (~2 lines)

**Pattern:** Remove JavaScript API surface for thread names.

---

## Batch 4: Thread Name Feature Removal (Tests)

Remove or modify tests that verify thread name functionality.

**Files affected:**

- `tests/core/process.c`
  - Remove `TESTENTRY (process_threads_should_include_name)`
  - Remove `const gchar * name;` from `TestThreadSyncData` struct
  - Remove `name` parameter from `create_sleeping_dummy_thread_sync()` (3 call sites)
  - Simplify thread creation calls (remove name argument)
  - Remove entire `process_threads_should_include_name` test implementation (~20 lines)
  - Remove pthread_setname_np code in `sleeping_dummy()` function
  - Remove `thread_collect_if_matching_id()` function (~15 lines)
  - Remove `g_free ((gpointer) d.name)` cleanup
- `tests/gumjs/script.c`
  - Remove `TESTENTRY (process_threads_have_names)`
  - Remove `GumNamedSleeperContext` struct definition
  - Remove `named_sleeper()` function declaration and implementation (~40 lines)
  - Remove entire `process_threads_have_names` test case (~60 lines)
  - Modify condition in `process_threads_can_be_enumerated_legacy_style`
    - Change: `#if defined (HAVE_MIPS)` → `#if defined (HAVE_ANDROID) || defined (HAVE_MIPS)`

**Pattern:** Remove all test infrastructure for thread name feature.

---

## Batch 5: Thread Name Obfuscation (Gum JS Loop)

Change the internal thread name for the JavaScript execution loop.

**Files affected:**

- `bindings/gumjs/gumscriptscheduler.c`

**Changes:**

- `"gum-js-loop"` → `"banana-gjs-loop"`

**Pattern:** Obfuscate the one remaining internal thread name to avoid detection.

**Note:** This relates to Batch 10 in frida-core patch (anti-anti-frida.py also targets "gum-js-loop").

---

## Batch 6: Branding Changes

Update log domain branding.

**Files affected:**

- `meson.build`

**Changes:**

- `'-DG_LOG_DOMAIN="Frida"'` → `'-DG_LOG_DOMAIN="Banana"'`

**Pattern:** Same branding change as frida-core (Batch 4).

---

## Batch 7: Copyright Notice Cleanup

Remove copyright notices for the thread name feature author.

**Files affected:**

- `bindings/gumjs/gumquickprocess.c`
- `bindings/gumjs/gumv8process.cpp`
- `gum/backend-darwin/gumprocess-darwin.c`
- `gum/backend-linux/gumprocess-linux.c`
- `gum/gumprocess.h`
- `tests/core/process.c`
- `tests/gumjs/script.c`

**Changes:**

- Remove line: `- * Copyright (C) 2023 Grant Douglas <me@hexplo.it>`

**Pattern:** Clean up attribution for removed feature.

---

## Batch 8: Memory Allocation Refactoring

Simplify POSIX memory allocation internals.

**Files affected:**

- `gum/backend-posix/gummemory-posix.c`

**Changes:**

- Remove `gum_memory_allocate_internal()` wrapper function
- Merge its logic directly into `gum_memory_allocate()`
- Remove `extra_flags` parameter from internal functions
- Simplify `gum_allocate_page_aligned()` signature
- Remove FreeBSD-specific MAP_FIXED | MAP_EXCL allocation attempt
- Inline flag handling (change from `base_flags | region_flags` to direct inline)

**Pattern:** Code simplification that may reduce detection surface or simply clean up code.

**Note:** This is more structural than anti-detection, but worth tracking separately.

---

## Batch 9: CI/Build Configuration Changes

Changes to continuous integration and test infrastructure.

**Files affected:**

- `.cirrus.yml`
  - FreeBSD image: `freebsd-13-2` → `freebsd-13-1` (downgrade)
- `tests/run-corellium.sh`
  - **Entire file deleted** (75 lines)

**Changes:**

- Downgrade FreeBSD CI image version
- Remove Corellium device testing infrastructure

**Pattern:** Infrastructure changes (possibly compatibility-related or removing cloud testing).

---

## Batch 10: Year Bumps in Copyright Headers

Year changes in copyright notices.

**Files affected:**

- `gum/backend-freebsd/gumprocess-freebsd.c`
  - `2022-2024` → `2022-2023`
- `gum/backend-posix/gummemory-posix.c`
  - `2008-2024` → `2008-2022`
- `gum/backend-qnx/gumprocess-qnx.c`
  - `2015-2024` → `2015-2023`
- `gum/backend-windows/gumprocess-windows.c`
  - `2009-2024` → `2009-2023`

**Pattern:** Reverting copyright year ranges (likely because patch is for older version).

---

## Implementation Notes

### 1. Dependencies between batches:

- **Batch 1 MUST be done first** - all other thread name changes depend on the struct change
- Batches 2, 3, 4 can be done in parallel after Batch 1
- Batch 5 (thread name obfuscation) is independent and can be done anytime
- Batch 6 (branding) is independent
- Batches 7, 9, 10 are cleanup/metadata

### 2. Relationship to frida-core patch:

- **Batch 5** (gum-js-loop rename) complements **frida-core Batch 10** (anti-anti-frida.py)
- **Batch 6** (branding) matches **frida-core Batch 4** (branding)
- Both patches work together to remove thread name as a detection vector

### 3. Anti-Detection Impact:

**High priority (removes detection vectors):**

- Batches 1-4: Thread name enumeration removal
- Batch 5: Thread name obfuscation
- Batch 6: Branding changes

**Low priority (cleanup/structural):**

- Batch 7: Copyright cleanup
- Batch 8: Memory allocation refactoring
- Batches 9-10: Infrastructure/metadata

### 4. Testing recommendations:

- After Batch 1: Expect compilation errors until Batches 2-4 are complete
- After Batches 1-4: Verify Process.enumerateThreads() works but returns no names
- After Batch 5: Verify gum-js-loop thread is renamed
- Full integration test with frida-core patch

### 5. Version compatibility:

- This patch removes a relatively new feature (2023)
- The thread name field may have evolved or been modified since
- Current codebase may have additional thread name usages not in this patch
- Semantic search needed to find all current thread name references

### 6. Philosophy of this patch:

This patch **removes the thread name enumeration feature entirely** rather than just obfuscating it. This is a more aggressive anti-detection strategy—if the API doesn't expose thread names at all, detection scripts can't use them. The trade-off is loss of debugging/introspection capability.

The one exception is the internal "gum-js-loop" thread, which is renamed rather than removed (since it's internal, not part of the public API).

### 7. Build order considerations:

Since frida-gum is a subproject of frida-core, this should be patched first, or at least the core structure change (Batch 1) must be done before attempting to build frida-core with its patches.
