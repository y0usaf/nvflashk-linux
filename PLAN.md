# Blower VBIOS restoration plan

## Goal

Safely restore the RTX 4090's original blower VBIOS (`G139-0332`, `95.02.3C.40.40`) from the two byte-identical Windows backups, but only after the Linux patch demonstrably bypasses both the PCI subsystem and Board ID checks without writing the EEPROM.

## Known artifacts

| Artifact | Identity | SHA-256 | Role |
|---|---|---|---|
| Current live dump | `G136-0332`, Board `046E`, `10DE:16F4`, `95.02.47.00.01` | `e1939223b7c92d5f00bfe8aa8d7cea5cb0ea5cefc243d93511c3d2a67d22079f` | Recovery image for the currently working FE firmware |
| `257978.rom` | Same metadata as current FE firmware | `1a5d4d0917d28e3d62694a2e0407100ee8a8c65089909779384d19061b5319c6` | Public/source FE image; not the blower firmware |
| `backup.rom` | `G139-0332`, Board `0475`, `10DE:16F3`, `95.02.3C.40.40` | `eea10264881c38d7f80e2b8caf3f986f0753ec84b424dbc9689b90fc862a7c1d` | Original blower candidate |
| `backup2.rom` | Byte-identical to `backup.rom` | `eea10264881c38d7f80e2b8caf3f986f0753ec84b424dbc9689b90fc862a7c1d` | Independent original blower read |
| Stock Linux NVFlash | 5.792.0 x86-64 | `bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7` | Backup, parsing, and same-ID operations |
| Previous patched NVFlash | Experimental k1 | `06508cc681069d295f9006bdd1179f207fcf94f890a7927eb437af918850e221` | PCI subsystem bypass only; retained for evidence, **not ready to flash** |
| Current patched NVFlash | Experimental k2 | `9426d3d05fa2ad0b3a0aa91de56690518f7f83cd26283527baae2e995b08f1d7` | PCI subsystem + Board ID bypass; statically validated, awaiting fail-closed no-write run |

The Windows partition is mounted read-only during analysis. Before any write, both blower and FE recovery images must also exist on independent storage outside their source NVMe.

## Current blocker

The first Linux patch forced NVIDIA's internal PCI subsystem override path. A no-write run confirmed that path, then terminated with:

```text
Overriding the PCI Subsystem ID mismatch.
ERROR: Board ID mismatch.
Nothing changed!
```

Static analysis has now located the separate Board ID gate and k2 redirects it to NVIDIA's existing Board ID bit-test/report/clear handler. The next blocker is dynamic validation: the exact k2 transcript must be captured with a fail-closed no-write run. `Overriding Board ID mismatch` is a status message, not a second confirmation prompt.

## Safety invariants

1. No EEPROM write during WS0–WS5.
2. Run all GPU operations from the `vbios-maintenance` Limine specialisation.
3. NVIDIA/Nouveau modules must be absent and the RTX 4090 must have no bound driver.
4. AMD iGPU must remain bound to `amdgpu`; display and SSH recovery must work independently.
5. Never use scripted input that could accidentally answer the final update prompt with `y`.
6. Patch only exact SHA-256-identified binaries and exact expected instruction bytes.
7. Never overwrite source ROMs or the stock NVFlash binary.
8. A real write requires a separate, explicit human decision after all pre-flash gates pass.
9. The final `y` confirmation is manual—never automated or piped.
10. If any observed output differs from the expected transcript, stop.

## Workstreams

### WS0 — Preserve recovery artifacts

- Copy the complete FE dump directory to another physical device/machine.
- Copy both original blower dumps from the Windows NVMe to Linux and independent storage.
- Verify all copies using the hashes above.
- Store metadata and hashes alongside each copy.
- Keep the 150,528-byte sysfs PCI ROM only as identification evidence; never use it for recovery.

**Accept:** At least two physical devices hold the full FE dump and blower image; hashes match the table.

### WS1 — Locate the Linux Board ID gate

- Follow xrefs to:
  - `Board ID mismatch`
  - `overrideboard`
  - `Overriding Board ID mismatch`
  - compatibility Board ID reporting strings
- Recover function boundaries from `.eh_frame`.
- Trace control flow after the accepted PCI subsystem override.
- Identify where the Board ID mismatch throws/returns instead of invoking the internal override handler.
- Compare the equivalent Windows 5.814 function and its arguments/state transitions.
- Record virtual address, file offset, original bytes, branch target, and semantic rationale.

**Accept:** `research/NOTES.md` explains the failing Linux branch and proposed edit with disassembly evidence; no binary has been changed speculatively.

**Status:** Complete for k2; evidence is recorded in `research/NOTES.md`.

### WS2 — Implement guarded k2 patch

- Add the Board ID edit to the Rust patcher.
- Require the exact stock input SHA-256.
- Verify original bytes at every patch offset before changing anything.
- Calculate and pin the complete k2 output SHA-256.
- Keep atomic, no-overwrite output behavior.
- Add tests for:
  - both edits applied
  - either instruction precondition failing
  - unsupported input hash
  - existing output refusal
  - exact changed-byte count

**Accept:** `nix flake check` passes and the output differs only at documented instructions.

**Status:** Complete; k2 SHA-256 is pinned and all guarded patcher tests pass.

### WS3 — Static validation

