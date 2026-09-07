# Maintenance research note

This file records public, sanitized findings only. It contains no private paths, USB identifiers, recovery-kit names, assistant history, or operational flash procedure.

## Finding

The k4 patch retains the stock NVFlash flow except for the reviewed mismatch paths. Static checks and the reviewed single-card experiment support the exact output hash published in [README.md](../README.md). The experiment restored the original VBIOS identity on one RTX 4090; startup fan spin and repeated readbacks were observed. Sustained cooling and workload validation remain open.

## Limits

- This is not a compatibility matrix or a safety guarantee.
- A successful no-write transcript does not prove electrical, thermal, or firmware compatibility.
- The harness and transcript matching are machine-specific research, not a generic dry run.
- Software recovery depends on PCI enumeration and an independent recovery path. A card that blocks POST or disappears from PCIe requires qualified hardware recovery.
- No proprietary NVFlash binary, VBIOS, ROM, or recovery artifact is included here.

## Reproduction boundary

Use only the safe patch/build and static verification commands in the README. Do not infer hardware readiness from a successful build, disassembly check, or simulated PTY test. Hardware commands are intentionally omitted from this public note.
