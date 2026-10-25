# GENESIS-1.1 engineering report
## Repository continuity
Repository: chatgptopenaiagi/HUMAN-HARDWARE-AWARE-AI. Local workspace: E:\HUMAN-HARDWARE-AWARE-AI. Historical baseline: 6624bf63daf9435287f0c1cd265b7170015bcde4. Development branch: genesis-1.1-awareness-kernel. The repository was clean at the baseline; no Git lock or repository-specific instruction file was found. Existing Codex process observations cannot rule out every concurrent process; no unexpected file changes were observed. No history reset was used. Main is not merged.

## Implemented components
Three versioned JSON-serializable record models; evidence labels and TTL freshness; directed capability graph with shared storage and primary/portable compiler alternatives; objective-conditioned probes; six validator decisions; fixed simulated action adapter; OS-restricted proposer; broker gateway; JSONL action/probe evidence; one-attempt checkpoint recovery and inconsistent-state lockout.

Reality facts carry source method/context, observation time, result, exit status, scope and evidence ID. Plans pin reality, intent and graph versions. Obsolete intent plans fail. Material mutations mark affected facts stale before modifying state and re-probe afterward. Unrelated stale GPU information is neither required nor refreshed for a compiler objective. Presence and operational capability use separate probes.

## Experimental isolation
Restricted low-integrity primary token with three restricting SIDs, medium-integrity protected state, low outbox, no inherited handles, temporary broker-process DACL protection, and a one-process Windows Job Object. Only this test harness's process security and repository-local disposable files are changed. Installed runtime files are reused locally because their source ACL prevents restricted access; no runtime is installed or reconfigured. See SECURITY-BOUNDARY.md for the exact trusted base and exclusions.

## Observed outcomes
The final fixed scenario run records 20 proposals: 16 necessary, 3 unnecessary, 1 obsolete. There are 14 correct authorizations, 6 correct rejections, zero false authorizations, zero false rejections, and zero wrong rejection reasons. Eleven authorized actions execute and pass verification; three authorized actions suffer deliberate faults.

All seven functional scenario variants except the deliberately failed-recovery variant complete. Fourteen final bypass attempts are denied with unchanged protected state. Two recoveries restore verified checkpoints; one deliberately failed recovery leaves an inconsistent locked environment. Initial diagnostic access weaknesses are preserved separately and are not concealed in the final counts.

All seven invariants have behavioral tests. Graph tests additionally show a verified portable alternative prevents unnecessary installation of the primary compiler. Intent revision increments and excludes the emulator step. Freshness tests cover expiry, inadequate evidence, failed probes and irrelevant stale facts.

## Reproduction and evidence
Run python -m unittest discover -v, then python experiments/run_genesis_1_1.py. The runner creates new disposable state; published result files are regenerated rather than appended to earlier runs. Unit tests use a separate result directory and do not replace the committed experiment run.

Review results/genesis-1.1/summary.json and the adjacent complete action, probe, client, snapshot, tree, runtime manifest and bypass records. Timing is a small local diagnostic, not a benchmark. The source hash manifest identifies implementation files used for the result set; final commit and push SHA are reported after repository verification.

## Model independence and scientific conclusion
A deterministic client can propose unnecessary actions without any reuse instruction, and the broker rejects them before changing protected state. Necessary simulated changes are also authorized and verified. The unrestricted mechanical control performs the injected redundant SDK change on a separate writable state file.

This supports the proposition that policy and evidence can enforce selective simulated execution independently of proposal cooperation. It does not establish the frequency of unnecessary proposals by a neutral model: no genuine model-behavior trial was conducted. It does not establish real hardware compatibility, real package-management correctness, real APK generation, energy savings or recovered human time.

GENESIS-1.1 is complete for the declared deterministic simulator and tested isolation boundary. Generalized security, model-behavior effects and real-environment effectiveness remain unvalidated. GENESIS-2 has not started.
