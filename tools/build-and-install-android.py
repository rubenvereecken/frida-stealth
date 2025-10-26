#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str]):
    """Build Frida for Android ARM64 and install on a connected device."""

    parser = argparse.ArgumentParser(
        description="Build and install Frida for Android ARM64"
    )
    parser.add_argument(
        "--name",
        default="frida-server",
        help="Name for the binary on device (default: frida-server)",
    )
    parser.add_argument(
        "--device",
        help="Device ID to use (default: first connected device)",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=SOURCE_ROOT / "build-android",
        help="Build directory path (default: build-android)",
    )
    parser.add_argument(
        "--keep-build",
        action="store_true",
        help="Keep build directory after installation",
    )
    args = parser.parse_args(argv[1:])

    print("=== Frida Android ARM64 Build & Install ===\n", flush=True)

    # Check prerequisites
    device_id = check_prerequisites(args.device)
    if not device_id:
        sys.exit(1)

    # Create build directory
    build_dir = args.build_dir
    if build_dir.exists():
        print(f"Removing existing build directory: {build_dir}", flush=True)
        shutil.rmtree(build_dir)

    build_dir.mkdir()
    print(f"Created build directory: {build_dir}\n", flush=True)

    try:
        # Configure
        print("Configuring Frida for Android ARM64...", flush=True)
        configure_script = SOURCE_ROOT / "configure"
        run([str(configure_script), "--host=android-arm64"], cwd=build_dir)
        print("Configuration complete.\n", flush=True)

        # Build
        print("Building Frida (this may take a while)...", flush=True)
        run(["make"], cwd=build_dir)
        print("Build complete.\n", flush=True)

        # Find frida-server binary
        frida_server = find_frida_server(build_dir)
        if not frida_server:
            print(
                "ERROR: Could not find frida-server binary in build directory",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"Found frida-server: {frida_server}\n", flush=True)

        # Deploy
        remote_path = f"/data/local/tmp/{args.name}"
        deploy(frida_server, remote_path, device_id)

        # Success
        print(f"\n✓ frida-server installed as {remote_path}", flush=True)

        # Clean up unless --keep-build
        if not args.keep_build:
            print(f"Cleaning up build directory: {build_dir}", flush=True)
            shutil.rmtree(build_dir)
            print("Build directory removed.", flush=True)
        else:
            print(f"Build directory preserved: {build_dir}", flush=True)

        print("\n✓ Build and install completed successfully!", flush=True)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if isinstance(e, subprocess.CalledProcessError):
            for label, data in [("Output", e.output), ("Stderr", e.stderr)]:
                if data:
                    print(
                        f"{label}:\n\t| " + "\n\t| ".join(data.strip().split("\n")),
                        file=sys.stderr,
                    )
        print(
            f"\nBuild directory preserved for inspection: {build_dir}", file=sys.stderr
        )
        sys.exit(1)


def check_prerequisites(device_id: str | None) -> str | None:
    """Check that all required tools and environment variables are available.
    Returns the device ID to use, or None on failure."""

    # Check ANDROID_NDK_ROOT
    ndk_root = os.environ.get("ANDROID_NDK_ROOT")
    if not ndk_root:
        print(
            "ERROR: ANDROID_NDK_ROOT environment variable is not set", file=sys.stderr
        )
        print("Please set it to your Android NDK installation path", file=sys.stderr)
        return None

    ndk_path = Path(ndk_root)
    if not ndk_path.exists():
        print(
            f"ERROR: ANDROID_NDK_ROOT points to non-existent path: {ndk_root}",
            file=sys.stderr,
        )
        return None

    print(f"✓ ANDROID_NDK_ROOT: {ndk_root}", flush=True)

    # Check for adb
    if not shutil.which("adb"):
        print("ERROR: adb not found in PATH", file=sys.stderr)
        print("Please install Android SDK platform-tools", file=sys.stderr)
        return None

    print("✓ adb found", flush=True)

    # Check for connected device
    result = run(["adb", "devices"], capture_output=True)
    devices = [line for line in result.stdout.strip().split("\n")[1:] if line.strip()]

    if not devices:
        print("ERROR: No Android devices connected", file=sys.stderr)
        print("Please connect a device and enable USB debugging", file=sys.stderr)
        return None

    # Use specified device or first available
    if device_id:
        if not any(device_id in line for line in devices):
            print(f"ERROR: Device {device_id} not found", file=sys.stderr)
            return None
        print(f"✓ Using device: {device_id}", flush=True)
        return device_id
    else:
        # Extract device ID from first device (format: "device_id    device")
        device_id = devices[0].split()[0]
        print(f"✓ Using device: {device_id}", flush=True)
        return device_id


def find_frida_server(build_dir: Path) -> Path | None:
    # Common paths where frida-server might be located
    patterns = [
        "subprojects/frida-core/server/frida-server",
        "build/subprojects/frida-core/server/frida-server",
        "**/frida-server",
    ]

    for pattern in patterns:
        matches = list(build_dir.glob(pattern))
        if matches:
            # Return the first match that's actually a file
            for match in matches:
                if match.is_file():
                    return match

    return None


def deploy(frida_server: Path, remote_path: str, device_id: str):
    print("Deploying frida-server to device...", flush=True)

    # Push to device
    run(["adb", "-s", device_id, "push", str(frida_server), remote_path])
    print(f"✓ Pushed to {remote_path}", flush=True)

    # Make executable
    run(["adb", "-s", device_id, "shell", "chmod", "755", remote_path])
    print("✓ Made executable", flush=True)

    # Kill any existing frida-server instances
    print("Stopping any existing frida-server instances...", flush=True)
    run(["adb", "-s", device_id, "shell", "killall", "-9", "frida-server"], check=False)
    time.sleep(1)

    # Start frida-server with nohup
    print("Starting frida-server...", flush=True)
    run(["adb", "-s", device_id, "shell", f"nohup {remote_path} > /dev/null 2>&1 &"])

    # Give it a moment to start
    time.sleep(2)

    # Verify it's running
    result = run(["adb", "-s", device_id, "shell", "ps", "-A"], capture_output=True)
    if "frida-server" not in result.stdout:
        raise Exception("frida-server does not appear to be running")

    print("✓ frida-server is running", flush=True)


def run(
    argv: list[str],
    check: bool = True,
    capture_output: bool = False,
    timeout: int | None = None,
    **kwargs,
) -> subprocess.CompletedProcess:
    kwargs_to_use = {"check": check, **kwargs}

    if capture_output:
        kwargs_to_use["capture_output"] = True
        kwargs_to_use["encoding"] = "utf-8"

    if timeout:
        kwargs_to_use["timeout"] = timeout

    return subprocess.run(argv, **kwargs_to_use)


if __name__ == "__main__":
    main(sys.argv)
