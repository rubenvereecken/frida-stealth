# Frida Stealth

A maintained fork of [Frida](https://frida.re/) with stealth patches applied to evade common detection methods.

**Inspiration & Credits:** This project builds upon the excellent work from [AsenOsen/frida-stealth](https://github.com/AsenOsen/frida-stealth) and [JsHookApp/Frida-Patchs](https://github.com/JsHookApp/Frida-Patchs).

## What does it do?

These patches modify Frida to avoid common detection patterns:

- Obfuscated thread names (no more "frida-\*" threads)
- Renamed internal loops and data structures
- Modified default port numbers
- Anonymized unix socket names
- Cleaned SELinux context names

For additional Android-specific stealth techniques, see [AsenOsen's framework patching approach](https://github.com/AsenOsen/android-framework-jar-patching).

## Getting Started

### Option 1: Pre-patched (Recommended)

This repository maintains pre-patched versions of Frida. Simply clone and build:

```bash
git clone --recurse-submodules https://github.com/rubenvereecken/frida.git
cd frida
```

**Optional:** If you need a specific Frida version, checkout the corresponding branch before building:

```bash
git checkout stealth/17.3.2 # Optional! By default you're on stealth/main which tracks frida main
```

**Initialize submodules:**

```bash
git submodule update --init --recursive
```

Then build Frida as normal. For detailed build instructions, see the [official Frida documentation](https://frida.re/docs/building/).

#### Quick build examples

**Python bindings:**

```bash
make python-macos  # or python-linux, python-windows
pip install subprojects/frida-python
```

**Android (arm64):**

```bash
export ANDROID_NDK_ROOT="$ANDROID_HOME/ndk/25.2.9519653"
make core-android-arm64
```

Binaries will be in `build/frida-android-arm64/`.

### Option 2: Manual Patching (For Maintainers)

If you're maintaining your own Frida fork and want to apply these patches manually:

**Apply patches to frida-core:**

```bash
cd subprojects/frida-core
git apply /path/to/frida-stealth/subprojects/frida-core/patches/*.patch
```

**Apply patches to frida-gum:**

```bash
cd subprojects/frida-gum
git apply /path/to/frida-stealth/subprojects/frida-gum/patches/*.patch
```

Note: Patches are maintained for each Frida version. Use patches from the corresponding `stealth/X.Y.Z` branch.

After applying patches, build Frida normally following [official build instructions](https://frida.re/docs/building/).

## Additional Stealth Techniques

For Android, consider these complementary approaches:

1. **[ZygiskFrida](https://github.com/lico-n/ZygiskFrida)** - Inject via Zygisk to avoid ptrace detection
   - Use with [Kitsune Magisk](https://github.com/HuskyDG/magisk-files) (not regular Magisk)
2. **[AntiFrida Bypass Scripts](https://github.com/apkunpacker/AntiFrida_Bypass)** - Runtime memory obfuscation
3. **[Framework Patching](https://github.com/AsenOsen/android-framework-jar-patching)** - System library injection

## Building from Source (Platform-Specific)

### Apple Platforms

Create a code-signing certificate first (see [GDB's guide](https://sourceware.org/gdb/wiki/PermissionsDarwin)):

```bash
export MACOS_CERTID=frida-cert
export IOS_CERTID=frida-cert
make
sudo killall taskgated  # Restart taskgated to accept new cert
```

### CLI Tools

Install required Python packages:

```bash
pip install colorama prompt-toolkit pygments
```

## Learn More

- [Official Frida Documentation](https://frida.re/docs/home/)
- [Building Frida](https://frida.re/docs/building/)
- [Original Frida Repository](https://github.com/frida/frida)

## Contributing

Want to add a new stealth modification? See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- How the repository and branches are organized
- Complete workflow for creating and applying patches
- Helper scripts in `tools/` for maintaining patches across versions
