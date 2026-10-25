# Persistent state
## Proposed record schema
Required fields: record_id, subject, claim, evidence_class, source, method, observed_at, verified_at where applicable, validity_scope, freshness_policy, dependencies, objective_version, supersedes and redaction_status. Predictions also need horizon and assumptions. Actions need status, postconditions, failures and resource measurements.

Example, illustrative only:
```json
{
  "record_id": "example-001",
  "subject": "report-workflow",
  "claim": "Can produce an offline report",
  "evidence_class": "UNKNOWN",
  "source": "pending integration probe",
  "observed_at": null,
  "validity_scope": "specified notebook and input dataset",
  "dependencies": ["runtime-version", "input-access"],
  "objective_version": "v1"
}
```

## Lifecycle
Append evidence events and derive a current view. Retain prior verification after expiry as historical evidence. Invalidate dependent views after environment changes. Represent conflicting records explicitly rather than using whichever was written last.

## Persistence requirements
Atomic updates, interruption recovery, schema versions, backups and access controls are requirements for a future implementation. Exclude secrets and unnecessary identifiers; use references to credential stores. Retention and deletion policies must cover both source events and derived views. A Git documentation repository is not itself a complete operational memory system.
