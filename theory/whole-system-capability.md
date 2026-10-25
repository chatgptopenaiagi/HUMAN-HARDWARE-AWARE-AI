# Whole-system capability
## Proposition
A system's useful capability depends on relationships among components, not just their presence.

## Proposed mechanism
Represent a capability as an outcome, prerequisite resources, compatible versions, authority, operating envelope and verification evidence. Distinguish unavailable, unverified, verified-within-envelope and invalidated states.

Windows + WSL + CUDA + Anaconda + Docker + Codex is an illustrative composition, not a requirement or a claim about this machine. A meaningful probe would follow the actual workflow across relevant boundaries, verify its output, and record limits. Testing each component independently does not establish the combined workflow.

## Decision rule
Prefer the smallest existing composition that satisfies acceptance criteria. If a capability is unverified, budget a bounded probe before depending on it. If a prerequisite changes, invalidate affected edges and recheck only what matters. Measure whether integration probing saves more effort than it consumes.
