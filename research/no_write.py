#!/usr/bin/env python3
"""Staged, exact-transcript NVFlash test. There is no firmware-write mode."""

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import termios
import time

STOCK = "bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7"
K4 = "082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa"
BLOWER = "eea10264881c38d7f80e2b8caf3f986f0753ec84b424dbc9689b90fc862a7c1d"
FE = "e1939223b7c92d5f00bfe8aa8d7cea5cb0ea5cefc243d93511c3d2a67d22079f"
OVERRIDE = b'Type "YES" to confirm (all caps):'
FINAL = b"Update display adapter firmware?"
LIMIT = 128 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(kit, sys=Path("/sys"), proc=Path("/proc")):
    for name, expected in {"nvflash-stock": STOCK, "nvflashk-k4": K4,
                           "backup.rom": BLOWER, "backup2.rom": BLOWER,
                           "factory-full-1.rom": FE, "factory-full-2.rom": FE}.items():
        require(digest(kit / name) == expected, f"Hash mismatch: {name}")
    modules = {line.split()[0] for line in (proc / "modules").read_text().splitlines()}
    require(not modules.intersection({"nvidia", "nvidia_drm", "nvidia_modeset",
                                      "nvidia_uvm", "nouveau"}), "GPU driver still loaded")
    require("vbios_maintenance=1" in (proc / "cmdline").read_text().split(),
            "Not booted with vbios_maintenance=1")
    devices = sys / "bus/pci/devices"
    gpu = devices / "0000:01:00.0"
    require((gpu / "vendor").read_text().strip() == "0x10de" and
            (gpu / "device").read_text().strip() == "0x2684", "Unexpected GPU identity")
    require(not (gpu / "driver").is_symlink(), "4090 still bound to a driver")
    amd = devices / "0000:6a:00.0/driver"
    require(amd.is_symlink() and amd.resolve().name == "amdgpu", "AMD iGPU not bound to amdgpu")
    nvidia = [p for p in devices.iterdir() if (p / "vendor").read_text().strip() == "0x10de"
              and (p / "class").read_text().strip().startswith("0x03")]
    require(len(nvidia) == 1, "Expected exactly one NVIDIA display adapter")


def dialogue(before, after, board=None):
    if before is not None:
        require(0 < len(before) <= LIMIT, "Invalid pre-override transcript size")
        require(before.rstrip().endswith(OVERRIDE), "Before transcript must end at override prompt")
        require(before.count(OVERRIDE) == 1 and FINAL not in before,
                "Unexpected/reordered prompt before override")
        require(b"PCI Subsystem ID override detected." in before, "Missing PCI override warning")
    if board is not None:
        require(before is not None, "Board transcript requires PCI transcript")
        require(0 < len(board) <= LIMIT and board.rstrip().endswith(OVERRIDE),
                "Board transcript must end at override prompt")
        require(board.count(OVERRIDE) == 1 and FINAL not in board,
                "Unexpected/reordered Board prompt")
        require(b"Overriding the PCI Subsystem ID mismatch." in board and
                b"Board ID override detected." in board, "Missing Board override warning")
    if after is not None:
        require(board is not None, "After transcript requires Board transcript")
        require(0 < len(after) <= LIMIT and after.count(FINAL) == 1,
                "Expected exactly one final update prompt")
        require(OVERRIDE not in after, "Repeated override prompt")
        require(b"Overriding the Board ID mismatch." in after, "Missing Board confirmation status")
        require(b"95.02.47.00.01" in before + after and b"95.02.3C.40.40" in before + after,
                "Missing current/replacement VBIOS identities")
        require(after.rstrip().endswith(b"Press 'y' to confirm (any other key to abort):") or
                after.rstrip().endswith(b"Press 'y' to confirm ('s' to skip, any other key to abort):"),
                "After transcript must end at the final confirmation prompt")


