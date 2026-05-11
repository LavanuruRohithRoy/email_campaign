# Email Campaign Platform

A multi-tenant email campaign platform built with FastAPI, PostgreSQL, Redis, AWS SES/S3/SQS, and React + Vite. The application is structured for org-scoped team workflows, secure authentication, and a testable service-layer architecture.

## Current Stage

This stage now includes M1 Auth, M2 Contacts, M3 Template Builder, M4 Campaign Management, M5 Scheduling and Sending, and M6 Open/Click Tracking. Authentication, refresh rotation, logout, RBAC, rate limiting, contact workflows, template CRUD, campaign lifecycle management, SQS enqueue/send worker flows, scheduler-triggered sends, SES-backed test send, tracking token injection, and public tracking endpoints are implemented and covered by tests.

## What Is Implemented

### Authentication and Session Management
- Email and password login with bcrypt-hashed passwords
- JWT access token issuance
- Refresh token generation and rotation
- Logout flow that invalidates refresh tokens
- `/me` endpoint for authenticated user lookup

### Authorization
- Role-based access control using:
  - `super_admin`
  - `campaign_manager`
  - `viewer`
- Guarded route access through FastAPI dependencies
- Authenticated and role-restricted route patterns in place for future modules

### Security and Rate Limiting
- Login rate limiting backed by Redis
- Rate limiting active in all environments
- Proper 429 response behavior after repeated failed logins
- Secure token handling and password verification logic

### M2 Contacts
- Contact list create, update, delete, and list operations
- Contact CRUD with org-scoped validation
- Contact list membership management
- Contact detail responses with list memberships and event history
- CSV preview and import job scaffolding
- Segment create, update, delete, and live count support
- Suppression-list checks on contact creation and import paths
- Org-scoped filtering across lists, contacts, segments, and imports

### M3 Template Builder
- Template create, list, update, delete, and duplicate operations
- Template delete protection when a campaign references the template
- Starter template seeding for new organizations
- Image asset upload helper backed by S3
- Org-scoped template access for super admins, campaign managers, and viewers
- Template schema and service layer aligned with the campaign/template model

### M4 Campaign Management
- Campaign create, list, read, update, delete, and duplicate operations
- Draft-only protection for campaign updates and deletes
- Recipient target configuration for lists, segments, and exclusions
- Recipient resolution with deduplication and suppression filtering
- Estimated recipient count endpoint for send confirmation
- Campaign scheduling and cancellation flow
- Test-send request validation and SES-backed delivery

### M5 Scheduling and Sending
- Immediate campaign send endpoint that enqueues recipients into SQS
- Pause and resume controls for in-flight sends
- Send progress endpoint with sent/total status
- Async send worker for SQS polling, personalization, tracking-token injection, and SES delivery
- Scheduler loop that triggers due scheduled campaigns
- Worker send-rate throttling and concurrency controls via settings

### M6 Open and Click Tracking
- Public tracking endpoints at `/track/open` and `/track/click` (no JWT)
- 1x1 transparent pixel response for open tracking (always 200)
- Click redirect response for click tracking (always 302)
- Token resolution through `tracking_tokens` table
- Duplicate guard for open events (one opened event per contact/campaign token context)
- Click event capture on every click with URL metadata
- Device context capture on events (`ip_address`, `user_agent`)

### Database and Migration Stability
- Alembic migration path stabilized
- Initial schema migration made safe for enum creation
- Database cleanup helper added for local development and repeatable test setup
- ORM models aligned with current auth and schema expectations

### Test Reliability
- Async test fixtures standardized
- Async SQLAlchemy session handling for tests
- Redis isolation per test run
- Auth test coverage for:
  - successful login
  - wrong password rejection
  - login rate limiting
  - `/me` access
  - refresh token rotation
  - refresh token reuse rejection
  - role guard denial
  - logout invalidation
- Contact test coverage for lists, contacts, suppression, CSV preview, import job creation, segments, and RBAC
- Template test coverage for CRUD, duplication, delete-in-use, viewer read access, seed, and upload validation
- Campaign test coverage for CRUD, duplicate, recipient configuration, recipient count, scheduling, cancel schedule, test-send validation, and viewer RBAC
- Sending test coverage for enqueue, pause/resume, progress, worker processing, and scheduler triggering
- Tracking test coverage for open pixel, open dedup, click redirect, click metadata, and invalid-token handling
- Full backend suite currently passes with 69 tests green

## Project Structure

### Backend
- `backend/app/main.py` - FastAPI app and router registration
- `backend/app/config.py` - environment settings
- `backend/app/database.py` - async SQLAlchemy engine and session setup
- `backend/app/dependencies.py` - auth and DB dependencies
- `backend/app/models/` - ORM models and enums
- `backend/app/routers/` - API route modules
- `backend/app/services/` - business logic layer
- `backend/app/middleware/` - request middleware and rate limiting
- `backend/app/utils/` - security and token helpers

### Migrations
- `backend/migrations/` - Alembic migrations and schema evolution

### Tests
- `backend/tests/` - backend test suite and fixtures

## Backend Tech Stack
- FastAPI
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Redis
- python-jose
- bcrypt
- pytest
- pytest-asyncio
- httpx

## Running Locally

### Backend
1. Install dependencies.
2. Configure environment variables.
3. Apply migrations.
4. Run the FastAPI application.

### Tests
Run the full backend test suite:

```bash
python -m pytest tests/ -v