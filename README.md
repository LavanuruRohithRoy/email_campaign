# Email Campaign Platform

## 1. Project Overview
Multi-tenant email campaign platform for team-based campaign creation, audience targeting, tracked delivery, unsubscribe compliance, and analytics reporting.

## 2. Architecture Overview
- **Backend:** FastAPI + async SQLAlchemy + PostgreSQL + Redis
- **Workers:** async queue workers for campaign send processing and scheduling
- **Infra integrations:** AWS SES (send), SQS (send queue + DLQ), SNS (SES event delivery), S3 (analytics CSV export + template assets)
- **Frontend:** React + Vite + TypeScript + Tailwind + shadcn-style UI

## 3. Tech Stack
### Backend
FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL, Redis, boto3, python-jose, passlib[bcrypt], httpx, pytest/pytest-asyncio.

### Frontend
React 18, Vite, TypeScript, React Router, TanStack Query, Zustand, Axios, React Hook Form, Zod, Recharts, TailwindCSS.

## 4. Backend Structure
```text
backend/app/
  main.py
  config.py
  database.py
  dependencies.py
  core/
  middleware/
  models/
  routers/
  schemas/
  services/
  utils/
  workers/
backend/migrations/
backend/tests/
```

## 5. Frontend Structure
```text
frontend/src/
  components/
  features/
    analytics/
    auth/
    campaigns/
    contacts/
    dashboard/
    lists/
    segments/
    templates/
    unsubscribe/
  lib/
  routes/
  stores/
  types/
```

## 6. Queue/Worker Architecture
- Campaign sends are enqueued to `AWS_SQS_SEND_QUEUE_URL`
- `python -m app.workers.send_worker` polls queue, applies suppression/status checks, injects tracking/unsubscribe links, sends via SES, writes `campaign_sends` + `email_events`
- Failed send processing is retried with exponential backoff using Redis retry keys
- After `WORKER_MAX_RETRIES`, message is sent to `AWS_SQS_DLQ_URL` when configured
- `python -m app.workers.scheduler` promotes due scheduled campaigns into send queue

## 7. SES/SQS/SNS Flow
1. Campaign send starts from API/service layer and enqueues recipient jobs to SQS
2. Send worker pulls message, renders email, sends using SES configuration set
3. SES delivery/bounce/complaint notifications go through SNS
4. SNS notifies webhook endpoint: `POST /webhooks/ses` (also available at `/api/v1/webhooks/ses`)
5. Webhook processing updates events + suppression and campaign send status

## 8. Analytics Flow
- Event data (`sent`, `delivered`, `opened`, `clicked`, `bounced`, `complained`, `unsubscribed`) is aggregated from `email_events`
- Dashboard + campaign report endpoints provide KPI summaries and time-series
- Report export endpoint builds CSV and uploads to S3, returns presigned URL
- Redis cache reduces analytics query load (TTL 300s)

## 9. Template Builder Features
- Template CRUD with org scoping and role checks
- Builder editor API endpoints under `/api/v1/templates/builder`
- Supports HTML + design JSON persistence
- Template image/thumbnail upload support via S3 helpers
- Template deletion protected when campaigns reference template

## 10. Campaign Flow
- Draft campaign creation/editing
- Audience selection via lists/segments with exclusions
- Recipient resolution with deduplication and suppression/contact-status filtering
- Review + send now / schedule / cancel schedule / pause / resume
- Progress endpoint for live send status monitoring

## 11. CI/CD Setup
GitHub Actions validates quality gates on push/PR to `main`:
- Backend tests
- Backend lint/typecheck
- Frontend lint/typecheck/build
- Docker compose and image validation

## 12. Docker Setup
Root `docker-compose.yml` provisions:
- PostgreSQL
- Redis
- Backend API service
- Send worker service
- Scheduler service

## 13. Local Development Setup
### Backend
```bash
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm ci
npm run dev
```

### Workers
```bash
cd backend
python -m app.workers.send_worker
python -m app.workers.scheduler
```

