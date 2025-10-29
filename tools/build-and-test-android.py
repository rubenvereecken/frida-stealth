#!/usr/bin/env python3

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent
BUILD_AND_INSTALL = SOURCE_ROOT / "tools" / "build-and-install-android.py"


def main(argv: list[str]):
    """Build, install, and thoroughly test Frida on Android ARM64."""

    print("=== Frida Android ARM64 Build & Test ===\n", flush=True)

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Get git hash for naming
    git_hash = get_git_hash()
    print(f"Git hash: {git_hash}\n", flush=True)

    # Build directory for testing
    build_dir = SOURCE_ROOT / "build-android-test"

    try:
        # Build and install using the build-and-install script
        print("Building and installing Frida...\n", flush=True)
        run(
            [
                sys.executable,
                str(BUILD_AND_INSTALL),
                "--name",
                f"frida-server-{git_hash}",
                "--build-dir",
                str(build_dir),
                "--keep-build",  # We'll clean up ourselves after tests pass
            ]
        )

        print("\n" + "=" * 60, flush=True)
        print("=== Running Tests ===", flush=True)
        print("=" * 60 + "\n", flush=True)

        # Run tests
        run_tests()

        # Success - clean up
        print("\n=== All tests passed! ===", flush=True)
        print(f"Cleaning up build directory: {build_dir}", flush=True)
        shutil.rmtree(build_dir)
        print("Build directory removed.\n", flush=True)

        print("✓ Build and test completed successfully!", flush=True)

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


def check_prerequisites() -> bool:
    """Check that testing tools are available."""

    # Check for frida CLI
    if not shutil.which("frida"):
        print("ERROR: frida CLI not found in PATH", file=sys.stderr)
        print("Please install frida-tools: pip install frida-tools", file=sys.stderr)
        return False

    print("✓ frida CLI found\n", flush=True)

    return True


def get_git_hash() -> str:
    """Get the current git commit hash (short version)."""
    result = run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=SOURCE_ROOT, capture_output=True
    )
    return result.stdout.strip()


def run_tests():
    """Run comprehensive tests on the deployed Frida server."""

    # Test: Inject and run a script to verify server is working
    print(
        "Test: Injecting 'Hello World' script to verify server functionality...",
        flush=True,
    )
    inject_hello_world()


def inject_hello_world():
    """Inject a simple hello world script into Settings or Play Store."""

    # Create a temporary script file
    script_code = """
console.log("\\n" + "=".repeat(50));
console.log("FRIDA INJECTION TEST");
console.log("Hello World from Frida!");
console.log("Process: " + Process.id + " - " + Process.getCurrentThreadId());
console.log("=".repeat(50) + "\\n");
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(script_code)
        script_path = f.name

    try:
        # Try Settings and Play Store - most reliable targets
        target_apps = [
            "com.android.settings",
            "com.android.vending",
        ]

        for app in target_apps:
            print(f"  Trying target: {app}", flush=True)
            try:
                result = run(
                    ["frida", "-U", "-l", script_path, "-f", app, "--no-pause"],
                    capture_output=True,
                    timeout=15,
                    check=False,
                )

                # Check if we got our expected output
                if "FRIDA INJECTION TEST" in result.stdout:
                    print(f"✓ Successfully injected into {app}", flush=True)
                    print("\nInjection output:")
                    # Print the relevant part of the output
                    for line in result.stdout.split("\n"):
                        if any(
                            marker in line
                            for marker in [
                                "FRIDA INJECTION TEST",
                                "Hello World",
                                "Process:",
                                "===",
                            ]
                        ):
                            print(f"  {line}")
                    return

            except subprocess.TimeoutExpired:
                print(f"  Timeout waiting for {app}", flush=True)
                continue
            except Exception as e:
                print(f"  Failed to inject into {app}: {e}", flush=True)
                continue

        raise Exception(
            "Could not inject into Settings or Play Store. "
            "Make sure one of these apps is installed."
        )

    finally:
        # Clean up temp file
        Path(script_path).unlink(missing_ok=True)


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
