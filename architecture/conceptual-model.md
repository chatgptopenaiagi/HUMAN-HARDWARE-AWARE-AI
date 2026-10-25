# Conceptual model
## Entities
An Objective has versioned Requirements and AcceptanceCriteria. A Resource describes hardware, software, code, connectivity or human capacity. A Capability connects prerequisites to a possible workflow. An EvidenceRecord supports or contradicts a claim. A Plan contains Actions with dependencies. An Action yields an Outcome and resource measurements.

Every action references an objective version and requirement. Every accepted criterion references evidence. Every capability references prerequisites, envelope and verification time.

## Invariants
- An installed package does not imply an operational capability.
- A passing action does not imply mission completion.
- A prediction does not update verified state until observed and checked.
- Missing or contradictory evidence cannot satisfy mandatory acceptance.
- Human-authorized revisions preserve earlier intent versions.
- COMPLETE stops execution; PAUSED names the missing condition.

## Proposed interfaces
Discovery returns observations, not permission to modify. Planning returns candidates, not executable authority. Verification returns scoped judgments with evidence. Coordination grants bounded ownership. Persistence records all transitions. These are logical boundaries; implementation technology remains undecided.
