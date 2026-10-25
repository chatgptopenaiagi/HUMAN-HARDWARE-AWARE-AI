# Agent coordination
## Problem
Multiple sessions can conflict on files, repeat installations, assume different environments, fragment memory and compete for CPU, GPU, disk or attention. A local worker's success does not prove global success.

## Proposed single logical coordination layer
Maintain one objective contract, task ledger, dependency graph, resource budget and evidence store. Assign scoped work ownership with leases, expiration and fencing tokens. Require workers to publish expected postconditions, touched resources, outputs and failures.

Before a mutation, validate that ownership and state version remain current. Serialize shared environment changes and reject stale writes. Idempotency keys can identify retries, but cannot guarantee an external side effect happened exactly once; reconcile observed state after interruption.

## Parallelism gate
Permit concurrency only for isolated tasks with explicit merge and verification rules and an expected benefit after coordination overhead. Set a concurrency and resource budget. On conflict or coordinator failure, stop affected mutations and reconcile state.

GENESIS-1 uses one existing session and launches no additional agents. This document investigates future coordination only.
