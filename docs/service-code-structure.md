# Service Code & File Structure Guide

Use this as a template for implemented services, not as a requirement to create empty files.

## Recommended Python/FastAPI service layout
```text
services/task-service/
├── pyproject.toml
├── Dockerfile
├── README.md
├── .env.example
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
├── src/task_service/
│   ├── main.py                 # FastAPI app and lifespan
│   ├── api/
│   │   ├── router.py           # Combines route modules
│   │   ├── dependencies.py     # Auth/request dependencies
│   │   └── routes/
│   │       ├── health.py       # Health/readiness endpoints
│   │       └── tasks.py        # Thin HTTP endpoints
│   ├── schemas/
│   │   ├── task.py             # Pydantic request/response models
│   │   └── errors.py           # Stable error models
│   ├── domain/
│   │   ├── models.py           # Domain types, if useful
│   │   ├── enums.py
│   │   └── errors.py
│   ├── services/
│   │   └── task_service.py     # Use cases/business rules
│   ├── repositories/
│   │   └── task_repository.py  # Database queries
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   ├── events/
│   │   ├── publisher.py
│   │   └── consumer.py
│   ├── clients/                # Typed clients for other services/providers
│   ├── config.py               # Validated environment settings
│   └── observability.py        # Logs, traces, metrics
└── tests/
    ├── unit/
    ├── integration/
    └── contract/
```

## Responsibilities
| File/folder | Responsibility |
|---|---|
| `main.py` | App setup, middleware, startup/shutdown |
| `api/routes/` | HTTP handling, status codes; keep business logic out |
| `api/dependencies.py` | Request-scoped dependencies and auth context |
| `schemas/` | Validate request/response shapes |
| `domain/` | Core concepts/rules independent of framework where practical |
| `services/` | Use cases and business decisions |
| `repositories/` | Database reads/writes only |
| `db/` | Database engine/session and ORM setup |
| `migrations/` | Versioned schema changes |
| `events/` | Event publishing/consuming |
| `clients/` | Typed external/service API adapters |
| `config.py` | Environment settings and validation |
| `observability.py` | Structured logs, tracing, metrics, correlation IDs |
| `tests/` | Tests organized by scope |

## Request flow
```text
HTTP request -> route + validation -> auth/authorization
             -> service/use case -> repository/client -> response schema
```
Routes should be thin. Business rules belong in services/use cases; database queries belong in repositories. Do not add a layer that only forwards arguments.

## Suggested functions
For `task_service.py`:
- `create_task(...)` — enforce domain rules and create a task.
- `get_task(...)` — retrieve within the caller's authorization scope.
- `list_tasks(...)` — filters and pagination.
- `update_task(...)` — enforce valid state/field transitions.
- `cancel_task(...)` — request cancellation and emit an event if required.

For `task_repository.py`:
- `create(...)`
- `get_by_id(...)`
- `list_for_owner(...)`
- `update(...)`
- `delete_or_archive(...)` — only if product policy permits.

Use descriptive names; avoid vague functions like `process_data()` or `handle_all()`.

## Service capability map
| Service | Typical modules | Main capabilities/functions |
|---|---|---|
| API Gateway/BFF | `routes/`, `auth/`, `clients/`, `middleware/` | Authenticate, rate-limit, route/aggregate client requests |
| Identity & Device | `users/`, `sessions/`, `devices/` | Register/revoke devices, manage sessions |
| Task | `routes/tasks.py`, `task_service.py`, `task_repository.py` | Create/list/update/cancel tasks, deadlines and status |
| Orchestrator | `workflows/`, `executions/`, `workers/`, `state_machine.py` | Start/advance execution, retries, cancellation, outcomes |
| Decision Router | `rules/`, `classifiers/`, `routing.py` | Choose deterministic/fast/reasoning path; never grant permissions |
| Policy & Tool Registry | `policies/`, `tools/`, `approvals/` | Validate tools/arguments, check permissions, require approval |
| Automation/Trigger | `schedules/`, `triggers/`, `workers/` | Schedule and enqueue due work |
| Integration | `providers/`, `oauth/`, `tokens/` | Provider APIs, OAuth lifecycle, token refresh/revocation |
| Knowledge/Memory | `memories/`, `retrieval/`, `consent/` | Store, retrieve, update, delete approved memories |
| File Intelligence | `indexing/`, `extractors/`, `ocr/`, `search/` | Extract, index, and search authorized files |
| Sync | `connectors/`, `sync_jobs/`, `conflicts/` | Track sync, reconcile changes, handle conflicts |
| Web Research | `browser/`, `extractors/`, `summaries/`, `sources/` | Controlled browsing, extraction, sourced summaries |
| Notification | `channels/`, `templates/`, `delivery/` | Format and deliver notifications |
| Audit/Observability | `audit/`, `metrics/`, `tracing/` | Record actions/approvals and operational telemetry |

These are suggestions, not mandatory files. Create modules only when the service needs them.

## Shared packages
- `packages/contracts/`: versioned event schemas and API contracts.
- `packages/python-common/`: genuinely shared utilities only.
- `packages/dart-common/`: shared Dart types/widgets only when useful.
Do not put service-specific business logic or database models in shared packages.

## When to add a file/function
Ask: Does it have a distinct responsibility? Is there already a suitable module? Is reuse real rather than speculative? Is the name clear? Can it be tested? Split files when responsibilities or navigation become difficult—not just due to an arbitrary line count.

## Every service README should document
Purpose/ownership; endpoints and auth; events published/consumed; data ownership; environment variable names; local run/test commands; health endpoint; dependencies and failure behavior.
