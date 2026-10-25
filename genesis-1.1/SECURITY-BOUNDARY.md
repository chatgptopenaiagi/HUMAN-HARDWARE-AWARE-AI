# Experimental security boundary
## Assets and authority
The governed assets are authoritative JSON state files and their protected directories under experiments/.runtime/run-*/…/protected, and the broker's memory and token. The trusted Python harness creates fixtures, owns intent revisions, injects test faults, validates plans, executes a fixed simulated operation catalog, and verifies results. It is the trusted computing base. A restricted client supplies data proposals only; it receives no shell-execution endpoint and no writable protected handle.

The model itself was not invoked in the experiments. The client stands at the proposal boundary and the bypass tests execute actual OS operations from that client. This is OS-enforced separation inside the stated boundary, not merely a conditional command wrapper.

## Enforced mechanisms
- Protected directories receive an inheritable medium integrity label; the outbox alone receives low integrity and a Users modify ACE.
- CreateRestrictedToken disables privileges except Windows' retained traverse privilege and supplies three restricting SIDs: Users, Everyone and the current logon SID. SetTokenInformation assigns low integrity.
- Windows therefore checks both ordinary and restricting-SID permissions. Mandatory Integrity Control denies writes up to protected state.
- The child is created suspended with bInheritHandles false. It is placed in a Job Object before resuming: one active process, kill on job close, all basic UI restrictions. It cannot leave descendants running after broker protections are restored.
- While the client exists, the broker process DACL denies new real process handles, including query rights that could expose its primary token. The trusted broker retains its existing pseudo handle. Original DACL restoration occurs before leaving the protection context.
- The child environment is an explicit nonsecret allowlist. Existing interpreter files are staged locally with hashed cache validation and no site packages. Source-runtime ACLs remain untouched.

## Tested attacks
Actual attempts cover truncation, append, deletion, replacement, attributes, sibling creation, directory rename, broker termination access, memory-write access, handle duplication, DACL modification, thread creation, primary-token theft and descendant creation. Filesystem denial requires access-denied errors; unrelated errors do not count as successful enforcement. The descendant case observes the configured Windows job quota error. State bytes are compared independently by the broker.

## What is not controlled
Arbitrary administrator or Codex shell commands, a compromised trusted broker, unrelated processes/services, network access, confidentiality of all files, OS exploits, and all possible Windows privilege-escalation methods are outside this experiment. This is not a production sandbox or a global Windows security guarantee. Low integrity does not by itself provide complete isolation.

Trusted test code can modify the simulation directly for setup and fault injection; that is not the restricted executor interface. No actual installation, registry, service, CUDA, driver, Docker, WSL or Anaconda configuration adapter exists.

## Failures found during development
The first privilege-reduced low-integrity preflight allowed a broker termination handle. A later test obtained a primary-token handle when process query access remained available. Both were failed preflights; no destructive termination or elevated-token execution was performed. Expanded process protection, actual restricting SIDs and job confinement were added. Raw diagnostic evidence is retained in experiments/results/development-findings.json. These failures are separate from the final experiment's bypass counts.

The installed PowerShell client failed under the stricter token because a policy registry read was denied. That permission was not changed. The installed Python files were reused in a repository-local runtime copy instead. Missing existing ffi.dll and zlib.dll dependencies were identified and included; no new runtime was downloaded.

## Basis and portability
See Microsoft's [restricted-token documentation](https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens), [CreateRestrictedToken reference](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken), and [Mandatory Integrity Control](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control). These describe the mechanisms; the committed attack evidence establishes the observed behavior here. Token creation privileges, filesystem labels and existing-runtime layouts may differ elsewhere. Setup errors are blockers, not permission to run an unrestricted replacement.
