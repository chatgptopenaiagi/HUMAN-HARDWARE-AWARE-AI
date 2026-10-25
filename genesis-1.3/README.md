# GENESIS-1.3 — Awareness Kernel 0.1.3.dev1

**EXPERIMENTAL DEVELOPER PREVIEW. Real-system mutation and the execution gateway remain disabled.**

Three improvements: evidence-backed ALREADY_SATISFIED decisions; minimal goal-conditioned read-only observation; and human-controlled Intent revisions with persistent history, plan invalidation and capability-graph deltas. No new runtime dependency is required.

## Install or extract
Install human_hardware_awareness_kernel-0.1.3.dev1-py3-none-any.whl into your own virtual environment using an existing Python (requires 3.10+, tested 3.14.9 on Windows 11):

```powershell
python -m venv .awareness-preview
.\.awareness-preview\Scripts\python.exe -m pip install --no-deps .\human_hardware_awareness_kernel-0.1.3.dev1-py3-none-any.whl
.\.awareness-preview\Scripts\awareness-kernel.exe --version
```

Or extract AwarenessKernel-0.1.3.dev1-windows-x64.zip and run .\AwarenessKernel.exe. The EXE includes its Python runtime. Both distributions have the same CLI. Substitute the installed command or EXE in the examples. Download from the private repository prerelease and compare SHA256SUMS.txt before use.

## Start with a hypothetical example
The human supplies the objective and structured criteria. Free text is not automatically translated by an AI model. Built-in scenarios are explicitly hypothetical; they are not observations of your workstation.

```powershell
awareness-kernel workspace-init --workspace .\my-awareness --scenario android-phone --objective "Build APK, test emulator, install on phone"
awareness-kernel assess --workspace .\my-awareness
awareness-kernel probe-plan --workspace .\my-awareness
awareness-kernel plan-create --workspace .\my-awareness --requirement emulator_test --operation build --json
awareness-kernel intent-revise --workspace .\my-awareness --remove emulator_test --objective "Build APK and install on phone" --reason "I no longer require emulator testing" --confirm
awareness-kernel graph-delta --workspace .\my-awareness
awareness-kernel intent-history --workspace .\my-awareness
awareness-kernel intent-diff --workspace .\my-awareness --from-revision 1 --to-revision 2
```

Use the returned plan ID with plan-evaluate --workspace .\my-awareness --plan <plan-id>. It becomes REJECTED_STALE after the revision. The emulator branch is no longer required; the verified simulated APK path remains recognized, and phone connectivity remains NEEDS_VERIFICATION. No actual APK is built or installed.

## Read-only live observation
Select a different workspace explicitly. Fixture evidence cannot be promoted to live measurements:

```powershell
awareness-kernel workspace-init --workspace .\my-live-awareness --scenario live --objective "Verify this application's runtime and available local space" --criterion python_runtime --min-storage 1048576
awareness-kernel probe-plan --workspace .\my-live-awareness
awareness-kernel probe-run --workspace .\my-live-awareness
awareness-kernel probe-results --workspace .\my-live-awareness --json
awareness-kernel workspace-show --workspace .\my-live-awareness --json
```

For this criterion, only the current application runtime and selected workspace volume's free bytes are measured. An EXE's embedded Python is explicitly an application runtime, not proof of an installed developer Python toolchain. Other goals can plan scoped Java/compiler/SDK/Gradle/build-tools/ADB candidate locators. These never invoke the located programs. Gradle wrappers, Java, adb, compilers and SDK commands are not executed. adb device enumeration is unsupported because it can start a daemon.

Runtime evidence is tied to the executable/runtime/application version, and storage evidence to the selected volume. A changed context requires fresh observations even before the ordinary time limit expires. Historical records are retained; expiry never turns remembered data into a current measurement.

Probe plans state what is required, fresh and reusable, stale, unknown, irrelevant or unsupported. Shared facts are deduplicated; a verified alternative path avoids probing the unused alternative. The planner chooses one justified witness/least-unknown viable route, not a mathematical global optimum for every graph. Worker deadlines and output limits bound observation. Fresh locator results are reused as observations; they are not promoted to operational capability evidence.

Live Android/native build capabilities normally remain NEEDS_VERIFICATION because this milestone has no side-effect-free end-to-end build/device adapter. A failed probe or missing PATH candidate never establishes global absence. ACTUAL_CAPABILITY_GAP requires currently verified blockers across every alternative in the recorded scope. No installation is automatically proposed as necessary.

## Commands and records
New commands require --workspace. Their default output is concise text; add --json for full evidence and version references. workspace-show exposes current snapshots and the goal graph; assess reports sufficiency. intent-show/history/diff expose human records. intent-revise supports --add, --remove, --exclude, --include, --objective, and explicit --narrow native=native_portable. Every accepted revision requires a reason and --confirm, preserves prior records and invalidates plans pinned to the prior revision.

Supported structured criteria: apk, smartphone_install, emulator_test, native, native_portable, report, archive and python_runtime. Shared dependencies can remain relevant after removing a top-level criterion if another retained requirement still needs them. --min-storage is a positive lower bound in bytes for live workspaces or clearly labeled simulated units for fixtures; it is not an estimate of arbitrary build size.

The two native criteria currently describe Windows x64 native-binary targets. Operational evidence for another artifact/platform is not interchangeable. Android API levels, compiler ABIs and arbitrary user-defined target platforms are not fully modeled by this finite preview catalogue.

State lives only in the selected directory: awareness-state.json, a temporary exclusive lock, and atomic-write temporary files. It contains schema/version references, snapshots, evidence history, human revisions, plans and events. Reopen it in a new process with workspace-show. A stale lock is reported and never silently removed. Pending interrupted writes are reported but never substituted for committed state. Unknown schemas fail closed. This is not a database, background service, power-loss guarantee or cryptographically authenticated evidence ledger.

The legacy graph/inspect/simulate/selftest commands remain available as disposable GENESIS-1.2-style examples. AUTHORIZED never executes a proposed action. Application-owned files and bounded read-only probe workers are permitted; software installation, registry/driver/service changes and arbitrary AI command execution are not.

## Reproduce
Run python -m unittest discover -v, then packaging/build.ps1 using the existing build environment. It writes version-separated artifacts under dist/0.1.3.dev1 and independently tests the installed wheel and EXE. Run python packaging/assemble_release.py to inspect archives, test ZIP extraction and generate hashes. See SECURITY.md, BUILD-REPORT.md and committed evidence for observed outcomes and limitations. GENESIS-1.2 release artifacts are preserved. GENESIS-1.4 is not initiated.
