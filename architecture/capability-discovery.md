# Capability discovery
## Proposed protocol
Start from requirements and ask which capabilities are necessary. Reuse fresh evidence, inspect only relevant inventory, then perform the smallest authorized integration probe where uncertainty affects the plan.

Each probe specifies prerequisites, expected output, timeout, resource budget, side effects and cleanup. Record command or method, versions, time, exit result and semantic output check. A process exit code alone is insufficient when the desired artifact is missing.

## Capability record
Store capability ID, workflow, participating resources, compatibility assumptions, verification evidence, scope, freshness policy and invalidation triggers. Network reachability, authentication and resource availability can change independently of installed versions.

## Failure handling
Classify absence, denied access, incompatibility, transient failure and unknown cause separately. Bound retries and retain evidence. A failed probe disproves only the tested configuration, not all possible implementations. No exploratory installation is implied by discovery.
