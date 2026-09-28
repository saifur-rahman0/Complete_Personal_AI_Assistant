# Project Memory: AI Workforce — Autonomous Digital Employees

## 1. Project Goal & Assistant Vision
Build a personal "Jarvis-like" AI assistant platform for delegating tasks from phone (Android) or laptop (Windows). Core capabilities include:
- Cross-device task delegation and tracking from phone and laptop.
- Local folder and file management across devices.
- Web scraping and structured web research.
- Contextual memory and task reminders.
- Windows application/service interaction via a dedicated local agent worker.
- Strict human authorization for consequential actions, least privilege, and full auditability.

## 2. Confirmed Technology & Architecture Decisions
- **Client Architecture & Workload Division (`apps/client/`):**
  - *Android (Mobile Companion):* Dedicated lightweight profile strictly for receiving push/in-app notifications, managing task reminders, presenting human permission approval cards, and submitting quick commands on the go. Does not run heavy local LLM inference or background workers.
  - *Windows (Workstation Hub & Command Center):* Primary workstation UI interacting directly with local LLMs, full task execution views, and advanced system controls.
- **Local Model Execution & Worker (Windows):** Windows hosts both the local LLM inference runtime (Ollama/vLLM/local runtimes) and the dedicated Python worker (`agents/windows-agent/`) for local file and app automation.
- **Backend Microservices:** Python + FastAPI (REST endpoints for synchronous APIs).
- **Interaction Mode:** Text-first command & chat interface in the Flutter client (voice input deferred to later iteration).
- **First Automated Milestone (Option A):** Windows local file & folder management (searching, organizing, sorting, and safely moving files via the Windows agent).
- **Local Windows Worker:** Dedicated Python daemon (`agents/windows-agent/`) running exclusively on the user's Windows machine. Communicates via authenticated outbound connection to the backend. Strictly isolated from the Flutter UI.
- **Fast Low-Cost Decision Routing:** Decision Router leverages System One classification models (Laya open-source weights for local inference, or Jev hosted API) to deliver sub-second, low-cost intent classification, fast-path vs. deep-reasoning routing, and policy checks before invoking heavier LLMs.
- **Data Persistence:** PostgreSQL with per-service schema ownership and versioned migrations (Alembic); `pgvector` when vector memory is introduced. No direct cross-service database queries.
- **Async Messaging:** RabbitMQ for decoupled events with typed envelopes (ID, type, version, timestamp, producer, correlation ID), idempotency, retries, dead-letter handling, and transactional outbox where necessary.
- **Development Environment:** Docker Compose for local services (PostgreSQL, RabbitMQ).
- **Automation & Integrations:** Playwright browser automation gated by explicit policy; Google Drive OAuth with least-privilege scopes as the initial cloud integration.
- **Core Starting Scope:** API Gateway/BFF + Task Service + Orchestrator + Shared Contracts (`packages/contracts/`) + Local Infrastructure.

## 3. Current Implementation Status
- **Status:** Initial foundations & documentation stage.
- **Existing Files:**
  - `AGENTS.md` (Operational instructions and safety rules)
  - `README.md` (Project overview and architectural map)
  - `docs/architecture.md` (High-level system topology, service boundaries, and messaging model)
  - `docs/coding-standards.md` (Readability, typing, boundary validation, and separation of concerns)
  - `docs/database-guidelines.md` (Service data ownership, migrations, transactions, and privacy)
  - `docs/security-guidelines.md` (Least privilege, AI sandboxing, human approval, and credential safety)
  - `docs/service-code-structure.md` (Standard FastAPI service directory layout and capability map)
  - `docs/testing-guidelines.md` (Unit, integration, contract, E2E, and security test standards)
  - `memory.md` (Persistent working memory tracking status, decisions, and roadmap)
- **Pending Implementation:** No services, applications, shared packages, or infrastructure configs have been scaffolded yet.

## 4. Completed Milestones
- **Milestone 0: Architecture & Foundation Review**
  - Inspected existing codebase and documentation.
  - Reconciled technical decisions, architectural patterns, and safety constraints.
  - Initialized persistent working memory (`memory.md`).
