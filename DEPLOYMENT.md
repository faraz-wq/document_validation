# POC Deployment Guide Template (Local + Cloud Run)

## 0) Document Control

* **POC Name:** Document Validation Service
* **Repo:** https://github.com/techbharat-ai/documentValidation.git
* **Owner/Maintainer:** <NAME + TEAM>
* **Last Updated:** 2026-02-03
* **Environments:** dev | prod

---

## 1) System Overview

### 1.1 What this POC does

* **Problem statement:** Extract structured data from uploaded documents and validate it against application-specific rules.
* **Primary APIs/UI:** REST (FastAPI). Frontend is referenced as a git submodule (`data-extraction-hub`) but is not present in this checkout.
* **Key dependencies:** PostgreSQL, Redis (Celery broker/result backend for async endpoints), Google Cloud Vision OCR, Vertex AI Gemini, Google Cloud Storage (optional).

### 1.2 High-level Architecture

* **Compute:** Docker container. Local via Docker Compose or Docker run. Cloud via Cloud Run.
* **Data plane:** PostgreSQL for persistence. Optional GCS for document storage.
* **AI plane:** Vertex AI Gemini (`gemini-2.5-flash`) for extraction, Cloud Vision OCR for text extraction.

---

## 2) Standard Software Stack (Fill This Per POC)

### 2.1 Runtime & Framework

| Component        | Version           | Purpose        | Notes               |
| ---------------- | ----------------: | -------------- | ------------------- |
| OS base image    | python:3.12-slim   | Container base | Debian-based image  |
| Language runtime | Python 3.12        | App runtime    | From base image     |
| Web framework    | FastAPI 0.125.0    | API server     | requirements.txt    |
| Process manager  | Uvicorn 0.38.0     | Serving        | Dockerfile CMD      |
| Task queue       | Celery 5.4.0       | Async tasks    | requirements.txt    |

### 2.2 Data & Infra Services

| Service          | Version                 | Local Option                 | GCP Option                          | Notes |
| ---------------- | ----------------------: | ---------------------------- | ----------------------------------- | ----- |
| Database         | PostgreSQL (not pinned) | External Postgres instance   | Cloud SQL (Postgres)                | SQLAlchemy + Alembic migrations |
| Cache/Queue      | Redis (not pinned)      | External Redis instance      | Memorystore for Redis (if used)     | Celery broker/result backend |
| Object storage   | GCS client 3.7.0         | Local filesystem (default)   | Cloud Storage (if GCS_BUCKET_NAME)  | GCS used only when enabled |

### 2.3 AI/LLM & Models

| Capability               | Provider            | Model/Version         | Where used                           | Notes |
| ------------------------ | ------------------- | --------------------- | ------------------------------------ | ----- |
| LLM (text/chat)          | Vertex AI           | gemini-2.5-flash       | Universal extraction workflow        | Hardcoded in `app/verification/processor.py` |
| OCR/Vision               | Cloud Vision API    | document_text_detection | OCR for PDFs/images                  | `app/ocr/google_vision.py` |
| Embeddings               | -                   | -                     | -                                    | Not used in this repo |
| OSS alternative (if any) | -                   | -                     | -                                    | Not present in this repo |

---

## 3) Repo & Configuration Conventions

### 3.1 Repository Layout (current)

```
/app
/alembic
/Dockerfile
/docker-compose.yml
/requirements.txt
/.env.example
/data-extraction-hub   (git submodule, empty unless initialized)
/tests
```

### 3.2 Configuration Strategy

* Environment variables are used throughout the backend.
* Local: Docker Compose reads `.env` automatically if present.
* No Secret Manager integration is defined in this repo.

---

## 4) Prerequisites

### 4.1 Local prerequisites

* Docker Engine and Docker Compose
* PostgreSQL server reachable via `DATABASE_URL` or `DB_*`
* Redis server if using async endpoints (`/validate-form-async`)
* Google Cloud credentials for Vertex AI, Vision, and GCS (ADC or `GOOGLE_APPLICATION_CREDENTIALS`)
* `poppler-utils` only if running outside Docker (required by `pdf2image`)

### 4.2 GCP prerequisites (per environment)

* GCP project and region
* Cloud Run and Artifact Registry enabled
* Vertex AI API enabled
* Cloud Vision API enabled
* Cloud Storage API enabled if using GCS
* Cloud SQL (Postgres) if using a managed database
* Memorystore for Redis if using async endpoints on GCP

### 4.3 IAM (least privilege baseline)

* Runtime service account requires access to Vertex AI, Cloud Vision, Cloud Storage, and Cloud SQL if those services are used.

---

## 5) Local Deployment (Docker)

### 5.1 Environment setup

1. Copy env template:

   ```bash
   cp .env.example .env
   ```
2. Fill required variables (see Section 9).

### 5.2 Run with Docker Compose

```bash
docker compose up --build
```

### 5.3 Run single container (backend only)

```bash
docker build -t document-validation:local .
docker run --rm -p 8000:8000 --env-file .env document-validation:local
```

