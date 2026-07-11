# nvflashk-linux — design & roadmap

> A reproducible, auditable binary patcher for NVIDIA's native Linux NVFlash. It exists to reproduce nvflashk's mismatch override without redistributing NVIDIA binaries.

## Vision

- **As conservative as a firmware tool should be** — exact input identity, byte-level preconditions, atomic output, and refusal on every unknown binary.
- **As auditable as a small patch can be** — recipes name every changed instruction and the research notes explain why.
- **No proprietary redistribution** — users provide an original NVFlash binary.

## Doctrine conformance

| Doctrine | Status | Notes |
|---|---|---|
| 01 extension-first core | n/a | Small one-shot patcher, not an extension host. |
| 02 snapshot in, actions out | n/a | No extension boundary. |
| 03 daemon + thin client | n/a | One-shot tool; no state outlives invocation. |
| 04 declarative front, idempotent executor | diverges | Recipes may become data after a second independently verified target; one target is not yet a declaration system. Reapplying is rejected rather than silently accepted because firmware tooling should expose provenance mistakes. |
| 05 one declaration mechanism | n/a | One verified target; abstraction is deferred until a second target exists. |
| 06 bare core must boot | follows | The CLI builds and reports help without proprietary samples; CI tests use synthetic fixtures. |
| 07 nix source of truth | follows | `nix build` and `nix flake check` are authoritative. Cargo is only a courtesy fallback. |

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Distribution | Patch user-supplied binaries | NVIDIA binaries are proprietary. |
| Matching | SHA-256 + exact original-byte checks | Never patch an ambiguous version or offset. |
| Output | New file, atomic rename | Never modify the user's only NVFlash copy. |
| Initial target | Linux x86-64 NVFlash 5.792.0 from the 5.814 archive | It is the Linux release contemporary with nvflashk 5.814.0.k1 and its hash is reproducible. |
| Hardware testing | Never automated | A real flash requires explicit human confirmation and recovery hardware. |

## Architecture

```text
src/main.rs                 one-shot patch executor
research/                   provenance, disassembly notes, and local tooling
research/samples/           ignored proprietary inputs
flake.nix                   authoritative package/dev/check definitions
```

The executor reads an original binary, proves its identity and expected instruction bytes, writes a patched copy, then verifies the output. It never invokes NVFlash or accesses hardware.

## Deferred (and why)

- Multi-version recipe format: wait for a second verified Linux target.
- GUI/flashing wrapper: unsafe before the patch itself is independently tested.
- ARM/QNX targets: no demonstrated demand or hardware test path.
- Automatic download: licensing/provenance and mirror stability are worse than a user-supplied input.

## Roadmap

- [x] WS0 — Pin the research environment and acquire hash-identified reference binaries. *Accept: Nix shell exposes ELF/PE analysis tools and sample hashes are recorded.*
- [x] WS1 — Recover nvflashk's Windows control-flow modifications and map them to Linux. *Accept: notes identify source and target basic blocks with disassembly evidence.*
- [x] WS2 — Implement the guarded Linux patch. *Accept: synthetic tests cover success, unknown hash, wrong bytes, and existing output.*
- [x] WS3 — Independently validate without writes. *Accept: patched binary starts, reports its version, and retains all non-target bytes.*
- [ ] WS4 — Hardware validation by an equipped tester. *Accept: backup, mismatch prompt, flash, reboot, and restoration are documented on a dual-BIOS/test GPU.*
