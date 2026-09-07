# Third-party notices

## Project code

The repository's original code is offered under the MIT License in [LICENSE](LICENSE). That license applies to project-authored code and documentation only, to the extent the project has authority to license them.

## User-supplied NVIDIA software and firmware

NVFlash binaries, NVIDIA firmware, VBIOS/ROM images, and vendor documentation are third-party materials. They are not distributed by this repository. Users must obtain and use them lawfully and comply with their applicable licenses and terms.

The scope of rights around patching or operating proprietary tools and firmware has not received definitive legal review. No legal clearance is claimed.

## Research reference and dependencies

[notfromstatefarm/nvflashk](https://github.com/notfromstatefarm/nvflashk) is the Windows behavioral reference credited by this Linux reproduction. Research sample identities and provenance are recorded in [research/NOTES.md](research/NOTES.md); no affiliation or endorsement is implied.

Rust dependencies are pinned in `Cargo.lock` and retain their own licenses. Capstone and pyelftools are development-time verifier dependencies supplied through Nix; they are not bundled in this source release. NVIDIA and GeForce names identify third-party software and hardware and remain their owners' marks.