- Disassemble every patched basic block.
- Confirm control transfer reaches NVIDIA's existing override handler.
- Confirm no jump lands inside an instruction.
- Confirm ELF headers, size, permissions, and all non-target bytes are unchanged.
- Have a second analysis method reproduce offsets (for example, Ghidra plus Capstone/objdump).

**Accept:** Two independent disassembly methods agree; the changed-byte manifest is exact.

**Status:** Complete; GNU objdump and `research/verify.py` (Capstone/pyelftools) agree.

### WS4 — Fail-closed no-write harness

Build a PTY state machine that:

- launches patched NVFlash against `backup.rom`
- recognizes only exact expected prompts and status lines
- sends `YES` only after the exact generic/PCI subsystem override prompt
- recognizes the exact PCI subsystem override status without sending input
- recognizes `Overriding Board ID mismatch` as a status without sending input
- sends lowercase `n` after the exact final `Update display adapter firmware?` prompt
- kills NVFlash immediately on timeout, EOF, reordered prompts, or unknown output
- never contains or sends lowercase `y`

Keep staged manual checks as additional evidence:

1. EOF at the sole override prompt → `Nothing changed`.
2. One `YES`, then EOF before the final update answer → both override status lines are present but no write occurs.
3. Full PTY sequence → send one `YES`, reach the final update prompt, and send `n`.

**Accept:** Transcript shows both mismatches overridden, correct current/replacement metadata, final abort, and `Nothing changed`.

### WS5 — Prove the no-write test changed nothing

Immediately after WS4:

- Use stock NVFlash to create two fresh live dumps.
- Compare them byte-for-byte.
- Compare their SHA-256 to the pre-test live dump.
- Re-parse metadata with stock NVFlash.

**Accept:** Post-test dumps are identical to each other and the pre-test dump; live VBIOS remains `95.02.47.00.01`.

### WS6 — Validate the blower image

- Reconfirm `backup.rom` and `backup2.rom` are byte-identical.
- Parse both with stock NVFlash.
- Confirm:
  - Device ID `10DE:2684`
  - Chip SKU `301-0`
  - Project `G139-0332`
  - Board ID `0475`
  - Subsystem `10DE:16F3`
  - signed UEFI image
  - InfoROM backup present
- Correlate hash/metadata with public RTX 4090 VBIOS records where possible.
- Inspect power, thermal, and fan tables with an independent parser if available.
- Record that the physical card is a blower and that the historical high fan curve is expected behavior.

**Accept:** No unexplained identity, signature, image-layout, or hardware-topology conflict remains.

### WS7 — Pre-flash gate

All items must be true:

- [ ] WS0–WS6 accepted
- [ ] FE recovery image copied off-machine
- [ ] Blower image copied off-machine
- [ ] UPS/stable power available
- [ ] Motherboard display connected and working
- [ ] SSH or local TTY available through AMD iGPU
- [ ] `vbios-maintenance` booted
- [ ] NVIDIA/Nouveau modules absent
- [ ] RTX 4090 unbound from any driver
- [ ] Stock and k2 binaries re-hashed
- [ ] Candidate re-hashed immediately before use
- [ ] Recovery commands written down and available offline
- [ ] User explicitly approves the real write

**Accept:** Checklist archived with hashes and timestamp.

### WS8 — Restore original blower VBIOS

- Run k2 manually against the verified blower image.
- Confirm displayed current metadata is FE `G136-0332 / 046E / 16F4`.
- Confirm replacement metadata is blower `G139-0332 / 0475 / 16F3`.
- Manually acknowledge only the expected mismatch prompts.
- Manually enter the final `y` only after one last review.
- Do not interrupt power or reboot until NVFlash reports completion.
- Save the complete terminal transcript.
- Power-cycle into `vbios-maintenance` first, not the graphical desktop.

**Accept:** NVFlash reports a successful write and the machine returns to maintenance mode through the AMD iGPU.

### WS9 — Post-flash validation

- Read the installed VBIOS twice with stock NVFlash.
- Verify version, project, Board ID, subsystem, and hashes.
- Expect preserved card-specific InfoROM areas, so compare semantically before requiring whole-file identity.
- Confirm the blower fan behaves before applying load.
- Boot normally only after idle fan/temperature checks pass.
- Increase load gradually while monitoring temperature, fan RPM, power, voltage, and display stability.

**Accept:** Original blower identity and cooling behavior are restored with stable low-load operation.

## Recovery branches

### Card enumerates after a bad flash

1. Boot `vbios-maintenance` through AMD iGPU.
2. Confirm the 4090 appears on PCIe and has no driver.
3. Reflash the appropriate verified recovery image with k2 if IDs mismatch.
4. Power-cycle and revalidate before normal boot.

### Card does not provide display but still enumerates

Use the same maintenance/SSH recovery path; no NVIDIA display output is required.

### Card does not enumerate or blocks POST

Software recovery is no longer sufficient. Stop power-on attempts and use a known-correct external SPI programming procedure or qualified hardware repair. Do not improvise voltage, pinout, or flash-chip access.

## Explicit non-goals

- Flashing arbitrary RTX 4090 VBIOS files
- Cross-generation or different-GPU-chip flashing
- Automating the final write confirmation
- Treating a successful no-write bypass as proof of electrical compatibility
- Using the patched binary outside exact pinned versions
