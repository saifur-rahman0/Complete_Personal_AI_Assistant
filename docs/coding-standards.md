# Coding Standards

## General
- Optimize for readability; keep functions focused and names descriptive.
- Prefer explicit control flow and avoid hidden side effects.
- Avoid premature abstractions, giant files, and needless one-function files.
- Comments explain intent or non-obvious constraints.

## Python
- Type-hint public functions and domain objects.
- Use Pydantic for request/response/config validation.
- Keep HTTP routes thin; separate business logic and persistence.
- Inject database sessions and external clients.
- Use structured logging without secrets.
- Do not block the async event loop.
- Use the repository's chosen formatter, linter, and type checker consistently.

## Flutter/Dart
- Separate presentation, application/state logic, and data access.
- Keep widgets focused; move complex behavior into controllers/services.
- Model loading, empty, success, and error states.
- Do not put secrets or business rules in widgets.

## APIs/events
- Validate at boundaries; use stable error shapes.
- Use UTC timestamps and consistent naming.
- Version breaking changes explicitly.
- Keep events small; reference authorized file IDs rather than embedding large files.

## File organization
Organize by capability. Avoid giant `utils.py`, `services.py`, or `models.py`. Do not add layers that only forward calls without value.
