# Validation boundary and hardware evidence

## Release identity

`0.1.0` names the patch transformation previously called **k4**, not a new firmware write. Release packaging, CLI reporting, and filesystem safety changes do not change the generated NVFlash bytes.

| Artifact | SHA-256 |
|---|---|
| Supported stock Linux x86-64 NVFlash 5.792.0 | `bc36918546a749650a1a28cfd990a506a531b77529b57a7f119ad214563bc7e7` |
| Generated k4 / 0.1.0 NVFlash | `082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa` |
| Original blower VBIOS backup | `eea10264881c38d7f80e2b8caf3f986f0753ec84b424dbc9689b90fc862a7c1d` |
| Installed EEPROM readback | `0faa35a73299534ed406fdc96c0b62c66131598e0930bb589102df3836459632` |

These are identities, not download links or firmware recommendations. No proprietary artifacts are distributed.

## Observed case: single blower RTX 4090 restoration

Saved local evidence from the original restoration was inspected read-only during release preparation:

- The recorded command used `nvflashk-k4`; the retained binary matches the output hash above. The recorded exit status is `0`.
- Two immediate post-write dumps and two post-reboot dumps independently hash to the installed EEPROM identity above. Each is 2,048,000 bytes.
- Saved post-reboot metadata reports `95.02.3C.40.40`, project `G139-0332`, Board ID `0475`, and subsystem `10DE:16F3`.
- Startup blower spin was reported by the operator; this is not an instrumented sustained cooling measurement.
- The installed dump differs from the source backup at 377 byte positions; 300 of those retain the prior EEPROM byte. Full semantic classification of these differences is unresolved. Whole-file identity to the source ROM is **not** claimed.

Raw machine logs, ROMs, and recovery-kit contents remain private. This is a maintainer case report backed by locally inspected evidence, not an independently reproduced hardware trial.

## What checks do and do not prove

**Build/static checks** establish exact input/output identities, instruction preconditions, and unchanged non-target bytes. `research/verify.py` uses Capstone/pyelftools independently of the Rust patcher to check the instruction manifest. Automated PTY tests exercise the research harness against simulated prompts, not real hardware.

**Hardware evidence** establishes only the observed restoration and repeated readbacks on this card. Sustained cooling, normal-driver telemetry, light and extended workload stability, other boards, and other firmware combinations remain unverified. A matching device ID, successful mismatch override, or final confirmation prompt is not evidence of electrical or thermal compatibility.

`research/no_write.py` is machine-specific research for a reviewed environment and transcript. It is not a generic dry run and does not authorize or automate a write. No hardware command is part of release validation.

## Optional follow-up on the already-restored card

No further flash is needed to close the operational evidence gap. The operator can record normal-driver recognition, idle temperature/fan telemetry, then a cautious light workload while watching cooling and display stability. Stop on abnormal temperature, missing expected cooling, artifacts, or instability. Record duration, workload, driver and kernel versions, and sanitized measurements; do not claim success until observed. This checklist does not establish safety for other cards.
