# Contracts Package (`packages/contracts`)

This package provides versioned Pydantic schemas for cross-service events, task payloads, approvals, and device actions.

## Structure
- `contracts.events.envelope`: Universal event envelope model (`EventEnvelope`).
- `contracts.tasks`: Task lifecycle domain models, request/response shapes, and task events.
- `contracts.approvals`: Human authorization requests, approval status models, and resolution events.
- `contracts.files`: Local file and directory action schemas for the Windows agent.
