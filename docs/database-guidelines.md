# Database Guidelines

## Ownership
- Each service owns its schema, migrations, and data-access code.
- Never query another service's tables directly.
- Cross-service data comes through APIs, events, or a maintained read model.

## Schema changes
- Use versioned migrations; avoid manual production edits.
- Keep migrations reviewable and consider deployment compatibility.
- Back up and verify before destructive changes.

## Modeling
- Use stable IDs, UTC timestamps, constraints, and indexes based on real query patterns.
- Use transactions for atomic changes within one service.
- Do not use cross-service database transactions.

## Privacy
- Store only data needed for a feature.
- Restrict database roles and encrypt sensitive data where appropriate.
- Never store plaintext passwords or expose OAuth tokens to an LLM.
- Define retention and deletion behavior.

## Distributed consistency
Use events, idempotent consumers, and compensating actions. Consider a transactional outbox when an event must match a committed database change.
