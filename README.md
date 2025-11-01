# Frida Stealth

A maintained 1:1 mirror of [Frida](https://frida.re/) with stealth patches applied to evade common detection methods. Patches also available separately.

**Inspiration & Credits:** This project builds upon the excellent work from [AsenOsen/frida-stealth](https://github.com/AsenOsen/frida-stealth) (supports up to Frida v16) and [JsHookApp/Frida-Patchs](https://github.com/JsHookApp/Frida-Patchs).

Supports Frida v17+.

## What does it do?

These patches modify Frida to avoid common detection patterns:

- Obfuscated thread names (no more "frida-\*" threads)
- Renamed internal loops and data structures
- Modified default port numbers
- Anonymized unix socket names

To see all patches:

- [frida-core patches](https://github.com/rubenvereecken/frida-core-stealth/tree/stealth/main/patches)
- [frida-gum patches](https://github.com/rubenvereecken/frida-gum-stealth/tree/stealth/main/patches)

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

Some available versions (latest per major + minor):

- `stealth/17.4.0` - Latest 17.4.x
- `stealth/17.3.2` - Latest 17.3.x
- `stealth/17.2.17` - Latest 17.2.x
- `stealth/17.1.5` - Latest 17.1.x
- `stealth/17.0.7` - Latest 17.0.x

**Initialize submodules:**

```bash
git submodule update --init --recursive
```

Then build Frida as normal. For detailed build instructions, see the [official Frida documentation](https://frida.re/docs/building/).

**Important:** Build frida-tools from this repo for seamless compatibility. The stealth patches change the default port (27042→27043), so using vanilla frida-tools requires manual port forwarding:

```bash
# If using vanilla frida-tools with stealth frida-server:
adb forward tcp:27043 tcp:27043
frida -H 127.0.0.1:27043 ...

# If using stealth frida-tools (recommended):
frida -U ...  # Just works!
```

To build frida-tools, include `--enable-frida-tools` when configuring native builds.

### Option 2: Manual Patching (For Maintainers)

If you're maintaining your own Frida fork, apply patches manually:

```bash
git -C subprojects/frida-core apply /path/to/frida-stealth/subprojects/frida-core/patches/*.patch
git -C subprojects/frida-gum apply /path/to/frida-stealth/subprojects/frida-gum/patches/*.patch
```

Use patches from the corresponding `stealth/X.Y.Z` branch for version-specific patches. Then build normally per [official docs](https://frida.re/docs/building/).

## Additional Stealth Techniques

For Android, consider these complementary approaches:

1. **[ZygiskFrida](https://github.com/lico-n/ZygiskFrida)** - Inject via Zygisk to avoid ptrace detection
   - Use with [Kitsune Magisk](https://github.com/HuskyDG/magisk-files) (not regular Magisk)
2. **[AntiFrida Bypass Scripts](https://github.com/apkunpacker/AntiFrida_Bypass)** - Runtime memory obfuscation
3. **[Framework Patching](https://github.com/AsenOsen/android-framework-jar-patching)** - System library injection

## Contributing

Want to add a new stealth modification? See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- How the repository and branches are organized
- Complete workflow for creating and applying patches
- Helper scripts in `tools/` for maintaining patches across versions
