# nvflashk-linux

Auditable Linux reproduction of nvflashk's NVFlash mismatch override. It patches a user-supplied NVIDIA binary and never redistributes proprietary NVFlash files.

**Status: reverse-engineered and reproducibly built, but not hardware-validated. Do not flash without a factory-ROM backup and an independent recovery path (dual BIOS, iGPU, or second GPU).**

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

nix run . -- /path/to/x64/nvflash ./nvflashk
sha256sum ./nvflashk
# expected: 06508cc681069d295f9006bdd1179f207fcf94f890a7927eb437af918850e221
```

The generated ELF changes one six-byte conditional jump, forcing NVIDIA's existing internal `override detected` path. It does not invoke NVFlash or access the GPU.

Reverse-engineering evidence and the exact control-flow mapping: [research/NOTES.md](research/NOTES.md). Architecture and remaining hardware-validation milestone: [DESIGN.md](DESIGN.md).
