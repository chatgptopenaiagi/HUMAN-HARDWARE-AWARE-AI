# Human intent intelligence
## Proposition
Maintain a versioned intent contract rather than relying on the most recent local instruction alone. Capture final product, required functions, priorities, operating conditions, budget, available time, constraints and completion evidence.

## Proposed mechanism
Assign each requirement an identifier, mandatory/optional status and observable acceptance test. Link planned actions to requirement identifiers. Record revisions with author, reason and time; never silently rewrite the original objective.

For example, “make my existing notebook produce an offline report” requires offline operation on that notebook, not merely successful compilation elsewhere. Ask for missing acceptance information when it affects a decision; otherwise record a reversible assumption.

## Verification and failure
Review the contract with the human when material ambiguity remains. Flag contradictions and unresolved requirements. A plan without traceable contribution to a requirement needs justification or removal. The hypothesis is that this reduces drift; the cost of maintaining contracts must also be measured.
