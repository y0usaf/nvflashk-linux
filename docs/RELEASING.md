# Release procedure

## Version policy

- `v0.1.0` identifies the **k4 patch output already used for the documented restoration**, with release packaging and output-file safety fixes. The generated binary's pinned SHA-256 is unchanged.
- Future candidates use `vX.Y.Z-rc.N`, starting with positive `N=1`; no leading zeroes. Example: `v0.1.1-rc.1`.
- Both `Cargo.toml` and the root package entry in `Cargo.lock` must contain the exact version, including `-rc.N`. Nix reads its version from Cargo.
- RCs publish as GitHub **prereleases**, explicitly **not latest**. Stable tags publish as non-prereleases/latest. A stable tag is a distribution designation, not a hardware compatibility certification.
- Tags are immutable: never move or reuse a published tag. Fix a failed candidate with the next RC number.

## Prepare and review

1. Set the intended version in Cargo.toml and Cargo.lock, update CHANGELOG.md (also used as release notes), and record the scope/evidence in docs/VALIDATION.md. Do not convert untested hardware into a compatibility claim.
2. Run `nix build`, `nix flake check`, `nix fmt -- --check flake.nix` (or the formatter directly), Rust formatting/Clippy, and an independent code review. CI exercises synthetic unit/CLI/harness/release/archive tests without NVIDIA files or GPU access.
3. When patch bytes, input identity, or output identity change, run `research/verify.py` in `nix develop` against lawfully obtained local input and newly generated output. Compare against prior artifacts when bytes should be unchanged. Never automatically execute generated NVFlash, flash a GPU, or run the machine-specific harness as a release gate.
4. Inspect the complete publication tree and reachable Git history for secrets, personal paths/logs, executables, samples, ROMs and other third-party content; run a secret scanner. Review LICENSE/THIRD_PARTY_NOTICES.md and unresolved licensing questions. Source-only does not imply legal clearance.
5. Commit only reviewed source, ensure the working tree is clean, and push the branch. Wait for its Nix CI check to succeed.

## Tag and publish

For example, after setting both Cargo versions to `0.1.1-rc.1`:

```sh
./scripts/validate-release v0.1.1-rc.1
git tag -a v0.1.1-rc.1 -m '0.1.1 release candidate 1'
git push origin v0.1.1-rc.1
```

The tag triggers `.github/workflows/release.yml`. It checks out the exact tag, validates versions and tag/HEAD identity, runs Nix build/check, scans archive members, creates a deterministic source tarball plus SHA-256 file, then publishes. No NVIDIA executable, firmware, or compiled patcher is uploaded. The archive scanner is an additional gate, not a substitute for a secrets/licensing review.

A manual **Release** workflow run requires an existing tag and defaults to `dry_run=true`: it validates/builds/archives but does not publish. Set false only to publish a tag without an existing release. Rerunning an already-published tag does not overwrite the release.

To test an archive locally at its exact tagged commit:

```sh
./scripts/validate-release v0.1.0
python3 scripts/archive-release.py v0.1.0 /tmp/nvflashk-linux-0.1.0.tar.gz
```

Verify the published tag SHA, release/prerelease/latest flags, attached checksum, and source archive download. Build/check the downloaded or clean-checkout source; a workflow definition alone is not evidence that publishing works.

## Promote an RC

Review changes and feedback since the candidate; retain the limited hardware claims and unresolved sustained-load/legal questions until separately resolved. Change both Cargo versions from `X.Y.Z-rc.N` to `X.Y.Z`, update release notes, rerun the gates, commit, and publish a **new** stable tag. Keep the RC tag and release intact. No new flash is required merely to promote metadata/documentation changes; any new hardware validation is an explicit, separately reviewed activity.
