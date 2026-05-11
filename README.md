# Email Campaign Platform

A multi-tenant email campaign platform built with FastAPI, PostgreSQL, Redis, AWS SES/SNS/SQS/S3, and React + Vite. The application is structured for org-scoped team workflows, secure authentication, campaign sending, subscriber-safe tracking, unsubscribe compliance, analytics reporting, and deployment-ready frontend/backend boundaries.

## Current Stage

The project is complete through M9.

Implemented modules:
- M1 Auth, JWT refresh rotation, logout, RBAC, and Redis-backed login rate limiting
- M2 Contacts, lists, CSV import scaffolding, segments, and suppression checks
- M3 Templates, image upload helper, starter seeding, and template lifecycle protections
- M4 Campaign lifecycle, recipient targeting, exclusions, schedule controls, and test sends
- M5 Scheduling and SES/SQS sending workers
- M6 Open/click tracking with public tracking endpoints
- M7 Bounce/complaint handling with suppression-list updates and worker safeguards
- M8 Unsubscribe management, preference center APIs, send-safety validation, and frontend foundation
- M9 Analytics, reporting APIs, CSV export, dashboard visualization, campaign reports, and live send monitoring UI

## Backend Features

### Authentication and Authorization
- Email/password login with bcrypt-hashed passwords
- JWT access tokens and single-use refresh token rotation
- Logout invalidation for refresh tokens
- `/api/v1/auth/me` session lookup
- Role-based access control for `super_admin`, `campaign_manager`, and `viewer`
- Redis-backed login rate limiting

### Contacts, Lists, and Segments
- Contact CRUD with org-scoped validation
- Contact list CRUD and membership management
- Contact detail responses with memberships and event history
- CSV preview and import-job creation
- Segment CRUD and live segment counts
- Suppression checks on contact creation and import flows

### Templates
- Template create, list, read, update, delete, and duplicate
- Delete protection when campaigns reference a template
- Starter template seeding
- S3-backed image asset helper
- Viewer read access with write restrictions

### Campaigns and Sending
- Campaign create, list, read, update, delete, and duplicate
- Draft-only protections for campaign modifications
- Recipient targeting for lists and segments, including exclusions
- Recipient resolution with deduplication, suppression filtering, and contact-status safety
- Schedule, cancel schedule, immediate send, pause, resume, and progress endpoints
- SQS enqueue flow and async send worker
- SES-backed test send and campaign delivery path

### Tracking, Bounce, and Unsubscribe
- Public `/track/open` endpoint returning a transparent pixel
- Public `/track/click` endpoint redirecting through tracked URLs
- Opaque tracking tokens for open, click, and unsubscribe links
- Open-event deduplication per contact/campaign
- Click-event recording on every click
- Bounce and complaint handling from webhook/SNS/SQS flow
- Automatic suppression-list entries for permanent bounce and complaint handling
- Public `/unsubscribe?t={token}` endpoint with no JWT requirement
- Public `/preferences?t={token}` GET and POST endpoints with no JWT requirement
- Idempotent one-click unsubscribe with a single unsubscribe event
- Preference center reactivation only for `unsubscribed -> active`
- Future campaign recipient resolution excludes unsubscribed, bounced, complained, and suppressed contacts

### Analytics and Reports
- Protected `/api/v1/analytics/dashboard` dashboard metrics
- Protected `/api/v1/analytics/campaigns/{campaign_id}` campaign analytics
- Protected `/api/v1/analytics/campaigns/top` top campaign performance
- Protected `/api/v1/analytics/timeseries/opens` and `/clicks` time-series endpoints
- Protected `/api/v1/analytics/campaigns/{campaign_id}/export` CSV export endpoint
- Aggregated sent, delivered, open, click, bounce, complaint, and unsubscribe metrics
- Safe rate calculations with zero-division protection
- Redis caching for dashboard and campaign analytics with 300-second TTL
- S3-backed signed download URL generation for campaign report CSV files

## Frontend Features

The production frontend lives in `frontend/` with:
- React 18, TypeScript, Vite, TailwindCSS, and shadcn-style UI primitives
- React Router DOM for routing
- TanStack Query for server state
- Zustand for client/session UI state
- Axios API client with JWT attachment and refresh-token retry flow
- React Hook Form and Zod for form validation
- sonner toasts and lucide-react icons
- Recharts and date-fns for analytics visualization
- Auth login page and protected route shell
- Responsive dashboard shell with sidebar, top nav, mobile sheet, user menu, and role-aware navigation
- Contacts, lists, and segments foundation pages wired to real backend APIs
- Public unsubscribe and preference center pages wired to real M8 APIs
- Analytics dashboard with KPI widgets, open/click charts, and top campaigns
- Campaign report page with delivery, engagement, bounce, complaint, unsubscribe, CSV export, and live progress polling

Frontend routes:
- `/dashboard`
- `/contacts`
- `/lists`
- `/segments`
- `/campaigns`
- `/campaigns/:id/report`
- `/analytics`
- `/templates`
- `/settings`
- `/unsubscribe`
- `/preferences`

Frontend environment example:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Production frontend environment:

```env
VITE_API_BASE_URL=https://your-api-domain.com
```

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    dependencies.py
    models/
    routers/
    schemas/
    services/
    workers/
    middleware/
    utils/
  migrations/
  scripts/
  tests/

frontend/
  src/
    api/
    components/
      layout/
      ui/
      forms/
      tables/
    features/
      analytics/
        api/
        components/
        hooks/
        pages/
        types/
      auth/
      campaigns/
      contacts/
      dashboard/
      lists/
      segments/
      unsubscribe/
    hooks/
    lib/
    pages/
    routes/
    services/
    stores/
    types/
```

## Tech Stack

Backend:
- FastAPI
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Redis
- AWS SES, SNS, SQS, S3
- python-jose
- bcrypt
- pytest and pytest-asyncio
- httpx

Frontend:
- React 18
- TypeScript
- Vite
- TailwindCSS
- shadcn/ui-style primitives
- React Router DOM
- TanStack Query
- Zustand
- Axios
- React Hook Form
- Zod
- sonner
- lucide-react
- Recharts
- date-fns

## Running Locally

Backend:

```bash
cd backend
python -m pytest tests -v
```

M9 validation target:

```bash
cd backend
pytest tests/test_analytics.py -v
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend validation:

```bash
cd frontend
npm run lint
npm run build
```

## Deployment Preparation

Preferred production targets:
- Backend Web Service: Render
- Backend workers: separate Render background workers for send/scheduler/event processing
- Frontend: Vercel
- Database: Neon PostgreSQL
- Redis: Upstash Redis
- AWS: SES, SNS, SQS, and S3 remain external services

Backend production environment must include:
- `APP_ENV=production`
- `APP_BASE_URL=https://your-api-domain.com`
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
- `AWS_SES_CONFIG_SET`
- `ALLOWED_ORIGINS=https://your-frontend-domain.com`

Frontend production environment must include:
- `VITE_API_BASE_URL=https://your-api-domain.com`

Healthcheck routes are available through module health endpoints, including `/api/v1/auth/health`, `/api/v1/analytics/health`, `/track/health`, `/unsubscribe/health`, and `/preferences/health`.

## Validation Snapshot

Latest requested M9 validation:

```bash
cd backend
$env:PYTHONPATH='.'; ..\.venv\Scripts\pytest.exe tests/test_analytics.py -v
# 10 passed
```
