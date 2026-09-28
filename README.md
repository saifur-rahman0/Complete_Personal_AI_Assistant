# AI Workforce — Autonomous Digital Employees

A personal assistant platform for delegating tasks to AI agents across devices, with human authorization and auditable execution.

## Planned stack
- Client: Flutter + Dart (Android and Windows)
- Backend: Python + FastAPI microservices
- Local Windows agent: Python
- Data: PostgreSQL; pgvector if needed
- Async messaging: RabbitMQ
- Local development: Docker Compose
- Browser automation: Playwright behind explicit policy controls
- First cloud integration: Google Drive OAuth with least-privilege scopes

## Repository map
- `apps/client/` — Unified Flutter client (Android & Windows interfaces)
- `services/` — backend microservices
- `agents/` — device-side workers
- `packages/` — shared contracts and small reusable libraries
- `infrastructure/` — Docker, broker, database, operations
- `tests/` — integration, contract, and end-to-end tests
- `docs/` — architecture and engineering guidance

## Development approach
Start with the API gateway, task service, orchestrator, shared event contracts, and local infrastructure. Add other services when needed; do not build every planned service as an empty shell.

## Safety
- Use least privilege and scoped permissions.
- Keep secrets out of source control, prompts, and logs.
- Require approval for destructive or consequential actions.
- Maintain audit records for actions and approvals.
- Support cancellation and recovery where feasible.
- LLMs cannot bypass deterministic policy/authorization.
