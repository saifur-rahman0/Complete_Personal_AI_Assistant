# Task Service (`services/task-service`)

The Task Service manages task creation, state transitions, human authorization requests, and status reporting for the AI Workforce assistant.

## Key Capabilities
- **REST Endpoints:**
  - `GET /health` & `GET /ready`: Health check endpoints.
  - `POST /api/v1/tasks`: Submit a new task from the Flutter client.
  - `GET /api/v1/tasks`: List tasks with status filtering.
  - `GET /api/v1/tasks/{id}`: Detailed task status and logs.
  - `PATCH /api/v1/tasks/{id}`: State transitions.
  - `POST /api/v1/approvals`: Enqueue an action requiring human approval.
  - `GET /api/v1/approvals`: List pending approvals (used by Android companion).
  - `POST /api/v1/approvals/{id}/resolve`: Approve or reject an action.

## Local Execution
From the service directory or with the virtual environment activated:
```bash
uvicorn task_service.main:app --host 0.0.0.0 --port 8001 --reload
```
Interactive OpenAPI docs will be available at:
`http://localhost:8001/docs`
