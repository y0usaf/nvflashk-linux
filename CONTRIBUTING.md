# Contributing

Keep changes small, reviewable, and reproducible. Do not add proprietary NVFlash binaries, VBIOS/ROM files, recovery images, private paths, USB identifiers, personal logs, or assistant/session history.

For patch changes:

```sh
nix build
nix flake check
nix run . -- /path/to/x64/nvflash ./nvflashk-k4
sha256sum ./nvflashk-k4
nix develop --command python research/verify.py /path/to/x64/nvflash ./nvflashk-k4
```

Use legally obtained user-supplied inputs; do not commit them. Hardware tests are not required for ordinary contributions and must not be represented as generic validation. The no-write harness is machine-specific research, not a generic dry run. Do not execute hardware flash commands as part of documentation review.

By contributing, you confirm that you have the right to submit the contribution. Licensing scope and third-party legal review remain unresolved; do not claim legal clearance.
