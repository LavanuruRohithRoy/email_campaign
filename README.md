# Email Campaign Platform

A multi-tenant email campaign platform built with FastAPI, PostgreSQL, Redis, AWS SES/S3/SQS, and React + Vite. The application is structured for org-scoped team workflows, secure authentication, campaign sending, subscriber-safe tracking, unsubscribe compliance, and a production-ready frontend foundation.

## Current Stage

The project is complete through M8.

Implemented modules:
- M1 Auth, JWT refresh rotation, logout, RBAC, and Redis-backed login rate limiting
- M2 Contacts, lists, CSV import scaffolding, segments, and suppression checks
- M3 Templates, image upload helper, starter seeding, and template lifecycle protections
- M4 Campaign lifecycle, recipient targeting, exclusions, schedule controls, and test sends
- M5 Scheduling and SES/SQS sending workers
- M6 Open/click tracking with public tracking endpoints
- M7 Bounce/complaint handling with suppression-list updates and worker safeguards
- M8 Unsubscribe management, preference center APIs, send-safety validation, and frontend foundation

The backend test suite currently passes with 86 tests green. The frontend lint and production build also pass.

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

### Tracking and Events
- Public `/track/open` endpoint returning a transparent pixel
- Public `/track/click` endpoint redirecting through tracked URLs
- Opaque tracking tokens for open, click, and unsubscribe links
- Open-event deduplication per contact/campaign
- Click-event recording on every click
- Bounce and complaint handling from webhook/SNS/SQS flow
- Automatic suppression-list entries for permanent bounce and complaint handling

### M8 Unsubscribe Management
- Public `/unsubscribe?t={token}` endpoint with no JWT requirement
- Public `/preferences?t={token}` GET and POST endpoints with no JWT requirement
- One-click unsubscribe from existing outbound unsubscribe tokens
- Contact-level unsubscribe state management
- Idempotent repeated unsubscribe clicks
- Single unsubscribe event recording with `source=unsubscribe_link`
- Preference center reactivation only for `unsubscribed -> active`
- Bounced and complained contacts cannot be reactivated through preferences
- Future campaign recipient resolution excludes unsubscribed, bounced, complained, and suppressed contacts

## Frontend Features

The production frontend has started in `frontend/` with:
- React 18, TypeScript, Vite, TailwindCSS, and shadcn-style UI primitives
- React Router DOM for routing
- TanStack Query for server state
- Zustand for client/session UI state
- Axios API client with JWT attachment and refresh-token retry flow
- React Hook Form and Zod for form validation
- sonner toasts and lucide-react icons
- Auth login page and protected route shell
- Responsive dashboard shell with sidebar, top nav, mobile sheet, user menu, and role-aware navigation
- Contacts, lists, and segments foundation pages wired to real backend APIs
- Public unsubscribe and preference center pages wired to real M8 APIs

Frontend environment example:

```env
VITE_API_BASE_URL=http://localhost:8000
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
      auth/
      dashboard/
      contacts/
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
- AWS SES, S3, SQS
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

## Running Locally

Backend:

```bash
cd backend
python -m pytest tests -v
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

## Validation Snapshot

Latest local checks:

```bash
cd backend
$env:PYTHONPATH='.'; ..\.venv\Scripts\pytest.exe tests -v
# 86 passed

cd frontend
npm run lint
npm run build
# both passed
```
