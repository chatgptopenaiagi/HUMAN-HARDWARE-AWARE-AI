# GENESIS-1.1: evidence-backed Awareness Kernel
**What does the human want? What does the human have? What can the whole system accomplish?**

This prototype separates human intent, observed simulated reality, capability paths, proposals, authorization and verified results. It demonstrates selective execution of a small fixed operation catalog against disposable JSON resources. It does not install packages or build real APKs.

## Reproduce
From the repository root in the existing Windows environment:
```powershell
python -m unittest discover -v
python experiments/run_genesis_1_1.py
```

Use an existing compatible Python (tested: 3.14.9) on Windows/NTFS. No pip packages are required. The standard-library broker uses existing Windows APIs and icacls. It stages a reusable copy of the existing interpreter and standard library under experiments/.runtime because the source interpreter's user-only ACL prevents a genuinely restricted client from loading it. No installed environment, registry or global configuration is changed.

The client runs with a restricted low-integrity primary token, no inherited handles, and a one-process Windows Job Object. Only the higher-integrity trusted broker writes authoritative simulation state. If isolation setup fails, reproduction fails; it does not fall back to unrestricted execution. Non-Windows unit tests can check logic but cannot verify INV-007.

## Implementation
[records.py](../awareness_kernel/records.py) contains versioned records, scoped evidence and the graph. [kernel.py](../awareness_kernel/kernel.py) contains the simulator adapter, validator, gateway, verification, logging and recovery. [windows_isolation.py](../awareness_kernel/windows_isolation.py) supplies OS enforcement; [proposer.py](../awareness_kernel/proposer.py) is the restricted client.

The graph is authoritative; its tree projection displays shared references. The primary and portable compiler paths share one storage node. Software-presence and operational probes remain distinct records. Hardware storage and privileges in scenario decisions are simulated values, not workstation measurements.

## Review
Read [contract](EXPERIMENTAL-CONTRACT.md), [security boundary](SECURITY-BOUNDARY.md), [invariants](INVARIANTS.md), [measurement plan](MEASUREMENT-PLAN.md), [results](RESULTS.md) and the [full report](../experiments/GENESIS-1.1-REPORT.md). Inspect JSON artifacts under experiments/results/genesis-1.1. GENESIS-1 research remains intact; GENESIS-2 is not initiated.