### 5.4 Health check

* Endpoint: `GET http://localhost:8000/health`
* Expected: `200 OK` with database status

### 5.5 Common local issues

* Database not reachable or missing env vars (`DATABASE_URL` or `DB_*`).
* Redis not running when using async endpoints.
* Missing Google credentials for Vertex AI, Vision, or GCS.
* `docker-compose.yml` references `./document_validation` and `./data-extraction-hub`; those paths are not present in this checkout.

---

## 6) Cloud Deployment (Cloud Run)

### 6.1 Build & push container image

```bash
gcloud config set project <PROJECT_ID>
gcloud auth login
gcloud auth configure-docker <REGION>-docker.pkg.dev

gcloud builds submit --tag <REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/document-validation:<TAG>
```

### 6.2 Deploy to Cloud Run

```bash
gcloud run deploy document-validation \
  --image <REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/document-validation:<TAG> \
  --region <REGION> \
  --platform managed \
  --port 8000 \
  --set-env-vars ENV=production,GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,GOOGLE_CLOUD_LOCATION=<REGION>
```

### 6.3 Environment variables

* Cloud Run deployment uses environment variables for configuration.
* No Secret Manager integration is defined in this repo.

### 6.4 Networking (only if needed)

* Cloud SQL Unix socket mode is enabled by `INSTANCE_CONNECTION_NAME`.
* Redis access on GCP requires network connectivity to the Redis instance.

### 6.5 Scaling & performance knobs (document per POC)

* No Cloud Run scaling configuration is defined in this repo.

---

## 7) Data Services Deployment Templates (Per Service)

### 7.1 PostgreSQL

* **Local:** Configure with `DATABASE_URL` or `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`.
* **Cloud:** Cloud SQL supported via `INSTANCE_CONNECTION_NAME` which switches to `/cloudsql/<INSTANCE_CONNECTION_NAME>` socket path.
* **Migrations:** Alembic is used. `docker-compose.yml` runs `alembic upgrade head` in the backend entrypoint.

### 7.2 Redis (Celery)

* **Local:** Configure `REDIS_URL` or set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`.
* **Cloud:** Memorystore for Redis if using async endpoints.

---

## 8) AI / LLM Integration (Gemini + Alternatives)

### 8.1 Gemini via Vertex AI (GCP-native)

* Features calling Gemini: Universal extraction workflow in `app/verification/processor.py`.
* Model used: `gemini-2.5-flash`.
* Region: `GOOGLE_CLOUD_LOCATION` (defaults to `us-central1`).
* Auth: Application Default Credentials via service account.

### 8.2 RAG (if applicable)

* Not used in this repo.

### 8.3 Offline / OSS model alternative (if supported)

* Not present in this repo.

---

## 9) Environment Variables Template (Per POC)

### 9.1 Required

| Variable                  | Example                     | Required? | Used by           | Notes |
| ------------------------- | --------------------------- | --------: | ----------------- | ----- |
| `DATABASE_URL`            | `postgresql://...`          | ✅        | DB connection     | Alternative to `DB_*` vars |
| `DB_USER`                 | `postgres`                  | ✅ (if no `DATABASE_URL`) | DB connection | Used when `DATABASE_URL` is not set |
| `DB_PASSWORD`             | `...`                       | ✅ (if no `DATABASE_URL`) | DB connection | Used when `DATABASE_URL` is not set |
| `DB_HOST`                 | `localhost`                 | ✅ (if no `DATABASE_URL`) | DB connection | Used when `DATABASE_URL` is not set |
| `DB_PORT`                 | `5432`                      | ✅ (if no `DATABASE_URL`) | DB connection | Used when `DATABASE_URL` is not set |
| `DB_NAME`                 | `doc_val`                   | ✅ (if no `DATABASE_URL`) | DB connection | Used when `DATABASE_URL` is not set |
| `SECRET_KEY`              | `...`                       | ✅ (prod) | JWT auth          | Defaults to insecure value if not set |
| `GOOGLE_CLOUD_PROJECT`    | `<PROJECT_ID>`              | ✅        | Vertex AI init    | Required for Gemini usage |

### 9.2 Optional but used in code

