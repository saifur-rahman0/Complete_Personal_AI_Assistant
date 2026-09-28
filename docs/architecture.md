# Architecture

## High-level shape
```text
Flutter apps (Android / Windows)
          |
      API Gateway
          |
  Task | Orchestrator | Identity/Device | Other services
          |
   PostgreSQL (service-owned data)
          |
       RabbitMQ events

Windows agent -- authenticated outbound connection --> backend
```
This is a target architecture, not a mandate to create every service immediately.

## Folders
- `apps/client/`: Unified Flutter client with platform-specific operational roles:
  - *Android (Mobile Companion):* Notifications, task reminders, permission approval cards, and remote command entry.
  - *Windows (Command Center):* Primary workstation UI managing tasks, local LLM integrations, detailed execution inspector, and system settings.
- `services/`: backend capabilities.
- `agents/windows-agent/`: local Windows worker running on the host machine for local file operations, app automation, and local model dispatch.
- `packages/contracts/`: versioned API/event schemas.
- `packages/python-common/`: genuinely shared Python utilities.
- `packages/dart-common/`: shared Dart types/utilities if needed.
- `infrastructure/`: local containers and operations.
- `tests/`: cross-service tests.

## Service boundaries
- **API Gateway/BFF:** client-facing API, authentication integration, request shaping.
- **Identity & Device:** users, sessions, registered devices, device credentials.
- **Task:** task records, status, deadlines, recurrence metadata, cancellation.
- **Orchestrator:** execution lifecycle, workflow coordination, retries, cancellation.
- **Decision Router:** chooses deterministic, fast, or deeper reasoning paths (using fast System One decision models like Laya/Jev for sub-second, low-cost classification and routing); cannot authorize tools.
- **Policy & Tool Registry:** tool definitions, permissions, argument validation, approval requirements.
- **Automation/Trigger:** schedules and event-triggered work.
- **Integration:** external providers and OAuth token ownership.
- **Knowledge/Memory:** user-approved memories and retrieval.
- **File Intelligence:** indexing, metadata, OCR, extraction, search.
- **Sync:** device synchronization and conflict handling.
- **Web Research:** controlled browsing, extraction, summaries, source tracking.
- **Notification:** push/in-app/email delivery.
- **Audit/Observability:** action records, metrics, tracing.

Only implement a service when needed. Start with Gateway + Task + Orchestrator + RabbitMQ and shared contracts.

## Communication and reliability
- REST for synchronous calls; RabbitMQ for asynchronous events.
- Event envelopes include ID, type, version, timestamp, producer, and correlation ID.
- Make consumers idempotent where possible; use bounded retries and dead-letter queues.
- Use an outbox when database commits and event publication must stay consistent.
- Define timeouts; propagate correlation IDs; expose health/readiness endpoints.

## Data and security
Each service owns its tables and migrations. One PostgreSQL server is fine locally, but use separate schemas/roles where practical. Never read/write another service's tables directly.

LLMs propose plans; deterministic policy code authorizes tools. Local agents expose narrow, allowlisted capabilities—not arbitrary shell access.
