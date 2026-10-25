# Measurement framework
Define a mission cohort, observation window, acceptance contract and resource boundary before measurement. Freeze metric definitions before inspecting outcomes.

| Metric | Operational definition | Main limitation |
|---|---|---|
| HUMAN_TIME_RECOVERED | Baseline active human minutes minus assisted active human minutes | Counterfactual and learning effects |
| MISSION_COMPLETION_RATE | Accepted missions / all assigned missions | Report paused, failed and censored counts separately |
| OBJECTIVE_ALIGNMENT | Sum of preregistered weights for satisfied criteria / total criterion weight | Weights are subjective; mandatory failures still prevent completion |
| VERIFIED_CAPABILITY_COVERAGE | Required capabilities with current passing evidence / all required capabilities | Denominator must be fixed per objective version |
| RESOURCE_EFFICIENCY | Accepted outcomes per declared resource unit, separately by resource | Quality and resource tradeoffs resist one scalar |
| UNNECESSARY_OPERATION_RATE | Independently judged avoidable operations / all operations | Requires a published counterfactual classification rubric |
| DUPLICATED_WORK_RATE | Redundant operations repeating valid existing work / all operations | Necessary revalidation must be excluded |
| RECOVERY_TIME | Time from detected failure to restored verified usable state | Separate active human time from elapsed time; unrecovered cases are censored |
| ENERGY_PER_COMPLETED_OBJECTIVE | Total cohort energy, including failures / accepted objectives | Undefined if none complete; report energy and count |
| TOKENS_PER_VERIFIED_OUTCOME | All cohort input/output tokens / accepted objectives | Include retries and coordination; missing provider telemetry must be disclosed |

## Instrumentation
Use monotonic elapsed timers, human activity diaries, versioned action logs, token telemetry and available energy measurement. Separate measured energy from modeled estimates. CPU/GPU time, peak RAM, bytes written, network bytes and disk occupancy have distinct units and boundaries.

Report sample sizes, distributions, uncertainty, missing data, failed attempts and acceptance quality. Avoid invented precision and aggregation across incompatible task mixes. No metric values have been collected for the proposed architecture.
