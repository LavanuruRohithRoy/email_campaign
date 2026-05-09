# Email Campaign Platform — Agent Rules
# Stack: FastAPI + PostgreSQL + Redis + AWS SES/S3/SQS + React+Vite+Tailwind+shadcn

## WHAT WE'RE BUILDING
Mailchimp-like platform. Teams create/send/track email campaigns via AWS SES.
Three admin roles + subscriber (no login). Deadline: 12th May.

## PROJECT STRUCTURE
backend/app/
  main.py          # FastAPI app, router registration, lifespan
  config.py        # pydantic-settings, all env vars, fail fast if missing
  database.py      # Async SQLAlchemy engine + session
  dependencies.py  # get_db, get_current_user, require_role()
  models/          # SQLAlchemy ORM, one file per domain
  schemas/         # Pydantic v2 request/response, one file per domain
  routers/         # FastAPI routers, one file per domain
  services/        # Business logic only, no HTTP concerns
  workers/         # send_worker.py, bounce_worker.py, scheduler.py
  middleware/      # JWT auth, Redis rate limiting
  utils/           # security.py, token.py, csv_parser.py, pagination.py
backend/migrations/ # Alembic only, never alter DB manually
frontend/src/
  api/             # Axios instances + typed API functions
  components/      # shadcn/ui primitives + custom
  pages/           # auth/, dashboard/, contacts/, templates/, campaigns/, settings/, public/
  guards/          # ProtectedRoute, RoleGuard
  context/         # AuthContext (JWT payload, token, expiry)
  hooks/
docker-compose.yml  # postgres + redis for local dev

## TECH STACK
Backend:      FastAPI async, SQLAlchemy 2.x async, Alembic
Auth:         Custom JWT via python-jose + passlib[bcrypt]
Cache:        Redis via redis-py async
Queue:        AWS SQS (send queue + events queue)
Email:        AWS SES via boto3 in asyncio.to_thread
Storage:      AWS S3 via boto3
Frontend:     React 18 + Vite + TypeScript
Styling:      Tailwind CSS + shadcn/ui
Email editor: Unlayer @unlayer/react — do NOT build DnD from scratch
Forms:        React Hook Form + Zod
Data fetch:   TanStack Query
Charts:       Recharts

## SECURITY
- No hardcoded credentials. All via .env loaded through config.py.
- Passwords: bcrypt only. Never store/log/return plain text.
- JWT payload: { sub: user_id, role, org_id, exp: now+15min }
- Refresh token: 7 days, hashed in DB, single-use rotated.
- Login rate limit: 5 attempts/IP/15min via Redis. Return 429 after.
- AWS keys via env only. Never pass explicitly to boto3 clients.
- Tracking URLs use secrets.token_urlsafe(16), never raw DB IDs.
- CORS: ALLOWED_ORIGINS env only. Never allow_origins=["*"] in prod.
- ORM or parameterised queries only. No f-string SQL ever.

## CODE RULES
- No dead code, no unused imports or variables.
- Routers: HTTP only. Services: logic only. Workers: queues only.
- Full type hints — params and return types. No bare Any.
- Async all the way. No blocking I/O in handlers.
- HTTPException at router layer. Custom exceptions in services.
- No print() — use Python logging.
- All list endpoints: limit + offset, default 50, max 200.
- Every DB change = Alembic migration. Never alter tables manually.

## DATABASE
users:               id, org_id, email(unique), password_hash, role(enum), is_active
organisations:       id, name, logo_url, from_email, ses_config_set, aws_region
refresh_tokens:      id, user_id, token_hash, expires_at, used
contact_lists:       id, org_id, name, tags[]
contacts:            id, org_id, email, first_name, last_name, status(enum), custom_fields(JSONB), source(enum) | UNIQUE(org_id, email)
contact_list_members: contact_id, list_id, subscribed_at | PK(contact_id, list_id)
segments:            id, org_id, name, rules(JSONB)
templates:           id, org_id, name, category, blocks(JSONB), html(TEXT), thumbnail_url
campaigns:           id, org_id, name, subject, preview_text, from_name, from_email, status(enum), template_id, scheduled_at, timezone
campaign_sends:      id, campaign_id, contact_id, ses_message_id, status(enum) | UNIQUE(campaign_id, contact_id)
email_events:        id, contact_id, campaign_id, event_type(enum), occurred_at, ip_address, user_agent, metadata(JSONB)
suppression_list:    id, org_id, email, reason(enum), suppressed_at | UNIQUE(org_id, email)
tracking_tokens:     id, token(unique), contact_id, campaign_id, token_type(enum), target_url
import_jobs:         id, list_id, status(enum), total_rows, added, updated, skipped, errored