* `INSTANCE_CONNECTION_NAME` (Cloud SQL socket mode)
* `ENV` (`production` enables larger DB pools)
* `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
* `SQL_ECHO` (set `true` to log SQL)
* `REDIS_URL` (Celery broker/result backend default)
* `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
* `GCS_BUCKET_NAME` (enables GCS storage)
* `GCS_DOCUMENTS_PREFIX` (default `documents/`)
* `GOOGLE_CLOUD_LOCATION` (defaults to `us-central1`)
* `MAX_FILE_SIZE_BYTES` (default 50MB)
* `MAX_TOTAL_SIZE_BYTES` (default 100MB)
* `FILE_CLEANUP_INTERVAL_MINUTES` (default 60)
* `FILE_RETENTION_HOURS` (default 24)
* `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30)
* `REFRESH_TOKEN_EXPIRE_DAYS` (default 7)
* `GOOGLE_APPLICATION_CREDENTIALS` (if not using ADC)
* `VITE_API_BASE_URL` (frontend only, referenced in `docker-compose.yml`)

---

## 10) CI/CD Template (Pick One)

* No CI/CD workflow files are present in this repo.

---

## 11) Observability & Ops

* Logs: stdout + rotating file log `logs/app.log` (created by `app/logging_config.py`).
* Health endpoint: `GET /health`.
* Admin endpoints (auth required): `/v1/admin/system-health`, `/v1/admin/pool-stats`, `/v1/admin/cleanup-stats`.

---

## 12) Security Checklist (Minimum)

* `SECRET_KEY` must be set (default is insecure).
* JWT auth is enforced for v1 endpoints (see `/v1/auth/*`).
* File size and MIME type validation enforced in `app/utils/file_validator.py`.
* CORS allowlist is hardcoded in `app/main.py`.

---

## 13) Troubleshooting Runbook (Template)

* **Symptom:** `500` or DB errors on startup
* Check: `DATABASE_URL` or `DB_*` values, DB reachability, Cloud SQL socket configuration if using `INSTANCE_CONNECTION_NAME`.

* **Symptom:** Gemini or Vision API errors
* Check: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, service account permissions, APIs enabled.

* **Symptom:** Async validation tasks stay pending
* Check: Redis connectivity and Celery worker availability.

* **Symptom:** GCS upload/download errors
* Check: `GCS_BUCKET_NAME`, service account permissions, bucket existence.

* **Symptom:** `docker compose up` fails to build backend/frontend
* Check: `docker-compose.yml` build contexts reference `./document_validation` and `./data-extraction-hub`.

---

# “Per-Service End-to-End Guide” Checklist (What your devs are asking for)

This repo currently contains one backend service (Document Validation Service) and references a frontend submodule that is not present in this checkout.

1. **What it is + endpoints**
Service: Document Validation Service (FastAPI)
Endpoints:
```text
GET /health
POST /validate-form
POST /validate-form-json
GET /validate-form/rules/{application_type}
GET /validate-form/supported-types
POST /validate-form-async
GET /validate-form-async/{task_id}
GET /validate-form-async/user/tasks
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/token
POST /v1/auth/refresh
POST /v1/auth/logout
GET /v1/me/sessions
GET /v1/me/sessions/{session_id}
GET /v1/me/sessions/{session_id}/documents/{filename}
GET /v1/validation-sessions
GET /v1/validation-sessions/{validation_id}
DELETE /v1/validation-sessions/{validation_id}
GET /v1/validation-sessions/stats/summary
POST /v1/validation-sessions/{validation_id}/feedback
GET /v1/validation-configs
GET /v1/validation-configs/{application_type}
POST /v1/validation-configs
PUT /v1/validation-configs/{application_type}
DELETE /v1/validation-configs/{application_type}
GET /v1/validation-configs/{application_type}/export
GET /v1/admin/system-health
GET /v1/admin/pool-stats
GET /v1/admin/cleanup-stats
POST /v1/admin/cleanup-trigger
```

2. **Exact stack versions (runtime + DB + cache + AI)**
Runtime: Python 3.12 (base image `python:3.12-slim`)
Framework: FastAPI 0.125.0, Uvicorn 0.38.0
DB: PostgreSQL (server version not pinned in repo)
Cache/Queue: Redis (server version not pinned in repo), Celery 5.4.0
AI: Vertex AI Gemini `gemini-2.5-flash`, Cloud Vision OCR

3. **Local deploy steps (compose + env vars + health check)**
```bash
cp .env.example .env
docker compose up --build
```
Health check: `GET http://localhost:8000/health`

4. **Cloud Run deploy steps (build/push/deploy + secrets + IAM)**
```bash
gcloud builds submit --tag <REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/document-validation:<TAG>
gcloud run deploy document-validation --image <REGION>-docker.pkg.dev/<PROJECT_ID>/<AR_REPO>/document-validation:<TAG> --region <REGION> --platform managed --port 8000 --set-env-vars ENV=production,GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,GOOGLE_CLOUD_LOCATION=<REGION>
```
Secrets: environment variables only (no Secret Manager integration in repo)
IAM: service account needs access to Vertex AI, Vision, Storage, and Cloud SQL if used

5. **External dependencies (DB, Redis, Storage, Vertex AI)**
PostgreSQL, Redis (for async endpoints), Cloud Storage (optional), Vertex AI (Gemini), Cloud Vision API

6. **Rollback procedure (previous image tag redeploy)**
Redeploy the last known-good container image tag to Cloud Run.

7. **Known pitfalls + logs/dashboards**
`docker-compose.yml` build contexts reference `./document_validation` and `./data-extraction-hub`.
Frontend is a git submodule and is empty unless initialized.
Async endpoints require Redis and a Celery worker.
Logs: local `logs/app.log` and Cloud Run logs in Cloud Logging.