- **Milestone 1: Client & Worker Architecture Alignment**
  - Unified Android and Windows client interfaces into a single cross-platform Flutter application (`apps/client/`).
  - Affirmed separation between Flutter desktop UI and the Python local execution worker (`agents/windows-agent/`).
  - Aligned core system capabilities with the Jarvis-style personal assistant vision.
- **Milestone 2: Execution Priorities & Decision Routing Strategy**
  - Selected text-first command interaction for initial phases.
  - Selected Option A (Windows local file & folder management) as the first end-to-end automation target.
  - Confirmed local worker exclusivity to Windows PC.
  - Adopted System One classification (Laya / Jev) for low-cost, fast decision routing.
- **Milestone 3: Client Role Specialization & Local LLM Topology**
  - Configured Android app as lightweight companion dedicated to notifications, reminders, and approval cards.
  - Designated Windows machine as the primary workstation hub running local LLMs and task executions.

## 5. Important File & Folder Locations
- `AGENTS.md` — Agent rules, principles, implementation boundaries, and safety constraints.
- `README.md` — Project mission and planned stack overview.
- `docs/` — Canonical architecture, coding standards, database, security, and structure guides.
- `memory.md` — Living project memory, status, decisions, and verified checks.
- *(Target)* `apps/client/` — Unified Flutter app for Android and Windows.
- *(Target)* `agents/windows-agent/` — Local Windows execution daemon in Python.
- *(Target)* `packages/contracts/` — Versioned event schemas and API specifications.
- *(Target)* `packages/python-common/` — Shared Python utilities (logging, correlation ID propagation).
- *(Target)* `infrastructure/` — Docker Compose, PostgreSQL init scripts, RabbitMQ configuration.
- *(Target)* `services/task-service/` — Task lifecycle management and status tracking.
- *(Target)* `services/orchestrator/` — Workflow execution and tool dispatching.
- *(Target)* `services/gateway/` — API Gateway / BFF.

## 6. Key Design & Safety Decisions
- **Incremental Construction:** Never generate empty shell services; implement only when actively required.
- **Data Encapsulation:** Each service exclusively manages its own tables and migrations. Other services must interact via REST or RabbitMQ events.
- **Untrusted Model Output:** LLM outputs are treated as proposals, never as direct execution authorization.
- **No Arbitrary Code/Shell Execution:** LLMs may never execute arbitrary shell or model-generated scripts. Tools must be allowlisted with strictly validated parameters.
- **Human Authorization Required:** Explicit confirmation is mandatory for destructive actions (deletion), external communications/sharing, financial transactions, and account changes.
- **Credential & Secret Protection:** Secrets reside in environment variables or secret stores; never in source control, log outputs, or model prompts.
- **Failure Resilience:** Fail-closed security posture, bounded retries with dead-lettering, and correlation ID tracing across all boundaries.

## 7. Known Issues & Environment Constraints
- **Git Repository:** Git is currently not initialized in this workspace folder (`fatal: not a git repository`).
- **Execution Sandbox:** Command execution in the standard sandbox restricts access to files outside the workspace; host Python runtime (`C:\Python314\python.exe`) requires sandbox bypass permission when invoked directly.

## 8. Tests & Verification Checks Run
- [x] Inspected workspace files via filesystem listing (`docs/`, `AGENTS.md`, `README.md`).
- [x] Verified full contents of all 6 documentation guides in `docs/`.



## 9. Recommended Next Implementation Step
1. **Initialize Git & Repository Basics:**
   - Initialize git repository and create a comprehensive `.gitignore` tailored for Python, Flutter/Dart, Docker, and environment files (`.env`).
2. **Local Infrastructure Foundation:**
   - Create `infrastructure/docker-compose.yml` to provision PostgreSQL (with healthchecks and initialization) and RabbitMQ (with management UI).
3. **Shared Contracts Package:**
   - Scaffold `packages/contracts/` to define initial versioned schemas: base event envelope, task lifecycle events, and task models using Pydantic.
4. **Scaffold Initial Core Service (`services/task-service/`):**
   - Implement the Task Service following `docs/service-code-structure.md` (thin routes, domain models, Alembic migrations, database session, and healthcheck endpoints).
