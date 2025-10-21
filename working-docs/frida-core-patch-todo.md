# Frida Core Patch TODO

This document categorizes the types of changes from the old frida-core patch, organized into batches for systematic application.

## Batch 1: Thread Name Changes

Changes to thread names from "frida-_" to "banana-_" or other obfuscated names.

**Files affected:**

- `lib/agent/agent.vala` - eternal-agent threads (3 instances)
- `lib/agent/agent.vala` - emulated agent thread
- `lib/base/p2p.vala` - certificate generation thread
- `lib/gadget/gadget-glue.c` - gadget thread
- `lib/gadget/gadget.vala` - gadget TCP/Unix threads
- `server/server.vala` - server main loop thread
- `src/agent-container.vala` - agent container thread
- `src/frida-glue.c` - main loop thread
- `src/linux/frida-helper-process.vala` - helper process naming

**Pattern:** Replace hardcoded "frida-\*" thread names with randomized or alternate names.

---

## Batch 2: RPC String Obfuscation

Base64 encoding of RPC protocol identifiers.

**Files affected:**

- `lib/base/rpc.vala`

**Changes:**

- `"frida:rpc"` → Base64 encoded strings (`GLib.Base64.decode()`)
- Multiple instances in message handling

**Pattern:** Obfuscate protocol identifiers to avoid simple string scanning.

---

## Batch 3: Network Configuration Changes

Port numbers and default bind addresses.

**Files affected:**

- `lib/base/socket.vala`

**Changes:**

- `DEFAULT_CONTROL_PORT`: 27042 → 27043
- `DEFAULT_CLUSTER_PORT`: 27052 → 27053
- Default control address: 127.0.0.1 → 0.0.0.0
- Default cluster address: 127.0.0.1 → 0.0.0.0

**Pattern:** Change default network configuration to avoid fingerprinting.

---

## Batch 4: Branding/User-Agent Changes

User-facing strings and software identification.

**Files affected:**

- `lib/base/session.vala` - ICE agent software name
- `lib/base/socket.vala` - User-Agent and Server headers
- `lib/gadget/gadget.vala` - Application identifier and name
- `src/frida.vala` - ICE agent software name
- `meson.build` - G_LOG_DOMAIN

**Changes:**

- "Frida" → "Banana" in headers
- "re.frida.Gadget" → "re.banana.Gadget"
- G_LOG_DOMAIN: "Frida" → "Banana"

**Pattern:** Replace branding strings visible to detection mechanisms.

---

## Batch 5: SELinux Context Changes

Android/Linux SELinux security contexts.

**Files affected:**

- `lib/pipe/pipe.vala`
- `lib/selinux/patch.c`
- `src/linux/linjector.vala`

**Changes:**

- `frida_file` → `banana_file`
- `frida_memfd` → `banana_memfd`

**Pattern:** Update SELinux type names to match rebranding.

---

## Batch 6: Socket/IPC Path Changes

Unix domain socket and temporary file paths.

**Files affected:**

- `src/droidy/injector.vala` - Unix socket path
- `src/linux/frida-helper-backend.vala` - Fallback address
- `src/linux/frida-helper-process.vala` - Socket path

**Changes:**

- "frida:" → "banana:" (socket prefix)
- "/frida-" → "/banana-" (temp paths)

**Pattern:** Update IPC identifiers to avoid detection.

---

## Batch 7: GUID and Server Identifier Changes

DBus GUIDs and server identifiers.

**Files affected:**

- `lib/base/session.vala`
- `server/server.vala`

**Changes:**

- `HOST_SESSION_SERVICE`: Static GUID → New random GUID
- `DEFAULT_DIRECTORY`: "re.frida.server" → Randomized UUID (runtime)

**Pattern:** Randomize server identifiers to prevent fingerprinting.

---

## Batch 8: Entry Point Symbol Changes

Dynamic library entry point function names.

**Files affected:**

- `src/agent-container.vala`
- `src/linux/linux-host-session.vala`
- `src/qnx/qnx-host-session.vala`
- `src/windows/windows-host-session.vala`
- `tests/test-agent.vala`
- `tests/test-injector.vala`

**Changes:**

- `"frida_agent_main"` → `"banana_main"`

**Pattern:** Rename exported symbols to avoid detection.

---

## Batch 9: Agent File Name Randomization

Dynamic generation of agent library filenames.

**Files affected:**

- `src/linux/linux-host-session.vala`

**Changes:**

- "frida-agent-<arch>.so" → "{random_prefix}-<arch>.so"
- Generate random prefix at runtime using `GLib.Uuid.string_random()`

**Pattern:** Randomize agent filenames to avoid filesystem scanning.

---

## Batch 10: Anti-Detection Script Integration

Addition of Python post-processing script for agent binaries.

**Files affected:**

- `src/anti-anti-frida.py` - New file
- `src/embed-agent.sh` - Integration

**Changes:**

- Add Python script that uses LIEF to:
  - Rename `frida_agent_main` symbol
  - Replace "frida"/"FRIDA" in all symbols
  - Replace "gum-js-loop" thread name
  - Replace "gmain" thread name
- Integrate script execution in build process

**Pattern:** Post-process binaries to remove remaining fingerprints.

---

## Batch 11: Protocol Error Handling

Droidy protocol handling changes.

**Files affected:**

- `src/droidy/droidy-client.vala`

**Changes:**

- Remove exception throw for certain commands (OPEN/CLSE/WRTE)
- Replace `throw new Error.PROTOCOL` with `break`

**Pattern:** More permissive error handling (possibly to avoid detection).

---

## Batch 12: Debug/Development Changes

Development artifacts and debug code.

**Files affected:**

- `.DS_Store` - Binary file (macOS artifact)
- `lib/agent/agent-glue.c` - Whitespace change
- `lib/agent/agent.vala` - Trailing space
- `src/linux/linjector.vala` - Debug print statement
- `src/linux/linux-host-session.vala` - Empty line

**Changes:**

- Minor whitespace/formatting
- Debug print for entrypoint

**Pattern:** Clean up or document debug changes.

---

## Implementation Notes

1. **Dependencies between batches:**

   - Batch 8 must be coordinated with Batch 10 (symbol renaming)
   - Batch 5 must match naming from Batches 1, 4, 6

2. **Testing recommendations:**

   - Test each batch independently where possible
   - Verify Android/Linux builds after Batch 5
   - Full integration test after all batches

3. **Version compatibility:**

   - This patch is from an older Frida version
   - File paths and line numbers may have changed
   - Symbol/function signatures may have evolved
   - Semantic search will be needed to locate current equivalents

4. **Priority order:**
   - High: Batches 1, 4, 8 (core detection vectors)
   - Medium: Batches 2, 5, 6, 7, 9 (secondary detection)
   - Low: Batches 3, 11, 12 (configuration/cleanup)
   - Special: Batch 10 (requires new tooling)
