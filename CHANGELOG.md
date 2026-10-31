# Changelog

**Experimental, source-only release.** Incompatible firmware can leave a GPU unusable. Evidence is limited to one RTX 4090 original-VBIOS restoration; other hardware, arbitrary cross-flashing, and sustained cooling/workload stability are unverified. No NVIDIA binaries or ROMs are distributed. See [validation scope](https://github.com/y0usaf/nvflashk-linux/blob/main/docs/VALIDATION.md) and [third-party notices](https://github.com/y0usaf/nvflashk-linux/blob/main/THIRD_PARTY_NOTICES.md).

## 0.1.0

- Published the existing k4 exact output as the 0.1.0 baseline.
- Documented the pinned input and output SHA-256 values.
- Recorded the limited single-RTX4090 original-VBIOS restoration evidence.
- Clarified pending sustained cooling/workload validation, recovery limits, and the absence of compatibility guarantees.
- Sanitized public maintenance and validation notes.
- Fixed temporary-file cleanup ownership and stripped special/group-writable/other-writable output permission bits; generated k4 binary contents are unchanged.
- Added CLI version reporting, fail-closed release/version checks, source archive screening, CI, issue templates, and the release-candidate workflow.

## Future release candidates

The next patch release starts at `v0.1.1-rc.1`; this is a naming example, not an already-published candidate. Candidates are GitHub prereleases, never marked latest. Promotion requires the gates in [docs/RELEASING.md](docs/RELEASING.md).
