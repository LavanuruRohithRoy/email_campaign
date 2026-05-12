# Email Campaign Platform

<div align="center">

### Scalable Multi-Tenant Email Delivery & Campaign Infrastructure

<p align="center">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Frontend-React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Cache-Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Cloud-AWS-orange?style=flat-square&logo=amazonaws&logoColor=white" />
  <img src="https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square&logo=render&logoColor=black" />
  <img src="https://img.shields.io/badge/Frontend-Netlify-00C7B7?style=flat-square&logo=netlify&logoColor=white" />
  <img src="https://img.shields.io/badge/Queue-SQS-red?style=flat-square&logo=amazonaws&logoColor=white" />
  <img src="https://img.shields.io/badge/Notifications-SNS-yellow?style=flat-square&logo=amazonaws&logoColor=black" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Stage-Production_Ready-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Architecture-Async_Distributed-blueviolet?style=for-the-badge" />
</p>

</div>

---

# Live Deployment

| Service | URL |
|---|---|
| Frontend | https://email-campaign-we.netlify.app/ |
| Backend API | https://email-campaign-api-clwb.onrender.com |
| API Docs | https://email-campaign-api-clwb.onrender.com/docs |
| ReDoc | https://email-campaign-api-clwb.onrender.com/redoc |
| OpenAPI Spec | https://email-campaign-api-clwb.onrender.com/openapi.json |

---

## Overview

Enterprise-grade multi-tenant email campaign and audience management platform designed for scalable campaign orchestration, queue-driven delivery workflows, analytics tracking, and operational reliability.

The platform supports asynchronous email processing, audience segmentation, delivery telemetry, analytics aggregation, unsubscribe compliance, and distributed worker infrastructure using cloud-native services.

---

# High-Level Architecture

```text
                    ┌─────────────────────┐
                    │   React Frontend    │
                    │     (Netlify)       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  FastAPI Backend    │
                    │      (Render)       │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│ PostgreSQL DB  │   │     Redis      │   │ AWS SQS Queues │
│    (Render)    │   │   (Upstash)    │   │  Send / DLQ    │
└────────────────┘   └────────────────┘   └────────┬───────┘
                                                    │
                                                    ▼
                                         ┌────────────────┐
                                         │ Queue Workers  │
                                         │ Async Senders  │
                                         └────────┬───────┘
                                                  │
                                                  ▼
                                         ┌────────────────┐
                                         │    AWS SES     │
                                         │ Email Delivery │
                                         └────────┬───────┘
                                                  │
                                                  ▼
                                         ┌────────────────┐
                                         │ SNS Webhooks   │
                                         │ Event Pipeline │
                                         └────────────────┘
```

---

# Core Features

## Campaign Management

- Draft and scheduled campaign workflows
- Send now / scheduled send support
- Pause and resume capabilities
- Delivery progress monitoring
- Audience deduplication
- Suppression-aware delivery filtering

## Audience & Contact Management

- Contact storage and management
- List-based targeting
- Dynamic audience segmentation
- Exclusion filtering
- Subscription and suppression enforcement

## Analytics & Reporting

- Delivery metrics
- Open and click tracking
- Bounce and complaint handling
- Time-series analytics aggregation
- CSV export generation
- Cached analytics querying

## Template Builder

- Reusable email templates
- HTML and structured design persistence
- Organization-scoped template management
- Asset upload support
- Builder-oriented APIs

## Authentication & Access Control

- JWT-based authentication
- Role-aware authorization
- Tenant-scoped resource access
- Protected API routes
- Middleware-driven validation

---

# Authentication & Roles

The platform uses JWT-based authentication with role-aware authorization middleware.

## Supported Access Layers

- Admin
- Organization Manager
- Team Member

## Authentication Flow

- Login generates JWT access tokens
- Protected routes validate bearer tokens
- Role checks are enforced at API/service level
- Organization-scoped access prevents tenant crossover

## Planned Bootstrap Flow

Initial administrator provisioning is handled through:
- registration bootstrap flow
OR
- seed/bootstrap admin creation scripts

---

# Architecture Overview

## Backend

- FastAPI
- Async SQLAlchemy
- PostgreSQL
- Redis
- Alembic
- boto3
- python-jose
- passlib[bcrypt]

## Frontend

- React 18
- TypeScript
- Vite
- TailwindCSS
- TanStack Query
- Zustand
- Axios
- React Hook Form
- Recharts

## Infrastructure

- AWS SES
- AWS SQS
- AWS SNS
- AWS S3
- Docker
- GitHub Actions
- Render
- Netlify

---

# System Flow

## Delivery Pipeline

1. Campaign requests are created through API endpoints
2. Recipient jobs are pushed into queue infrastructure
3. Background workers process email delivery asynchronously
4. Emails are sent through AWS SES
5. Delivery events are routed through SNS notifications
6. Event processors update analytics and suppression states
7. Dashboard services aggregate engagement metrics

