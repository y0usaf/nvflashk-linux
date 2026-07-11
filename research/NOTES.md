# Reverse-engineering notes

## Reference provenance

| Sample | SHA-256 | Source |
|---|---|---|
| Windows NVFlash 5.814.0 x64 | `7da95cb255db9674beda2228e2baa6573f40434e3f82d2f665a80f716d3c7b09` | FileHorse mirror of the original 5.814 archive |
| Windows nvflashk 5.814.0.k1 | `8377ce3c5def44c3c3ec37856fccf3ab1dbfe524b8204d8c1d8ffb1781abc8f6` | notfromstatefarm/nvflashk GitHub release |
| Linux NVFlash x86-64 5.792.0 | `bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7` | TechPowerUp download ID 2271, archive labelled 5.814 |

Samples are proprietary and excluded by `.gitignore`.

## Confirmed Windows changes

The stock and k1 PE files have identical length. Most differences are message strings/signature data. Two executable-code edits occur in the same function:

1. File offset `0xB6E33A` (VA `0x140B6EF3A`): five-byte `call` plus its alignment NOP → six NOPs. This is an output-formatting call immediately before the override-state tests; it does not control the bypass.
2. File offset `0xB6E39C` (VA `0x140B6EF9C`): `0f 84 5f 01 00 00` (`je +0x15f`) → six NOPs. This makes NVIDIA's existing override-confirmation path unconditional.

The second edit is the behavioral nvflashk change. The function contains the stock strings `override confirmation skipped`, `override detected`, and `You are intending to override`, which make its branches identifiable across builds.

## Linux mapping

TechPowerUp's archive labelled 5.814 contains Linux version 5.792.0, built September 2022. Raw offsets differ from Windows, but the Linux function at virtual address `0x5A59B4` has the same control-flow sequence and messages:

```text
0x5A5AB8  test r14b,r14b       # override confirmation skipped
0x5A5ABB  je   0x5A5AF0
0x5A5AF0  test r13b,r13b       # override detected
0x5A5AF3  je   0x5A5C0B        # skip stock internal override path
0x5A5AF9  ...                  # override confirmation path
0x5A5C0B  test r12b,r12b       # ordinary dangerous-override path
```

Linux file offset `0x1A5AF3` maps to virtual address `0x5A5AF3` because `.text` has a `0x400000` load bias. The verified patch is:

```text
0f 84 12 01 00 00  →  90 90 90 90 90 90
```

This is the semantic equivalent of Windows edit 2. The output differs from the input at exactly six bytes and has SHA-256 `06508cc681069d295f9006bdd1179f207fcf94f890a7927eb437af918850e221`.

## Validation boundary

Verified:

- Exact input SHA-256 and original instruction bytes
- ELF still starts and reports NVFlash 5.792.0
- Exactly six bytes change
- Patched disassembly falls through into NVIDIA's existing `override detected` path
- Reproducible Nix build and unit tests

Not verified:

- A real mismatched-ROM check or EEPROM write
- GPU-generation compatibility beyond what stock 5.792.0 supports
- Recovery behavior

Treat the generated binary as experimental until hardware validation is completed with a factory-ROM backup and an independent recovery GPU/dual BIOS.
