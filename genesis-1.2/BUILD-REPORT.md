# GENESIS-1.2 build and verification report

Status: **EXPERIMENTAL DEVELOPER PREVIEW**, version 0.1.2.dev1. Evaluation-only distribution; execution disabled.

## Continuity and environment
Repository E:\HUMAN-HARDWARE-AWARE-AI was clean on genesis-1.1-awareness-kernel at 12ec823e821f34bbc2efcc3b44a783ad6b388186. Work proceeds on genesis-1.2-developer-preview without merging main. GENESIS-1.1 source evidence is not rewritten. The existing kernel, records, recovery and isolation algorithms are unchanged; additions provide packaging and a CLI wrapper.

Windows 11 build 29695, PowerShell 7, Python 3.14.9 and approximately 86.8 GB free on E: were observed. build 1.6.1, setuptools 84.0.0 and wheel 0.48.0 were already installed. The launcher also lists two Python 3.15 paths; neither was needed. No new Python distribution was installed.

No standalone packager was initially available in the active runtime. PyInstaller 6.22.3 and its dependencies were installed only in .preview-work/venv, the same isolated environment used for wheel acceptance. Anaconda base packages were not installed, removed or upgraded. PyInstaller's documented Python compatibility includes the existing runtime: https://pyinstaller.org/en/stable/. A console EXE avoids adding a GUI layer to the existing kernel.

## Deliverables and functional acceptance
- A dependency-free Python wheel with awareness-kernel entry point and python -m awareness_kernel support.
- A Windows x64 standalone console EXE, plus an extraction ZIP containing documentation and runtime notices.
- A source archive built through the standard build backend, with focused tests and packaging scripts.
- Installation instructions, security boundary, automated evidence and SHA256SUMS.txt.

All 39 source tests pass, including the original 32 tests and seven preview tests. Original Windows isolation is retested only in its source context. Twenty-nine installed-artifact checks pass: 14 against the wheel entry point, 14 against the EXE, and one against the installed Python module entry point. Checks cover version/help, graph JSON/tree, snapshots, feasible and rejected proposals, resource limits, selftest and absent execution commands.

Acceptance runs from a fresh directory outside the repository. The wheel imports from the isolated environment's site-packages. The copied EXE runs with PATH reduced to Windows System32 and without PYTHONPATH/PYTHONHOME. No Python installation or repository is on that test PATH. Working-directory files remain unchanged. The EXE embeds Python; the wheel intentionally uses the selected installed interpreter.

Release assembly checks archive contents, wheel source identity, no runtime dependencies, and absence of caches or test environments. It extracts the actual Windows ZIP, checks its EXE hash against the tested binary and runs the extracted selftest. Artifact hashes and byte counts are recorded separately to avoid self-referential checksums. See evidence/artifact-acceptance.json, artifact-inventory.json, unit-tests.txt, source-manifest.json and SHA256SUMS.txt.

## Failures and warnings retained
The first acceptance harness failed on a case-sensitive SystemRoot lookup after successful compilation. The lookup was corrected; subsequent independent acceptance passes. The initial build log retains the failure.

PyInstaller reported the inherited administrator context and a conda-derived virtual environment. No privilege or environment configuration was changed to hide those warnings. Initial --clean used PyInstaller's default per-user cache; subsequent builds explicitly scope that cache under .preview-work. This changed a build cache, not global configuration. Unused crypto, compression, decimal and ctypes modules were excluded from the EXE; actual CLI acceptance was repeated afterward. Remaining optional-platform import warnings are retained in build logs and do not prevent the tested commands.

## Limits and conclusion
The installed/frozen isolation mechanism is unverified, so the CLI provides no mutation or execution endpoint. AUTHORIZED is a feasibility judgment only; postconditions are NOT_EXECUTED. Existing developer APIs remain trusted-harness research code and are not a security boundary. All resources shown by the preview are simulated fixtures, not fresh hardware inventory.

The EXE is unsigned, console-only and tested on this Windows x64 workstation, not a clean second machine. Python versions other than 3.14.9 were not tested. No real package/build, AI inference, GPU action or energy-saving claim is supported. The primary criterion is met for the supported inspection and transition-evaluation functions: a human can install or extract, launch and use the preview outside the source checkout.

Artifacts are published as a prerelease in the existing private repository after verification. The release points to the dedicated development commit; main and prior evidence remain preserved.
