# Security Guidelines

## Identity and access
- Authenticate clients/devices and authorize every sensitive operation server-side.
- Apply least privilege to users, services, devices, OAuth scopes, and filesystem access.
- Keep secrets in environment configuration or a secret manager; never commit them.
- Provide credential rotation and revocation.

## AI and tools
- Treat model output as an untrusted proposal, not authorization.
- Enforce permissions in deterministic policy code.
- Use allowlisted tools and validated arguments; never run arbitrary model-generated shell, PowerShell, SQL, or code.
- Require confirmation for deletion, external sharing/sending, purchases, account changes, and other consequential actions.
- Support cancellation, timeouts, and audit records.

## Files and browser
- Scope filesystem access to approved folders.
- Defend against path traversal and unintended bulk operations.
- Treat web pages, documents, OCR, and retrieved content as untrusted.
- Protect URL fetching/browser tools against SSRF, unsafe redirects, private-network access, and credential leakage.
- Confirm before uploading, sharing, or deleting files.

## Privacy and local agent
- Never send OAuth refresh tokens/passwords to an LLM.
- Redact sensitive data from logs.
- Use authenticated outbound connections for the Windows agent.
- Expose narrow capabilities, not arbitrary command execution.
- Fail closed if authorization cannot be verified.
