# Developer-preview execution boundary

The existing GENESIS-1.1 kernel, validator, recovery and Windows isolation implementation are preserved. Packaging changes entry points, executable identity and installed layout; GENESIS-1.1's source-checkout gateway relies on repository-relative paths and a reusable interpreter. Its original enforcement evidence does not automatically apply to a wheel or frozen executable.

Both preview distributions therefore expose **inspection and evaluation only**. There is no execute, shell, command-string, package-manager or mutation switch. simulate calls the existing plan and validate methods, never submit. Temporary fixture initialization writes only disposable JSON files, which are removed afterward; proposed state transitions never execute. Decisions explicitly report execution_enabled false, DISABLED_IN_DISTRIBUTION and postconditions NOT_EXECUTED.

Automated checks patch submit to raise if called, evaluate necessary and unnecessary proposals, reject unsupported command-line operations, verify unchanged fixture state, and repeat those acceptance checks against the installed wheel and EXE outside the checkout. Original Windows isolation tests are repeated from source and reported separately. They are not represented as packaged-isolation results.

The Python wheel retains existing research modules for developer review. A developer importing Kernel and calling its trusted-harness APIs is outside the preview CLI boundary; Python is not an access-control sandbox. Arbitrary Codex commands, administrator actions and modified application code are not governed. The EXE imports the evaluation CLI and omits unused isolation modules through normal dependency collection.

No real installation adapter or AI inference endpoint exists. CUDA, drivers, Anaconda environments, WSL, Docker, services and the registry are not modified by preview operations. No stronger execution-security claim is made. Future execution support requires a separately authorized adapter and isolation verification in its distributed form.
