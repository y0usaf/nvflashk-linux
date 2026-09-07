# Release and validation plan

## Published baseline

- `0.1.0` names the existing k4 output exactly: `082f84b1c80b14c2c0eccb3c41c4bec7f8f5886fa03e533abb87d64ce0f36cfa`.
- The supported input is the pinned Linux x86-64 NVFlash 5.792.0 binary documented in [README.md](README.md).
- No proprietary binary, VBIOS, ROM, recovery image, or machine-specific artifact is distributed.

## Experimental validation

The only reported hardware result is an experimental original-VBIOS restoration on a single RTX 4090. Startup fan spin and repeated readbacks were observed. Sustained cooling, long-duration workloads, and independent compatibility validation remain pending. No compatibility guarantee is made.

The no-write harness is machine-specific research, not a generic dry run. It must not be presented as proof that another card, binary, prompt sequence, or firmware image is safe.

## Recovery boundary

A software path is relevant only if the GPU still enumerates and an independent recovery display or console exists. A non-enumerating or POST-blocking card requires qualified external SPI recovery or hardware repair. Do not improvise hardware procedures.

## Release candidate lifecycle

1. `v0.1.1-rc.1`: publish reproducible patch/build checks, sanitized evidence, and explicit limitations.
2. `v0.1.1`: release only after review of the RC documentation, exact k4 reproducibility, and the unresolved legal/licensing question.

Neither milestone expands hardware support or grants legal clearance.
