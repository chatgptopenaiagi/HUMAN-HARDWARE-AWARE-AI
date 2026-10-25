# Verification model
## Levels
Inventory verification checks a scoped observation. Capability verification checks an integrated workflow. Action verification checks intended postconditions and relevant regressions. Objective verification checks the complete human acceptance contract.

## Proposed acceptance procedure
Map every mandatory requirement to an observable test, artifact, evaluator and operating envelope. Check artifacts semantically as well as checking command status. Record failures, missing evidence, stale evidence and exceptions. Use independent evaluation when practical; a worker's self-report is evidence to inspect, not final authority.

A mission is COMPLETE only if all mandatory criteria pass under the authorized objective version. A score cannot override a mandatory failure. Optional work remains explicitly optional. A publication failure can coexist with completed local research when the mission contract permits that fallback.

## Recovery
After a failed action, inspect actual state before retrying. Verify rollback rather than assuming it. Preserve failed evidence and uncertainty. Stop or pause when recovery exceeds authorized scope or information is missing. Avoid blanket “all checks passed” claims unsupported by recorded checks.
