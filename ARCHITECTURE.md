# Architecture
## Proposed logical components
The intent contract stores outcome, priorities, operating conditions, constraints, resources and acceptance criteria. A discovery adapter gathers scoped observations. An evidence ledger preserves provenance and time. A capability graph links resources to tested workflows. A planner proposes actions; a consequence evaluator estimates risks and costs. A coordinator grants scoped execution ownership. A verifier checks both action postconditions and mission acceptance.

Information flows from intent and evidence into planning, through consequence review to execution, then back through verification into persistent state. Historical records never silently become current capability assertions.

## Control loop
START → DISCOVER → CHECK → OBSERVE → REMEMBER → UNDERSTAND HUMAN INTENT → MODEL SYSTEM CAPABILITIES → IDENTIFY MISSING REQUIREMENTS → PLAN → EVALUATE CONSEQUENCES → ACT → VERIFY → UPDATE MEMORY → COMPARE RESULTS WITH HUMAN OBJECTIVE → CONTINUE OR COMPLETE.

The [cycle specification](theory/autonomous-engineering-cycle.md) defines stage contracts. COMPLETE requires all mandatory acceptance criteria and no unresolved blocking evidence. PAUSED records the missing information or authority and the exact condition for resuming. A failed action returns to diagnosis and bounded replanning, not automatic repetition.

## Boundaries
Use one logical coordinator even if future workers run in parallel. Separate proposed predictions from observed state. Limit discovery to relevant, authorized probes. Never infer runtime interoperability from installation lists. No component is implemented in GENESIS-1.
