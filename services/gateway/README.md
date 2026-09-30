# Gateway Service

The API Gateway is the unified entry point for mobile (Android companion) and desktop (Windows) clients.

## Features
- Port: `8000`
- Reverse proxy to internal microservices (`task-service` :8001, `decision-router` :8002, `automation-service` :8003, `web-research` :8004).
- WebSocket & SSE event streaming (`/ws/events/{device_id}`, `/api/v1/stream/events`).
- Cross-device state synchronization and offline action reconciliation (`/api/v1/sync/batch`).
- Distributed correlation ID propagation (`X-Correlation-ID`).