---

# Queue & Worker Infrastructure

The platform uses asynchronous queue-based processing to isolate campaign delivery workloads from API request latency.

## Worker Responsibilities

- Queue polling
- Retry orchestration
- Delivery scheduling
- Email rendering
- Tracking injection
- Suppression enforcement
- Failure handling
- Dead-letter queue forwarding

## Queue Features

- Exponential retry backoff
- Redis-backed retry state
- DLQ support
- Worker isolation
- Fault-tolerant processing

---

# Analytics Pipeline

Analytics are generated from normalized event telemetry including:

- Sent
- Delivered
- Opened
- Clicked
- Bounced
- Complained
- Unsubscribed

The reporting subsystem supports:

- KPI aggregation
- Time-series visualization
- CSV export generation
- Cached query acceleration
- Campaign performance reporting

---

# Repository Structure

## Backend

```text
backend/
├── app/
│   ├── core/
│   ├── middleware/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── workers/
├── migrations/
└── tests/
```

## Frontend

```text
frontend/
├── src/
│   ├── components/
│   ├── features/
│   ├── routes/
│   ├── stores/
│   ├── lib/
│   └── types/
```

---

# Local Development

## Backend Setup

```bash
cd backend

python -m pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup

```bash
cd frontend

npm ci

npm run dev
```

## Worker Services

```bash
cd backend

python -m app.workers.send_worker

python -m app.workers.scheduler
```

---

# Docker Environment

Containerized orchestration is supported using Docker Compose.

## Included Services

- PostgreSQL
- Redis
- Backend API
- Send Worker
- Scheduler Worker

## Start Services

```bash
docker compose up -d
```

## Stop Services

```bash
docker compose down
```

---

# Environment Configuration

## Application & Security

```env
APP_ENV=
APP_BASE_URL=
SECRET_KEY=
JWT_SECRET=
```

## Database & Cache

```env
DATABASE_URL=
DATABASE_URL_SYNC=
REDIS_URL=
```

## AWS Infrastructure

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AWS_S3_BUCKET=
AWS_SQS_SEND_QUEUE_URL=
AWS_SQS_EVENTS_QUEUE_URL=
AWS_SES_CONFIG_SET=
```

## Frontend & CORS

```env
ALLOWED_ORIGINS=
VITE_API_BASE_URL=
```

---

# Deployment Architecture

## Backend Deployment

Backend services are configured for deployment on Render using containerized service definitions.

### Services

- API Service
- Send Worker
- Scheduler Worker

## Frontend Deployment

Frontend deployment is configured for Netlify using Vite production builds.

### Build Configuration

```text
Base Directory: frontend
Build Command: npm run build
Publish Directory: frontend/dist
```

---

# CI/CD Pipeline

GitHub Actions workflows validate:

- Backend tests
- Frontend builds
- Type safety
- Linting
- Docker validation
- Compose validation

Automated deployment workflows support:

- Continuous integration
- Deployment verification
- Runtime validation
- Infrastructure consistency

---

# Health Monitoring

## Platform Health Endpoints

```text
/health/live
/health/ready
/api/v1/health/live
/api/v1/health/ready
```

## Module Health Endpoints

```text
/api/v1/auth/health
/api/v1/analytics/health
/track/health
/unsubscribe/health
/preferences/health
/webhooks/health
```

---

# Security & Operational Hardening

The platform includes:

- Structured request logging
- Security headers
- Trusted host validation
- Request size limits
- Rate limiting
- Suppression enforcement
- JWT authentication
- Role-based authorization
- Queue retry isolation
- Production configuration validation

---

# AWS Infrastructure Requirements

The deployment expects:

- Verified SES identities
- SNS event topics
- SQS queues and DLQs
- S3 storage buckets
- IAM access policies

---

# API Documentation

Interactive API specifications:

```text
https://email-campaign-api-clwb.onrender.com/docs
https://email-campaign-api-clwb.onrender.com/redoc
https://email-campaign-api-clwb.onrender.com/openapi.json
```

---

# Testing Coverage

## Backend Coverage

- Authentication
- RBAC validation
- Campaign workflows
- Analytics processing
- Queue retry behavior
- Worker orchestration
- Tracking and unsubscribe handling

## Frontend Validation

- Type checking
- Linting
- Production build validation

---

# Current Runtime Status

- Backend deployed on Render
- Frontend deployed on Netlify
- PostgreSQL provisioned
- Redis provisioned
- AWS SES/SQS/SNS integrated
- CI/CD workflows operational
- Runtime stabilization in progress

---

# Deployment Status

The platform is structured for production-oriented deployment workflows with integrated infrastructure support across:

- Render
- Netlify
- PostgreSQL
- Redis
- AWS SES/SQS/SNS/S3

Core application flows, queue infrastructure, analytics processing, and deployment descriptors are operationally integrated and deployment-ready.

---
