# Orbis Video Studio AI - Backend Foundation

Backend core framework and relational domain database foundation.

## Technology Stack

- **Python**: 3.11+ / 3.12
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **Migrations**: Alembic
- **Database**: PostgreSQL 16
- **Validation**: Pydantic / Pydantic-Settings
- **Test Runner**: pytest

## Developer Quick Start

### Local Development Setup

1. **Install Dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run Tests:**
   ```bash
   pytest
   ```

3. **Database Migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start Application Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Docker Compose Setup

Run backend and PostgreSQL database in containerized developer environment:

```bash
docker compose up --build
```

Health endpoints will be available at:
- `http://localhost:8000/health`
- `http://localhost:8000/api/v1/health`


## WP007 generation queue

Start the worker explicitly with `python -m app.services.generation_worker` after
applying migrations. Importing or starting the API does not start provider work.
Configure provider credentials only on the server. Automated tests mock all HTTP.

1. `POST /api/v1/jobs` persists a `PENDING` job. Optional reference images use the
   provider-neutral `reference_images` array; custom parameters cannot override
   the server model or carry secret-like keys/values.
2. `POST /api/v1/queue/claim` returns a random `claim_token` and a 120-second lease.
3. `POST /api/v1/jobs/{id}/dispatch` requires `{"claim_token": "..."}`. The token
   must own a live claim. The database commits `SUBMITTING` and an attempt marker
   before HTTP. The token is omitted from ordinary job API responses.
4. `POST /api/v1/jobs/{id}/poll` observes persisted scheduling. Polls are at least
   10 seconds apart and fenced against concurrent callers. The worker performs
   these operations for due jobs automatically.
5. `POST /api/v1/jobs/{id}/cancel` cancels pending/claimed work locally, or calls
   the provider-neutral adapter for known active provider jobs. Terminal requests
   are no-ops; submitting/polling/cancelling jobs cannot race another operation.

Safe transient failures use deterministic backoff of 5, 10, 20, ... seconds,
with a 300-second cap and a persisted retry budget (default 3 total failed
attempts). Poll retries also respect the 10-second minimum interval. A known
provider identity is never submitted again. HTTP 400/401/403, configuration,
validation and provider rejection failures do not retry.

Connection failures known to occur before sending and HTTP 429 can retry
submission. Read/write timeouts, ambiguous HTTP 5xx and process death during
submission enter `RECONCILIATION_REQUIRED`; these cannot be blindly resubmitted.
Status requests can retry eligible HTTP 5xx/network failures because they do not
create chargeable work. Poll exhaustion also requires reconciliation.

`POST /api/v1/queue/recover` reclaims expired unused claims, resumes expired poll
leases, and quarantines ambiguous submission/cancellation leases. A still-live
lease is not disturbed. Reconciliation is a manual operator gate: verify provider
identity/outcome before any separately authorized repair. This WP intentionally
provides no automatic reset/requeue endpoint for ambiguous work.

Migration `007_queue_safety` adds ownership, lease, attempt and schedule fields.
It drops legacy untrusted provider results/error text, preserves clean request
payloads, and quarantines unsafe payloads or in-flight jobs lacking identity.
Downgrade removes the fields but does not undo quarantine or restore discarded
untrusted data. Provider output URLs remain job metadata; no Asset is fabricated.

Vidu mappings were checked against the published text-to-video,
reference-to-video, get-generation and cancel-generation documentation on
2026-09-06. The default `viduq2` supports both implemented generation paths.
No live Vidu validation is performed or required for this work package.
