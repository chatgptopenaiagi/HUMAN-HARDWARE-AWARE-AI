# Resource efficiency
## Proposition
Minimize unnecessary work while preserving correctness, reliability and human requirements.

## Resource ledger
Account for inference tokens, human attention and working hours, CPU/GPU time, peak RAM, disk occupancy, storage writes, energy, bandwidth, repeated installations, duplicate calculations and dependency count. Use measured values where available and label estimates.

## Proposed policy
Check relevant existing resources before installing anything. Cache evidence with explicit invalidation. Reuse artifacts only after compatibility and integrity checks. Stop satisfied missions and bound retries after failed actions. Compare feasible strategies as a vector of costs rather than hiding tradeoffs in a single arbitrary score.

Resource ceilings are constraints, not reasons to skip acceptance verification. Reducing local CPU use by offloading may increase network or remote energy costs. Report boundary choices and unavailable measurements; environmental and economic benefits remain hypotheses.
