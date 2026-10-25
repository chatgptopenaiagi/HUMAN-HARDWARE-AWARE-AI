# Behavioral invariants
| Invariant | Exercised behavior | Test evidence |
|---|---|---|
| INV-001 feasible transition | Missing compiler prevents build and leaves file unchanged; forged resource/postcondition plans rejected | test_INV001_build_without_compiler_cannot_mutate; test_forged_postcondition_and_scope_rejected |
| INV-002 evidence freshness | Expired, future-dated, failed, observed-only or inadequately evidenced facts cannot authorize | test_INV002_expired_evidence_blocks_mutation; test_future_evidence_and_inadequate_method_result_not_fresh |
| INV-003 reuse before install | Existing APK and alternative compiler paths prevent installation; reuse still executes | test_INV003_redundant_sdk_install_rejected_but_reuse_runs; test_existing_alternative_prevents_unneeded_primary_compiler |
| INV-004 re-verification | Instrumented save observes STALE before mutation; fresh evidence follows successful probe; old plan rejected | test_INV004_invalidated_before_reverification |
| INV-005 traceability | CUDA proposal outside CPU report requirement is rejected without probing CUDA; revision removes emulator path | test_INV005_irrelevant_cuda_cannot_reach_state; test_intent_revision_invalidates_old_plan_and_removes_path |
| INV-006 bounded recovery | One rollback attempt restores checkpoint; forced failure marks inconsistent and blocks later writes | test_recovery_restores_and_verifies_checkpoint_once; test_failed_recovery_locks_subsequent_mutations |
| INV-007 enforced execution | Independent restricted process attempts direct file and broker access; OS denies them and bytes remain unchanged | test_INV007_os_denies_bypass_and_preserves_state |

## Interpretation
Passing the tests establishes these bounded behaviors for the fixed adapter and tested Windows configuration. It is not a proof about arbitrary operating-system vulnerabilities or every possible program. A skipped Windows test means enforcement is unverified.

Events preserve validation reasons, evidence references, plans, before/after states, invalidation, postcondition checks and recovery. Probe records preserve failed observations even when current facts are superseded. All scenario capability claims refer only to the simulator.
