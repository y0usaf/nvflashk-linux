# Reverse-engineering notes

## Current release: 0.1.0 (k4)

Only **k4** is released. It changes the generic confirmation branch at file offset `0x1A5AF3` and the early Board option argument at `0x1AABC6`. It retains two separate mismatch confirmations; the late handlers remain stock. See [the k4 derivation](#k4-remove-the-unnecessary-late-handler-patch) and [validation evidence](../docs/VALIDATION.md).

The k2/k3 sections below are a chronological research record, **not instructions or supported alternatives**. Their incorrect assumptions are retained with subsequent corrections. The current `verify.py` accepts k4 only; earlier verifier results refer to historical versions.

```sh
nix develop --command python research/verify.py /path/to/stock/nvflash /path/to/nvflashk-k4
```

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

These are historical k2 static results, not current hardware claims. The current verifier intentionally rejects k2; use the k4 command at the top of this document.

## Validation boundary

Not verified:

- The k2 Board ID path on hardware
- Any EEPROM write
- GPU-generation compatibility beyond what stock 5.792.0 supports
- Recovery behavior

Treat k2 as experimental. Complete the fail-closed no-write run and prove the live VBIOS unchanged before considering a separately approved manual write.

## Maintenance hardware finding: k2 is insufficient (2026-09-06)

The actual k2 run with `--index=0 --overridesub backup.rom` accepted the PCI
YES and then threw `ERROR: Board ID mismatch.` Fresh stock reads before and
after both match the pinned FE hash. No firmware write occurred.

The earlier claim that the Board path was outside the generic function was
incomplete: the mismatch adjuster first calls that same generic function for
each mismatch, BEFORE reaching the late bit-clear handler patched by k2.
At VA 0x5AABC6 the Board call loads the option string `overrideboard` at
0x99D57D; at 0x5AABE9 it loads mask 4, with the label `Board ID` at 0x95E82B,
and at 0x5AABF9 calls vtable slot 0xA8. The generic function queries the option
at 0x5A5A40 and throws the named mismatch at 0x5A5A55 when it is false. This
precedes the original PCI patch. `--overrideboard` is rejected by the CLI
(parser tested inside a sandbox without GPU devices).

k3 retains both k2 edits and changes ONLY the Board call's option argument:

| Offset | VA | Original | Replacement |
|---|---|---|---|
| 0x1AABC6 | 0x5AABC6 | be 7d d5 99 00 | be 13 80 95 00 |

This is `mov esi, 0x958013`, pointing to the existing `overridesub` string.
The explicit `--overridesub` flag now gates both PCI and Board mismatches.
The Board label, mismatch bit, generic call, and confirmation remain intact.
Other mismatch option arguments are unchanged. The late k2 handler is still
needed to clear the Board bit after the generic acknowledgements.

Expected k3 dialogue has TWO distinct YES confirmations, followed by the final
update question. The no-write harness now reviews exact byte segments before
each response separately, supplies EOF at each exploratory stopping point,
and sends only lowercase n at the reviewed final question. No positive final
confirmation is available. The previous single-YES assumptions are superseded.

k3 SHA-256: `de024e95b1f946f8cb389a55ec790d313ba1d43bb8b6a92368f0c16e533a149f`.
Exactly 13 byte values differ from stock, within three pinned instruction
spans. Stock and historical k2 are retained unchanged. Successful static
checks alone do not establish hardware write readiness.

## k4: remove the unnecessary late-handler patch

k3 reached the final update question with both generic acknowledgement lines
(`Overriding the PCI Subsystem ID mismatch.` and `Overriding the Board ID
mismatch.`), correct FE/current and blower/replacement identities, and EOF
followed by `Nothing changed!`. It did not print the late handler status.

Objdump shows why: after ALL early per-mismatch calls succeed, stock code at
0x5AAE62 zeros the mismatch mask at rbp-0x1F8. Therefore the late Board bit is
already clear on this path. The claim above that the late k2 handler was
still needed is superseded by this complete control-flow evidence.

k4 removes the late-handler change entirely and retains just the generic
confirmation edit at 0x1A5AF3 and the Board option argument at 0x1AABC6.
The original late handlers and every other byte remain stock. There are nine
changed byte values across two spans (six NOPs and three address bytes).

SHA-256: `082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa`.
The required evidence is BOTH actual generic acknowledgement messages and
correct current/replacement metadata at the final update prompt, followed
by explicit abort and identical pre/post EEPROM dumps. No requirement is
relaxed for unexpected prompts: transcripts remain exact-byte matched.
