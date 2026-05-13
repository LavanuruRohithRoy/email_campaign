# Deployment Runbook

This repository is prepared for pre-hosting validation and staging deployment wiring.

## 1) Deployment Targets
- **Backend API:** Render web service
- **Workers:** Render background workers (`send_worker`, `scheduler`)
- **Frontend:** Netlify static deployment
- **Database:** Managed PostgreSQL
- **Cache:** Managed Redis
- **Email/Queues/Storage:** AWS SES + SNS + SQS + S3

## 2) Required Environment Configuration
Use `.env.example` as baseline. Do not commit real values.

Critical production variables:
- `APP_ENV=production`
- `APP_BASE_URL`
- `SECRET_KEY`
- `JWT_SECRET`
- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- `REDIS_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `AWS_SQS_SEND_QUEUE_URL`
- `AWS_SQS_EVENTS_QUEUE_URL`
- `AWS_SQS_DLQ_URL` (recommended)
- `AWS_SES_CONFIG_SET`
- `ALLOWED_ORIGINS`
- `VITE_API_BASE_URL`

## 3) Backend Startup
```bash
cd backend
alembic upgrade head
gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
```

## 4) Worker Startup
```bash
cd backend
python -m app.workers.send_worker
python -m app.workers.scheduler
```
Render workers should use the same environment variable set as the API service, including
`WORKER_CONCURRENCY`, `WORKER_MAX_RETRIES`, `SQS_POLL_WAIT_SECONDS`, and `SQS_MAX_MESSAGES`.

## 5) Frontend Build/Deploy
```bash
cd frontend
npm ci
npm run build
```
Netlify should publish `frontend/dist`.

## 6) Migration Commands
```bash
cd backend
alembic upgrade head
alembic current
alembic history
```

## 7) AWS Resource Requirements
Provision before live runtime:
1. SES verified domain/sender identities
2. SES configuration set
3. SNS topic for SES notifications
4. SQS send queue
5. SQS events queue (optional if webhook fan-out is introduced later)
6. SQS dead-letter queue
7. S3 bucket for template assets and analytics exports

## 8) IAM Permissions
Application IAM principal needs:
- SES: `ses:SendEmail`, `ses:SendRawEmail`
- SQS: `sqs:SendMessage`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`
- SNS: permission to confirm/receive notifications for subscribed endpoint flow
- S3: `s3:PutObject`, `s3:GetObject` on configured bucket paths

## 9) Queue + DLQ Runtime Behavior
- Send worker consumes campaign jobs from send queue
- Retry state is tracked in Redis per campaign/contact
- On retry exhaustion (`WORKER_MAX_RETRIES`), payload is forwarded to DLQ
- DLQ messages can be replayed manually after root-cause remediation
- Workers support graceful shutdown for SIGTERM/SIGINT so Render can stop instances cleanly

## 10) SES/SNS Event Flow
- SES events are delivered through SNS to `/webhooks/ses`
- Webhook processing updates delivery status, suppression state, and analytics events
- Event types handled: delivered, bounced, complained, opened, clicked, unsubscribed

## 11) Healthchecks
- `/health/live` and `/health/ready`
- `/api/v1/health/live` and `/api/v1/health/ready`

## 12) API Docs Endpoints
- `/docs`
- `/redoc`
- `/openapi.json`

## 13) Final Pre-Hosting Checklist
- CI workflows passing
- Render/Netlify config files updated
- Env values set in platform dashboards
- Migrations applied successfully
- Backend and workers start without config errors
- Frontend build succeeds
- Healthchecks return expected status
- No secrets committed to repo
