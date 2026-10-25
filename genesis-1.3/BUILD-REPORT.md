# GENESIS-1.3 engineering report

**EXPERIMENTAL DEVELOPER PREVIEW — 0.1.3.dev1.** Real-system mutation remains disabled. Read-only observations and application-owned workspace updates are supported.

## Baseline and continuity
Baseline branch genesis-1.2-developer-preview was clean at 1d14ff1e1c4a5515f6ce711522bb41890b826939. The initial regression run passed 39 tests. GitHub release v0.1.2-dev.1 was checked and confirmed published with uploaded wheel, EXE, ZIP and source assets; compilation alone was not used as publication evidence.

Development uses genesis-1.3-goal-conditioned-awareness. The existing Fact, Reality, Intent, Transition, capability DAG and legacy validator/kernel algorithms are reused. Added modules implement sufficiency, scoped probes and application-state persistence; the CLI adds workspace operations without replacing legacy commands. GENESIS-1, GENESIS-1.1 and GENESIS-1.2 research/evidence and distributions are preserved.

No new package dependency, Python runtime or packager was installed. The existing Python 3.14.9, build/setuptools/wheel and isolated PyInstaller 6.22.3 environment are reused. New artifacts have a distinct version directory under dist/0.1.3.dev1. Global configuration, services, CUDA, GPU drivers, Anaconda, WSL and Docker are outside the adapters.

## Implemented features
ALREADY_SATISFIED is a capability-state result, distinct from REJECTED_UNNECESSARY for an action. It requires a fresh compatible operational path plus resource evidence and includes intent/reality/graph versions, nodes, probe provenance, constraints, time and explanation. Unknown or stale operational evidence returns NEEDS_VERIFICATION. ACTUAL_CAPABILITY_GAP requires blockers across all alternatives in the recorded scope.

The goal-conditioned planner reuses fresh witness paths and scoped observations, deduplicates shared dependencies, avoids unrelated GPU/device/container scans and selects one justified alternative rather than probing every possible route. Costs, deadlines, output limits and unsupported adapters are visible. Safe workers measure runtime/storage or locate bounded metadata candidates; they never run found Java, Gradle, SDK, compiler or adb programs. Operational build/device verification remains unsupported rather than assumed.

Human revisions support add/remove/exclude/include, objective changes and explicit native-to-portable narrowing. Reasons and confirmation are required. Stable identifiers, full history, graph deltas, obsolete actions and stale plans persist in schema-versioned JSON. Atomic replacement and exclusive locks protect ordinary concurrent/interrupted updates. Pending files and locks are not silently promoted or removed.

## Verification and artifacts
The final source regression suite passes 74 tests, retaining all 39 baseline tests. Installed wheel and standalone EXE each pass all nine A-I goal scenarios through 31 CLI process invocations. The earlier 29 distribution checks also pass. The new acceptance evidence includes full input intents, starting reality, graph structure, expected/actual outcomes, provenance, explanations and execution status for each scenario.

Observed outcomes: simulated sufficiency and portable alternatives return ALREADY_SATISFIED; irrelevant GPU/CUDA paths are avoided; Android facts are planned without contacting a device; removing emulator testing increments revision and invalidates the old plan; expired or failed evidence returns NEEDS_VERIFICATION; history and evidence survive new processes. Actual read-only runtime/storage workers succeed in both distributions and their fresh results are reused. The source suite additionally observes a real worker FileNotFoundError against an explicitly nonexistent test-owned path and a bounded timeout; neither becomes global software absence.

No runtime implementation or packaging failure remained in these runs. Review identified two semantic edge cases before finalization: fresh locator observations must be reusable without counting as operational proof, and malformed/target-incompatible facts must not establish capability sufficiency. Regression tests cover both. PyInstaller retains its existing administrator/conda-derived-environment warnings; no environment changes were made to suppress them.

Live runtime evidence is additionally bound to executable/runtime/application-version context, and live storage evidence to the selected volume scope. Reopening a workspace with another application/runtime or volume therefore requires relevant re-verification rather than silently promoting remembered observations. Tests cover these scope changes. Current-state views label expired or context-inapplicable latest records STALE while preserving their original historical classification.

Machine-readable acceptance results in evidence/artifact-acceptance.json are authoritative for the completed wheel and EXE runs. The source transcript is evidence/source-tests.txt. Packaging checks include independent directories, JSON and human output, real worker starts, persistence across process exits, simulated A-I scenario evidence, hashes, archive inspection and ZIP extraction. Artifact byte counts and SHA-256 values are recorded in evidence/artifact-inventory.json and SHA256SUMS.txt after final assembly.

The source suite distinguishes injected failed-probe cases from actual worker failures and timeouts. Distribution case G replays explicitly labeled failed hypothetical evidence; it is not a failed measurement of the workstation's Android capability. Case I performs real runtime/storage probes. No live Android build, phone installation, compiler workflow or GPU capability is claimed.

## Limitations
This is a finite criterion/probe catalog, not natural-language goal inference. The chosen observation route is justified and deduplicated, not proven globally optimal. PATH absence is not global absence. Target compatibility is scoped evidence, not guessed from package names. Fresh cached derived records are recomputed for decisions; older source evidence remains historical.

The application runtime criterion describes the executing Python/embedded runtime, not a separately installed development environment. Live storage is measured in bytes; fixture resources have simulated units. Workers have bounded waits and termination cleanup, but are not a production hostile-code sandbox. Local state is human-trusted and unsigned; atomic replacement is not a power-loss guarantee. The EXE is unsigned and tested on the existing Windows x64 workstation only.

Only read-only observations and application-state writes are enabled. AUTHORIZED never reaches an execution adapter. The original GENESIS-1.1 isolation tests apply only to their source experiment. No energy, human-time, model-behavior, production-readiness or general Windows-security benefit is asserted. No GENESIS-1.4 work is initiated.

GENESIS-1.3 is complete within the documented finite capability/probe catalogue and tested Windows environment. Distribution and repository commit identifiers are recorded by the release tag and final delivery; source hashes and artifact checksums are independently inspectable. Publication occurs only after both distributions pass acceptance, without merging main or replacing older releases.
