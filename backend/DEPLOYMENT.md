# Deployment Notes

This document outlines preparation steps for deploying the backend to Render (web service + worker).

Commands:

- Run migrations before startup:

```bash
export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
cd backend
alembic upgrade head
```

- Start web service (example using gunicorn):

```bash
gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
```

- Start worker service:

```bash
python -m app.workers.send_worker
```

Healthcheck endpoints:

- `/health/live` - process liveness
- `/health/ready` - DB + Redis readiness

DLQ behavior:

- Configure `AWS_SQS_DLQ_URL` in environment for the worker to route failing messages.
- Worker will attempt `WORKER_MAX_RETRIES` then push payload to DLQ.
