# Hardware awareness
## Proposition
Execution strategy should reflect the resources actually available to this human. Inventory can include CPUs, GPUs, memory, storage, battery/power limits, smartphones, tablets, notebooks, workstations and remote systems.

## Proposed mechanism
Record device identity at a privacy-preserving scope, OS and runtime versions, available capacity, observation time and probe method. Distinguish installed capacity from currently free resources, and ownership from permission to use. Add network, installed software, models, code, virtualization, human experience and available time when relevant.

A historical GPU record does not prove the driver, runtime or device is usable now. Refresh volatile facts before consequential decisions; invalidate dependent capabilities after relevant changes.

## Limits
Collect only objective-relevant facts. Discovery itself consumes time and may expose sensitive identifiers. A hardware specification is evidence of potential, while an objective-relevant probe establishes bounded operational capability. No hardware beyond the recorded GENESIS-1 preflight has been verified.
