# Predictive engineering
## Proposition
Evaluate likely consequences before changing the environment.

## Proposed mechanism
For each candidate action, list prerequisites, version constraints, resource demand, affected components, objective contribution, recovery options and uncertainty. Forecast dependency conflicts, exhaustion, sequencing risks, hardware limits and deviation from the objective.

A prediction record names the event, time horizon, assumptions, confidence basis and observable outcome. Numerical probabilities require a defensible calibration method; otherwise use qualified estimates without invented precision.

## Decision and validation
Choose an action only if its expected contribution and constraints justify its risks. Prefer reversible probes when uncertainty dominates. A recovery plan specifies a checkpoint, rollback conditions and a verification step; rollback success cannot be presumed.

Compare forecasts with actual outcomes, including false alarms and missed failures. Forecasting overhead and excessive caution can outweigh benefits; this remains an empirical question.