def run(command, log, before=None, after=None, timeout=30, board=None):
    """Review exact PCI and Board prompts separately; EOF at the next unknown
    prompt, or n at the reviewed final prompt. No stdin is forwarded.
    """
    dialogue(before, after, board)
    steps = [(part, answer) for part, answer in
             ((before, b"YES\n"), (board, b"YES\n"), (after, b"n\n"))
             if part is not None]
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[1] &= ~termios.OPOST  # Preserve exact output bytes, including CR/LF.
    attrs[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    # NVFlash reads its final single-key answer from the controlling terminal.
    def controlling_terminal():
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    child = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                             start_new_session=True, close_fds=True, preexec_fn=controlling_terminal)
    os.close(slave)
    stage = 0
    pending = b""
    result = b""
    deadline = time.monotonic() + timeout
    if not steps:
        os.write(master, b"\x04")
    try:
        while True:
            require(time.monotonic() < deadline, "Timeout; no further input sent")
            ready, _, _ = select.select([master], [], [], min(0.2, max(0, deadline-time.monotonic())))
            if not ready:
                continue
            try:
                chunk = os.read(master, 4096)
            except OSError as error:
                if error.errno != 5:  # PTY EOF on Linux
                    raise
                chunk = b""
            if not chunk:
                break
            result += chunk
            log.write(chunk)
            log.flush()
            require(len(result) <= LIMIT, "Output limit exceeded")
            if stage < len(steps):
                expected, answer = steps[stage]
                pending += chunk
                require(expected.startswith(pending), "Transcript drift; no further input sent")
                if pending == expected:
                    if answer == b"n\n":
                        # NVFlash prints the prompt before switching /dev/tty
                        # to single-key mode, flushing queued input. Wait for
                        # that transition; any new output still fails closed.
                        ready, _, _ = select.select([master], [], [], 0.25)
                        require(not ready, "Transcript drift before final abort")
                    os.write(master, answer)
                    stage += 1
                    pending = b""
                    if stage == len(steps) and after is None:
                        os.write(master, b"\x04")
        require(stage == len(steps), "EOF before expected prompt")
        require(b"Nothing changed!" in result, "Missing explicit no-change result")
        child.wait(timeout=max(0.1, deadline-time.monotonic()))
        return result
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        os.close(master)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["preflight", "probe", "pci", "override", "replay"])
    parser.add_argument("kit", type=Path)
    parser.add_argument("--before", type=Path, help="Reviewed exact bytes through the override prompt")
    parser.add_argument("--board", type=Path, help="Reviewed exact bytes after PCI YES through Board prompt")
    parser.add_argument("--after", type=Path, help="Reviewed exact bytes after YES through final prompt")
    parser.add_argument("--log", type=Path, help="New transcript path; never overwritten")
    args = parser.parse_args()
    kit = args.kit.resolve()
    preflight(kit)
    if args.stage == "preflight":
        return
    require(os.geteuid() == 0, "Hardware test requires root")
    require(args.log is not None, "A new --log path is required")
    require((args.before is not None) == (args.stage in {"pci", "override", "replay"}), "Wrong --before for stage")
    require((args.after is not None) == (args.stage == "replay"), "Wrong --after for stage")
    require((args.board is not None) == (args.stage in {"override", "replay"}), "Wrong --board for stage")
    board = args.board.read_bytes() if args.board else None
    before = args.before.read_bytes() if args.before else None
    after = args.after.read_bytes() if args.after else None
    command = [str(kit / "runtime/ld-linux-x86-64.so.2"), "--library-path", str(kit / "runtime"),
               str(kit / "nvflashk-k4"), "--index=0", "--overridesub", str(kit / "backup.rom")]
    with args.log.open("xb") as log:
        result = run(command, log, before, after, board=board)
    if args.stage == "replay":
        require(b"ERROR: Update aborted" in result and b"keyboard failed" not in result,
                "Final negative confirmation not demonstrated")
    if args.stage in {"override", "replay"}:
        require(b"Overriding the Board ID mismatch." in result, "Board ID bypass not demonstrated")
        require(b"Overriding the PCI Subsystem ID mismatch" in result or
                b"Overriding PCI subsystem ID mismatch" in result, "PCI bypass not demonstrated")
        require(FINAL in result, "Final update prompt not reached")
        require(b"95.02.47.00.01" in result and b"95.02.3C.40.40" in result,
                "Current/replacement identity not demonstrated")


if __name__ == "__main__":
    main()
