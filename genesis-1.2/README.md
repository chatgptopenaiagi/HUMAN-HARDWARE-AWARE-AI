# Awareness Kernel 0.1.2.dev1

**EXPERIMENTAL DEVELOPER PREVIEW**

Inspect capability graphs, simulated Reality and Intent Snapshots, transition plans and authorization decisions without opening the source repository. The three questions remain: What does the human want? What does the human have? What can the whole system accomplish?

## Install the wheel
Use an existing Python 3.10 or newer (tested on Windows 11 with Python 3.14.9). Create a virtual environment in a location you choose; do not install into Anaconda base:

```powershell
python -m venv .awareness-preview
.\.awareness-preview\Scripts\python.exe -m pip install --no-deps .\human_hardware_awareness_kernel-0.1.2.dev1-py3-none-any.whl
.\.awareness-preview\Scripts\awareness-kernel.exe --version
.\.awareness-preview\Scripts\awareness-kernel.exe selftest
```

The wheel has no third-party runtime dependencies. The source archive is optional for developers rebuilding the package. No repository checkout or live AI connection is needed to use the preview.

## Windows executable
If using the verified Windows x64 release artifact, extract the ZIP and run AwarenessKernel.exe from PowerShell. It includes its runtime and requires no separately installed Python. It is a console application. Windows may present trust prompts for an unsigned experimental executable; no code-signing claim is made.

The following commands work with either awareness-kernel or AwarenessKernel.exe:

```powershell
awareness-kernel --help
awareness-kernel graph --requirement native --format tree
awareness-kernel inspect --scenario android
awareness-kernel simulate --scenario android --operation install --requirement apk --component sdk
awareness-kernel simulate --scenario notebook --operation install --requirement native --component compiler
awareness-kernel simulate --scenario notebook --operation build --requirement native
awareness-kernel selftest
```

Android rejects the redundant SDK; notebook authorizes a feasible compiler proposal but rejects a build without a compiler. The portable scenario reuses an alternative compiler. Workstation rejects CUDA for its CPU report objective. Archive provides another positive-control proposal. --storage adjusts simulated resource units.

## Supported behavior and boundary
POINT A reports capabilities observed in a fresh simulated fixture. POINT B reports its required capabilities. graph returns the authoritative directed graph or a tree projection. inspect includes snapshots, evidence and verification status. simulate returns a plan and validator decision. selftest checks seven expected decisions and unchanged state. JSON output identifies version, experimental status and disabled execution. A valid rejected proposal exits zero because evaluation succeeded; usage errors exit two; failed selftests exit one.

**No proposed action is executed.** AUTHORIZED means the existing validator considers a simulated transition feasible; it is not an execution ticket. Postconditions are NOT_EXECUTED. Each invocation starts a new disposable fixture and removes its temporary files afterward. There is no persistent project state or real workstation inventory in this preview.

The installed/frozen runtime has not inherited the source-checkout isolation claim. Mutation endpoints are deliberately absent from the preview CLI. The original kernel and isolation research remain in source for review; Python imports are trusted developer APIs, not a sandbox. See SECURITY.md and BUILD-REPORT.md.

## Rebuild
Use existing build/setuptools/wheel tools: python -m build --no-isolation. packaging/build.ps1 documents the single-packager EXE build and isolated test setup. Verify published SHA-256 checksums with Get-FileHash before use. The project remains experimental; no production readiness, real package installation, energy savings or model-behavior benefit is claimed. No open-source license is selected by this packaging milestone; repository access and applicable third-party licenses still apply.
