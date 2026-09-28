# Local Infrastructure

This directory provides Docker Compose definitions for running the foundational local infrastructure services required by the AI Workforce platform:

- **PostgreSQL 16**: Relational storage for task records, audit logs, and service data.
- **RabbitMQ 3 (with Management)**: Asynchronous event message broker.

## Prerequisites
- Docker and Docker Compose installed and running.

## Quick Start

### Start services in the background:
```bash
docker compose up -d
```

### Check service health and logs:
```bash
docker compose ps
docker compose logs -f
```

### Stop services:
```bash
docker compose down
```

### Stop services and remove persisted volume data (resets databases):
```bash
docker compose down -v
```

## Service Access Points

| Service | Protocol / Interface | Port | Credentials |
|---|---|---|---|
| PostgreSQL | `postgresql://` | `5432` | `postgres` / `postgres` (db: `ai_workforce`) |
| RabbitMQ AMQP | `amqp://` | `5672` | `guest` / `guest` |
| RabbitMQ Management UI | HTTP Dashboard | `http://localhost:15672` | `guest` / `guest` |