Enums:
  role:            super_admin | campaign_manager | viewer
  contact.status:  active | unsubscribed | bounced | complained
  event_type:      sent | delivered | opened | clicked | bounced | complained | unsubscribed
  campaign.status: draft | scheduled | sending | sent | paused | cancelled

Indexes:
  contacts(org_id, email)
  email_events(campaign_id, event_type)
  campaign_sends(campaign_id, status)
  tracking_tokens(token)
  suppression_list(org_id, email)

## RBAC
Super Admin:      All routes. AWS config. User management.
Campaign Manager: /contacts/*, /templates/*, /campaigns/*, /analytics/ read. No /settings/.
Viewer:           /analytics/*, /campaigns/:id/report only. Read-only.
Subscriber:       /track/*, /unsubscribe, /preferences — public, no token needed.
Enforce via require_role() FastAPI dependency. Never in service layer.

## AWS FLOW
SEND:   campaign_service → SQS(SEND_QUEUE) → send_worker → inject tracking → SES → campaign_sends
EVENTS: SES → SNS Topic → SQS(EVENTS_QUEUE) → bounce_worker → contact + suppression + email_events
OPEN:   GET /track/open?t={token} → resolve → email_events(opened) → return 1x1 PNG
CLICK:  GET /track/click?t={token} → resolve → email_events(clicked) → 302 to target_url

## ENV VARS (app refuses to start if any missing)
APP_ENV, SECRET_KEY, JWT_SECRET
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
AWS_S3_BUCKET, AWS_SQS_SEND_QUEUE_URL, AWS_SQS_EVENTS_QUEUE_URL, AWS_SES_CONFIG_SET
ALLOWED_ORIGINS
VITE_API_BASE_URL

## API CONVENTIONS
Prefix: /api/v1/   Public routes: /track/, /unsubscribe, /preferences
Auth header: Authorization: Bearer <token>
Error shape: { "detail": "message", "code": "SNAKE_CASE_CODE" }
List shape:  { "items": [], "total": 0, "limit": 50, "offset": 0 }
Timestamps: ISO 8601 UTC. UUIDs as strings.

## FRONTEND RULES
Role-aware sidebar:
  Super Admin:      full sidebar
  Campaign Manager: no Settings
  Viewer:           Analytics + Campaign reports only
ProtectedRoute: redirect /login if no valid token.
RoleGuard: render 403 page if role insufficient.
Axios: inject token on every request. On 401 try refresh once. On second 401 clear + redirect /login.
Unlayer: on save exportHtml() + exportDesign(). Send both to PUT /api/v1/templates/:id.

## BUILD ORDER
1.  Repo + docker-compose (postgres + redis)
2.  config.py, database.py, Alembic baseline migration
3.  M1 Auth — users, JWT, refresh tokens, RBAC middleware
4.  M2 Contacts — lists, contacts CRUD, CSV import job
5.  M3 Templates — Unlayer save/load JSON+HTML
6.  M4 Campaigns — 4-step wizard, draft management
7.  M5 Scheduling — SQS enqueue, send_worker, scheduler
8.  M6 Tracking — pixel endpoint, click redirect, token resolution
9.  M7 Bounce/Complaint — bounce_worker, suppression list
10. M8 Unsubscribe — public endpoint, List-Unsubscribe header injection
11. M9 Analytics — aggregations, dashboard KPIs, campaign report

## HARD STOPS
- No time.sleep() in async code — use await asyncio.sleep()
- No requests library — use httpx async
- No SELECT * — always name columns
- Never return password_hash in any response
- Never expose DB IDs in public URLs — opaque tokens only
- Never skip suppression check before sending
- Never allow_origins=["*"] in production
- Never commit .env — commit .env.example only
- Never put business logic in routers