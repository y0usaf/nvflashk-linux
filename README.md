# nvflashk-linux

Auditable Linux reproduction of NVFlash mismatch overrides. It patches a user-supplied NVIDIA binary and never redistributes proprietary NVFlash files.

**Status: k2 is statically validated for both the PCI subsystem and Board ID gates, but not hardware-validated. Do not flash without completing the fail-closed no-write procedure, preserving a factory-ROM backup, and providing an independent recovery path.**

## Supported input

Linux x86-64 NVFlash 5.792.0 from TechPowerUp's archive labelled 5.814:

```text
bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7  x64/nvflash
```

Unknown binaries are rejected. The original is never modified.

## Build and patch

```sh
nix build
nix flake check

nix run . -- /path/to/x64/nvflash ./nvflashk-k2
sha256sum ./nvflashk-k2
# expected: 9426d3d05fa2ad0b3a0aa91de56690518f7f83cd26283527baae2e995b08f1d7

nix develop --command python research/verify.py \
  /path/to/x64/nvflash ./nvflashk-k2
```

The generated ELF changes two six-byte instruction spans: the original generic/PCI override branch and the separate Linux Board ID gate. Both edits enter NVIDIA's existing internal handlers. The patcher does not invoke NVFlash or access the GPU.

Reverse-engineering evidence, exact control-flow mapping, and an independent Capstone verifier: [research/NOTES.md](research/NOTES.md). Safety workstreams: [PLAN.md](PLAN.md). Architecture: [DESIGN.md](DESIGN.md).
