# AI workstation
## Hypothetical context
A dedicated NVIDIA GPU is a scenario assumption, not a verified local resource.

## Human objective
Complete a GPU-assisted engineering workflow. The human must specify quality, time and operating constraints before execution.

## What does the human have?
Check device visibility, driver/runtime compatibility, free VRAM, permissions and thermal/power constraints. Treat historical inventory as provisional until relevant checks pass.

## What can the whole system accomplish?
Probe a minimal end-to-end workload before assigning large work; reuse compatible environments. Record untested combinations as UNKNOWN; avoid installing a standard stack by default.

## Acceptance and failure
Check the requested output, actual device execution and resource envelope. An installed CUDA package does not prove device interoperability or enough free VRAM.

## Research comparison
Compare feasible strategies at equal acceptance quality, including setup, supervision, recovery and resource costs. This scenario supplies no measured benefit and authorizes no environment changes.
