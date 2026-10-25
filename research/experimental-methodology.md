# Experimental methodology
## Design
Preregister questions, task cohort, hardware classes, acceptance tests, baselines, resource limits, exclusion rules and analysis. Compare a conventional workflow with the proposed integrated workflow using matched tasks and counterbalanced order. Keep model/tool versions and permissions comparable; record unavoidable changes.

## Conditions and ablations
Separate intent preservation, capability discovery, persistent memory, forecasting and coordination. Ablate one mechanism at a time where feasible. Include short tasks where overhead could dominate, stale-state tasks, constrained hardware and recovery tasks.

## Procedure
1. Record scoped starting state and permitted resources.
2. Establish an independent acceptance test and measurement boundary.
3. Execute the assigned condition with action, failure and resource logs.
4. Apply the same acceptance evaluation regardless of condition.
5. Retain failed, paused and aborted runs with reasons.
6. Compare paired outcomes and uncertainty; report deviations from protocol.

## Validity and ethics
Account for operator experience, learning, network variation, task difficulty, cache warmth and subjective duplication judgments. Use blinded artifact review where possible. Protect credentials and personal inventory. Obtain authorization before changes and provide bounded recovery.

A documentation preflight is not a controlled experiment. No benchmark run is included in GENESIS-1.
