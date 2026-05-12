# Backend Deployment Notes

## Commands
### Run migrations
```bash
cd backend
alembic upgrade head
```

### Start API service
```bash
gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
```

### Start send worker
```bash
python -m app.workers.send_worker
```

### Start scheduler worker
```bash
python -m app.workers.scheduler
```

## Healthchecks
- `/health/live` and `/api/v1/health/live`
- `/health/ready` and `/api/v1/health/ready`

## DLQ Behavior
- Configure `AWS_SQS_DLQ_URL` to enable dead-letter forwarding.
- Worker retries failures up to `WORKER_MAX_RETRIES` before DLQ handoff.

## SES/SNS/SQS/S3 Integration Expectations
- SES: used for campaign and test email sends.
- SNS: sends SES event notifications to `/webhooks/ses`.
- SQS: send worker polls `AWS_SQS_SEND_QUEUE_URL`.
- S3: analytics CSV export + template asset storage.

## Render Runtime Notes
- Keep API and workers as separate services.
- Use shared environment variables across backend and worker services.
- Ensure migrations run before promoting a new API release.
