# Autonomous engineering cycle
The following stage contracts propose one persistent control loop. Evidence and authorized scope flow through every stage. A failed check does not silently advance.

| Stage | Purpose | Inputs | Outputs | Verification condition | Failure condition | Next relationship |
|---|---|---|---|---|---|---|
| START | Establish mission and authority | Human request | Mission boundary | Scope and authority identified | Conflicting or absent authority | DISCOVER |
| DISCOVER | Locate relevant resources | Mission scope | Candidate inventory | Sources scoped to objective | Inaccessible source | CHECK |
| CHECK | Check source quality and freshness | Inventory and existing records | Validation decisions | Evidence relevance and age assessed | Stale or conflicting records unresolved | OBSERVE |
| OBSERVE | Capture current state | Authorized probes | Timestamped observations | Probe method and result retained | Probe fails or exceeds budget | REMEMBER |
| REMEMBER | Persist initial evidence | Observations | Durable evidence references | Write acknowledged and retrievable | Persistence unavailable | UNDERSTAND HUMAN INTENT |
| UNDERSTAND HUMAN INTENT | Formalize desired outcome | Request and constraints | Versioned acceptance contract | Mandatory criteria observable | Material ambiguity | MODEL SYSTEM CAPABILITIES |
| MODEL SYSTEM CAPABILITIES | Map usable combinations | Contract and evidence | Scoped capability graph | Critical integrations verified or unknown | Assumed interoperability | IDENTIFY MISSING REQUIREMENTS |
| IDENTIFY MISSING REQUIREMENTS | Find gaps | Contract and capabilities | Gap and dependency list | Every mandatory criterion traced | Hidden prerequisite | PLAN |
| PLAN | Choose feasible actions | Gaps and budgets | Ordered bounded plan | Actions trace to requirements | No feasible authorized path | EVALUATE CONSEQUENCES |
| EVALUATE CONSEQUENCES | Forecast costs and side effects | Plan and current state | Risk and recovery assessment | Assumptions and limits explicit | Unbounded risk or missing authority | ACT or PLAN |
| ACT | Perform authorized bounded work | Approved-scope plan and ownership | Outcome and action log | Actual actions recorded | Failure, conflict or budget breach | VERIFY |
| VERIFY | Check postconditions and regressions | Outcome and tests | Scoped verification evidence | Semantic checks completed | Failed or missing evidence | UPDATE MEMORY |
| UPDATE MEMORY | Reconcile persistent state | Verification and failures | Updated ledger and invalidations | Updates durable and consistent | Stale derived state | COMPARE RESULTS WITH HUMAN OBJECTIVE |
| COMPARE RESULTS WITH HUMAN OBJECTIVE | Assess mission acceptance | Contract and evidence | Criterion status and remaining gaps | All mandatory criteria evaluated | Local success mistaken for completion | CONTINUE OR COMPLETE |
| CONTINUE OR COMPLETE | Choose next control state | Acceptance and blockers | Continue, complete or paused | Complete only with mandatory passes | Repeated retries without new evidence | DISCOVER or PLAN; terminal COMPLETE; PAUSED |

## Control rules
COMPLETE is terminal for this objective version. PAUSED records a blocker, preserved state and resumption condition when information or authority is unavailable. Resume by refreshing relevant evidence. Failure routes to bounded diagnosis and replanning; after a retry limit, pause with evidence. New human requirements create a new contract version. Discovery may precede full intent formalization, but remains limited to the scope already authorized.
