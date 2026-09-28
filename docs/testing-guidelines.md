# Testing Guidelines

## Test layers
- **Unit:** business rules, validation, state transitions, policy decisions.
- **Integration:** repositories, database, broker, external adapters.
- **Contract:** API and event compatibility.
- **End-to-end:** critical user journeys.
- **Security:** authorization, invalid input, path traversal, prompt-injection boundaries, approval enforcement.

## Expectations
- Add tests for new behavior and bug fixes.
- Test success and important failure paths.
- Keep unit tests deterministic.
- Use disposable test databases/queues and no production credentials.
- Test duplicate event delivery and retries.
- Verify unauthorized/unapproved actions are rejected.

## Before completion
Run relevant tests, formatter, linter, and type checks. Report exactly what ran, results, and any checks not run.
