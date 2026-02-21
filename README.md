# Salt — Tax Automation Platform

Monorepo containing the backend API, frontend SPA, and infrastructure configuration for the Salt Tax Automation platform.

```
salt/
├── backend/    # FastAPI 0.115+ (Python 3.12)
├── frontend/   # React 18 + TypeScript 5 (Vite)
└── infra/      # Docker Compose & deployment config
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 24+ |
| Docker Compose | v2 (bundled with Docker Desktop) |
| Python | 3.12 |
| Node.js | 20 LTS |
| Git | any recent |

---

## Local Setup

### 1. Clone & configure environment

```bash
git clone <repo-url> salt
cd salt
cp .env.example .env
```

Open `.env` and fill in every placeholder value. At minimum, set:

- `SECRET_KEY` — any long random string (`openssl rand -hex 32`)
- `FERNET_KEY` — see comment in `.env.example` for generation command
- `OPENAI_API_KEY` — your OpenAI key
- `AZURE_DI_ENDPOINT` / `AZURE_DI_KEY` — Azure Document Intelligence resource
- `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` / `MICROSOFT_TENANT_ID` — Azure AD app registration
- `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_JWT_SECRET` — Supabase project
- `SENDGRID_API_KEY` — SendGrid API key (or switch `EMAIL_PROVIDER=smtp`)

### 2. Start all services

```bash
docker compose -f infra/docker-compose.yml up --build
```

This starts nine services:

| Service | URL |
|---------|-----|
| API (FastAPI) | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Frontend (React) | http://localhost:3000 |
| Flower (Celery monitor) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Run database migrations

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
```

### 4. Verify the stack

```bash
# API health check
curl http://localhost:8000/health

# Frontend (opens in browser)
open http://localhost:3000
```

---

## Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Celery workers

```bash
# In separate terminals from the backend/ directory:
celery -A app.worker worker -Q ingestion  --pool=gevent  -c 20  --loglevel=info
celery -A app.worker worker -Q extraction --pool=gevent  -c 100 --loglevel=info
celery -A app.worker worker -Q routing    --pool=prefork -c 8   --loglevel=info
celery -A app.worker worker -Q notification --pool=gevent -c 4  --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # Vite dev server on http://localhost:5173
```

---

## Project Structure (expanded)

```
salt/
├── .env.example          # All required environment variable keys
├── .gitignore
├── README.md
│
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI app factory
│   │   ├── worker.py     # Celery app factory
│   │   ├── api/          # Route handlers
│   │   ├── services/     # Business logic
│   │   ├── models/       # SQLAlchemy ORM models
│   │   └── tasks/        # Celery task modules
│   ├── alembic/          # Database migrations
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/   # shadcn/ui + custom components
│   │   ├── pages/        # react-router-dom route pages
│   │   ├── hooks/        # TanStack Query hooks
│   │   └── lib/          # Axios client, utilities
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
│
└── infra/
    ├── docker-compose.yml
    ├── nginx/            # Reverse proxy config (production)
    └── scripts/          # DB seed, migration helpers
```

---

## Environment Variables

See [.env.example](.env.example) for the full list with descriptions.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115+, Python 3.12 |
| ORM | SQLAlchemy (async) + asyncpg |
| Database | PostgreSQL 16 |
| Task queue | Celery 5.4+ |
| Broker / cache | Redis 7 |
| Auth | Supabase Auth (JWT HS256) |
| OCR Tier 1 | pdfplumber (native PDFs) |
| OCR Tier 2 | Azure Document Intelligence |
| OCR Tier 3 | OpenAI gpt-4o-mini / gpt-4o |
| Frontend | React 18, TypeScript 5, Vite |
| UI | shadcn/ui, Radix UI, Tailwind CSS |
| Data grid | TanStack Table v8 |
| Data fetching | TanStack React Query |
| Storage | Local FS (prototype) → Azure Blob (production) |
| Email | SendGrid |
| Containers | Docker Compose v2 |