## 14. Environment Variables
See `.env.example` for full list. Required groups:
- App/security: `APP_ENV`, `APP_BASE_URL`, `SECRET_KEY`, `JWT_SECRET`
- Data stores: `DATABASE_URL`, `DATABASE_URL_SYNC`, `REDIS_URL`
- AWS: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_SQS_SEND_QUEUE_URL`, `AWS_SQS_EVENTS_QUEUE_URL`, `AWS_SES_CONFIG_SET`, optional `AWS_SQS_DLQ_URL`
- Frontend/CORS: `ALLOWED_ORIGINS`, `VITE_API_BASE_URL`

## 15. GitHub Actions Workflows
- `.github/workflows/backend-tests.yml`
- `.github/workflows/lint-and-typecheck.yml`
- `.github/workflows/frontend-build.yml`
- `.github/workflows/docker-validation.yml`

## 16. Deployment Preparation
- Configuration validation is fail-fast via `app/config.py`
- Production guards block localhost DB/Redis/CORS origins
- Render service definitions included in `render.yaml`
- Netlify frontend deployment structure included in `netlify.toml`
- Deployment runbook is in `DEPLOYMENT.md` and `backend/DEPLOYMENT.md`

## 17. Render Deployment Structure
`render.yaml` defines:
- `email-backend-web` (FastAPI)
- `email-send-worker` (SQS send worker)
- `email-scheduler-worker` (scheduled campaign worker)

Each service uses backend Docker image path and environment groups from `.env.example`.

## 18. Netlify Deployment Structure
`netlify.toml` defines:
- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `frontend/dist`
- SPA redirect to `index.html`

## 19. Redis Requirements
Used for:
- Login rate limiting
- Analytics cache
- Worker retry tracking/backoff state

## 20. AWS Requirements
- SES verified domain/sender and configuration set
- SNS topic subscribed to SES notifications
- SQS send queue + events queue + DLQ
- S3 bucket for template assets and analytics report exports
- IAM permissions documented in `DEPLOYMENT.md`

## 21. Healthcheck Endpoints
Platform checks:
- `/health/live`
- `/health/ready`
- `/api/v1/health/live`
- `/api/v1/health/ready`

Module checks:
- `/api/v1/auth/health`
- `/api/v1/analytics/health`
- `/track/health`
- `/unsubscribe/health`
- `/preferences/health`
- `/webhooks/health`

## 22. Testing Structure
Backend tests are under `backend/tests/` and cover:
- auth/RBAC
- contacts/lists/segments
- campaigns/sending
- tracking/unsubscribe
- analytics
- worker retry + DLQ
- production hardening checks

Frontend validation uses lint + TypeScript + build pipeline.

## 23. Production Hardening Features
- Structured logging middleware and request IDs
- Trusted hosts + security headers + request size limits
- Redis-backed auth and webhook rate limiting
- Production config validation for secrets, URLs, origins
- Suppression list enforcement before send
- Opaque tracking/unsubscribe tokens (no public DB IDs)

## 24. Current Project Status
Repository is in **final pre-hosting readiness phase**:
- Core FRD scope implemented and operationally integrated
- CI workflows operational
- Deployment descriptors present for Render/Netlify
- Ready for staging credentials insertion and runtime validation

## 25. Remaining Runtime/Deployment Tasks
- Insert real staging/production credentials (never commit to git)
- Provision live AWS resources and wire SES/SNS/SQS/S3 ARNs/URLs
- Configure Render service env vars and worker process scaling
- Configure Netlify environment and production API origin
- Run end-to-end staging smoke tests with live queue/event traffic
- Validate SNS subscription confirmation and webhook signature flow in staging
- Validate DLQ alarm/monitoring and retry observability dashboards

---

## Commands Reference
### Migration commands
```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe_change"
```

### Frontend build commands
```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

### Local Docker workflow
```bash
# start infrastructure and app services
POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=postgres docker compose up -d

# validate compose
POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=postgres docker compose config

# stop
POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=postgres docker compose down
```

### CI validation process
1. Lint + typecheck backend/frontend
2. Execute backend tests
3. Build frontend
4. Validate docker-compose and Dockerfile build

### Queue and DLQ behavior
- Send queue receives campaign-recipient jobs
- Worker retries transient failures and rate-limits SES send rate
- Messages exceeding `WORKER_MAX_RETRIES` are moved to DLQ (if configured)
- DLQ payload wraps original message for forensic replay
