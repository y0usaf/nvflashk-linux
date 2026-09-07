# nvflashk-linux

A small, auditable patcher for a user-supplied Linux NVIDIA NVFlash binary. It does not include, fetch, or redistribute NVFlash or VBIOS/ROM files.

## Status: 0.1.0 — experimental

**Flashing incompatible firmware can leave a GPU unusable and require hardware repair. Removing a mismatch check does not make firmware compatible. This is not an NVIDIA-supported tool or a promise of parity with Windows nvflashk.**

`0.1.0` reproduces the exact existing **k4** output (the hash identifies generated NVFlash, not the patcher executable):

```text
SHA-256: 082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa
```

The patch was exercised during an experimental restoration on one RTX 4090 using its original VBIOS. Startup fan spin and repeated post-write readbacks were observed for that card. Sustained cooling, extended workloads, and broader hardware compatibility remain pending. This evidence is not a compatibility guarantee.

## Safe build and patch

Use a legally obtained, unmodified Linux x86-64 NVFlash 5.792.0 input whose SHA-256 is:

```text
bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7
```

The patcher never invokes NVFlash and never modifies the input:

```sh
nix build
nix flake check
nix run . -- /path/to/x64/nvflash ./nvflashk-k4
sha256sum ./nvflashk-k4
nix develop --command python research/verify.py \
  /path/to/x64/nvflash ./nvflashk-k4
```

The output changes nine byte values across two documented instruction spans. Unknown input hashes, mismatched original bytes, and existing output paths are rejected. `--overridesub` remains an NVFlash runtime option; it is not a patcher option.

## Hardware boundary

No hardware command is part of the build or verification procedure. Firmware work is experimental and at the operator's risk. Software recovery may help only when the card still enumerates and an independent display/recovery path is available. If the card no longer enumerates or prevents POST, software recovery is insufficient; stop and use qualified hardware SPI recovery or repair. Do not improvise electrical procedures.

The no-write harness in `research/no_write.py` is machine-specific research for the reviewed transcript and exact environment. It is not a generic dry run, compatibility test, or write-safety guarantee.

See [validation evidence](docs/VALIDATION.md), [reverse-engineering notes](research/NOTES.md), and the [release/RC procedure](docs/RELEASING.md).

## License and attribution

Project-authored code is MIT licensed; this does not license NVIDIA binaries or firmware. See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md). Review applicable terms and local law before obtaining, modifying, or using third-party software. Source-only distribution is not a legal clearance.

This project credits [notfromstatefarm/nvflashk](https://github.com/notfromstatefarm/nvflashk) as the Windows behavioral reference; it does not claim affiliation or endorsement.
