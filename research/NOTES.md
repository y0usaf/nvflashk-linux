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

## Linux PCI subsystem mapping

TechPowerUp's archive labelled 5.814 contains Linux version 5.792.0, built September 2022. Raw offsets differ from Windows, but the Linux function at virtual address `0x5A59B4` has the same control-flow sequence and messages:

```text
0x5A5AB8  test r14b,r14b       # override confirmation skipped
0x5A5ABB  je   0x5A5AF0
0x5A5AF0  test r13b,r13b       # override detected
0x5A5AF3  je   0x5A5C0B        # skip stock internal override path
0x5A5AF9  ...                  # override confirmation path
0x5A5C0B  test r12b,r12b       # ordinary dangerous-override path
```

Linux file offset `0x1A5AF3` maps to VA `0x5A5AF3` because `.text` has a `0x400000` load bias. The verified PCI edit remains:

```text
0f 84 12 01 00 00  →  90 90 90 90 90 90
```

## Linux Board ID gate

A hardware no-write run proved that the PCI edit reaches and accepts the subsystem override, then fails separately with `ERROR: Board ID mismatch.` The Board ID path is not part of the function above.

`.eh_frame` FDEs recover these relevant stripped-function boundaries:

| Function | VA range | Role |
|---|---|---|
| Compatibility reporter | `0x5A93B4..0x5AA163` | Reports mismatch-mask bit `0x04` with adapter/image Board IDs |
| Mismatch adjuster | `0x5AA164..0x5AB31B` | Applies NVIDIA's existing per-mismatch override handlers |

Direct string xrefs place `overrideboard` at `0x5AABC6`, `0x5AB008`, and `0x5E07CA`; `Overriding Board ID mismatch` is referenced at `0x5AB094`. The decisive part of the mismatch adjuster is:

```text
0x5AAF69  ... query altdevid, then relaxdevid
0x5AAFF4  test r13b,r13b
0x5AAFF7  je   0x5AB0B6       # skip the complete Board ID handler
0x5AAFFD  ... query overrideboard
0x5AB076  test r14b,r14b
0x5AB079  je   0x5AB0B6       # skip when overrideboard is false
0x5AB07B  test byte [rbp-0x1f8],0x04
0x5AB082  jne  0x5AB08D       # mismatch present → report override
0x5AB084  and  dword [rbp-0x1f8],0xfffffffb
0x5AB094  mov  esi,0x99d662   # "Overriding Board ID mismatch"
0x5AB0B4  jmp  0x5AB084       # clear Board ID mismatch bit
```

The equivalent Windows 5.814 mismatch-adjuster function is `0x140B6FA50..0x140B71211`. Its Board ID block has the same state transitions: it queries `overrideboard` at `0x140B7104B`, conditionally skips at `0x140B710DC`, tests mask bit `0x04` at `0x140B710DE`, reports the override at `0x140B710E9`, and clears the bit at `0x140B71112`. Stock Windows and k1 are byte-identical in this block; k1's earlier generic override edit does not identify the separate Linux Board ID gate.

The guarded k2 Board ID edit replaces the outer skip with one direct jump to NVIDIA's existing bit-test/report/clear handler:

```text
VA 0x5AAFF7, file offset 0x1AAFF7
0f 84 b9 00 00 00             je  0x5AB0B6
e9 7f 00 00 00 90          → jmp 0x5AB07B; nop
```

The target is an instruction boundary in the same `.eh_frame` function. It does not suppress all compatibility processing: the existing handler still tests bit `0x04`, emits NVIDIA's status message only when that mismatch exists, and clears only that bit. The jump also avoids relying on undocumented `altdevid`, `relaxdevid`, or `overrideboard` configuration state.

Important dynamic consequence: `Overriding Board ID mismatch` is a status message, **not a second confirmation prompt**. A no-write harness must send `YES` only for the existing generic/PCI override confirmation, recognize the Board ID status without sending input, then answer the final update prompt with lowercase `n`.

## k2 manifest

| Purpose | File offset | VA | Original | Replacement |
|---|---:|---:|---|---|
| PCI subsystem override | `0x1A5AF3` | `0x5A5AF3` | `0f 84 12 01 00 00` | `90 90 90 90 90 90` |
| Board ID handler | `0x1AAFF7` | `0x5AAFF7` | `0f 84 b9 00 00 00` | `e9 7f 00 00 00 90` |

The two six-byte instruction spans contain ten byte-value changes because two zero displacement bytes are unchanged. Complete k2 SHA-256:

```text
9426d3d05fa2ad0b3a0aa91de56690518f7f83cd26283527baae2e995b08f1d7
```

## Static validation

Verified with GNU `objdump` and independently with Capstone/pyelftools (`research/verify.py`):

- Exact stock and k2 SHA-256 values
- Exact original bytes at both offsets
- Exactly ten changed byte positions, all within the two documented instruction spans
- PCI branch decodes as six NOPs
- Board edit decodes as `jmp 0x5AB07B` plus one NOP
- `0x5AB07B` is an instruction boundary inside `0x5AA164..0x5AB31B`
- ELF size, permissions, headers, and every non-target byte are unchanged
- Generated ELF starts and reports NVFlash 5.792.0

Reproduce the independent check inside `nix develop`:

```sh
python research/verify.py /path/to/stock/nvflash /path/to/nvflashk-k2
```

## Validation boundary

Not verified:

- The k2 Board ID path on hardware
- Any EEPROM write
- GPU-generation compatibility beyond what stock 5.792.0 supports
- Recovery behavior

Treat k2 as experimental. Complete the fail-closed no-write run and prove the live VBIOS unchanged before considering a separately approved manual write.
