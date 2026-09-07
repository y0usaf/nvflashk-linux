# Security and recovery

Firmware modification can permanently disable hardware, corrupt identity data, or remove the software recovery path. Use an independent recovery display/console and verified backups. Never treat a build, disassembly result, or no-write harness run as permission to flash.

Software recovery is limited to cards that still enumerate and remain controllable. A non-enumerating or POST-blocking card needs qualified external SPI recovery or hardware repair. Do not improvise voltage, pinout, chip access, or recovery commands.

The no-write harness is machine-specific research, not a generic dry run. It is not a security boundary and provides no compatibility guarantee. Report security issues through [GitHub private vulnerability reporting](https://github.com/y0usaf/nvflashk-linux/security/advisories/new) before public disclosure; do not send proprietary firmware or personal machine logs.

## Patcher filesystem boundary

Run the patcher as an ordinary user in a directory you own and control, not under `sudo` or in a directory writable by other users. Atomic publication prevents replacement of an existing output; it is not a hostile-filesystem security guarantee against another process replacing directory entries. Special permission bits and group/other write bits are stripped from generated output. The patcher does not execute the generated binary.

Only the latest published release is maintained, with no guaranteed response time. For a report, provide the patcher version, reproduction using synthetic files where possible, expected/actual behavior, and sanitized error output. Normal support questions belong in issues; vulnerability details do not.
