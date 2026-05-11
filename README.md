# Email Campaign Platform

A multi-tenant email campaign platform built with FastAPI, PostgreSQL, Redis, AWS SES/S3/SQS, and React + Vite. The product is designed to support team-based campaign management with role-based access, secure authentication, campaign tracking, and operational reliability for production email delivery workflows.

## Current Stage

This stage focuses on the foundation for authentication, authorization, database reliability, and test stability. The backend now supports M1 Auth end-to-end, including JWT login, refresh token rotation, logout, and role-based access control. The database migration path has also been stabilized so the schema can be created and upgraded cleanly.

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