#!/usr/bin/env python3
"""Verify the two pinned k4 edits against user-supplied NVFlash binaries."""

import hashlib
import stat
import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86 import X86_OP_IMM
from elftools.elf.elffile import ELFFile

INPUT_SHA256 = "bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7"
OUTPUT_SHA256 = "082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa"
PATCHES = (
    (0x1AABC6, bytes.fromhex("be 7d d5 99 00"), bytes.fromhex("be 13 80 95 00")),
    (0x1A5AF3, bytes.fromhex("0f 84 12 01 00 00"), bytes.fromhex("90 90 90 90 90 90")),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def instructions(path: Path) -> dict[int, object]:
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        text = elf.get_section_by_name(".text")
        if text is None:
            fail(f"{path}: no .text section")
        decoder = Cs(CS_ARCH_X86, CS_MODE_64)
        decoder.detail = True
        return {item.address: item for item in decoder.disasm(text.data(), text["sh_addr"])}


def main() -> None:
    if len(sys.argv) != 3:
        fail(f"usage: {Path(sys.argv[0]).name} STOCK K4")

    stock_path, patched_path = map(Path, sys.argv[1:])
    stock, patched = stock_path.read_bytes(), patched_path.read_bytes()
    if digest(stock) != INPUT_SHA256:
        fail(f"unsupported stock SHA-256: {digest(stock)}")
    if digest(patched) != OUTPUT_SHA256:
        fail(f"unexpected k4 SHA-256: {digest(patched)}")
    if len(stock) != len(patched):
        fail("file size changed")
    expected_mode = stat.S_IMODE(stock_path.stat().st_mode) & ~0o7022
    if expected_mode != stat.S_IMODE(patched_path.stat().st_mode):
        fail("output permissions differ from safe input mode (special and group/other-write bits stripped)")

    expected_changed = set()
    for offset, original, replacement in PATCHES:
        if stock[offset : offset + len(original)] != original:
            fail(f"stock precondition failed at {offset:#x}")
        if patched[offset : offset + len(replacement)] != replacement:
            fail(f"k4 precondition failed at {offset:#x}")
        expected_changed.update(
            offset + index
            for index, (before, after) in enumerate(zip(original, replacement))
            if before != after
        )
    actual_changed = {index for index, pair in enumerate(zip(stock, patched)) if pair[0] != pair[1]}
    if actual_changed != expected_changed:
        fail("bytes outside the pinned changed-byte manifest differ")

    decoded = instructions(patched_path)
    for address in range(0x5A5AF3, 0x5A5AF9):
        item = decoded.get(address)
        if item is None or item.mnemonic != "nop" or item.size != 1:
            fail(f"PCI patch does not decode as six NOPs at {address:#x}")
    alias = decoded.get(0x5AABC6)
    if alias is None or alias.mnemonic != "mov" or alias.size != 5 or alias.op_str != "esi, 0x958013":
        fail("Board option edit is not the expected mov esi, overridesub")
    if stock[0x558013:0x558013 + 12] != b"overridesub\0":
        fail("Board option target is not the original overridesub string")
    print(f"stock: {INPUT_SHA256}")
    print(f"k4:    {OUTPUT_SHA256}")
    print("changed bytes: 9 across 2 pinned instruction spans")
    print("PCI path: 0x5a5af3 -> six NOPs")
    print("Board gate: 0x5aabc6 -> mov esi, 0x958013 (overridesub); confirmation retained")


if __name__ == "__main__":
    main()
