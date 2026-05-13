# rag-docs-chatbot

Work-in-progress RAG chatbot over a corpus of papers.

This README documents what is wired up so far and how to run it
locally. It grows as the project does.

## Stack

| Layer | Choice |
|---|---|
| Web framework | Django 6.0 |
| Config | `django-environ` (12-factor `.env`) |
| Database | PostgreSQL 18 (driver: `psycopg[binary]`) |

DRF, pgvector, embeddings and the agent orchestrator are not wired up
yet.

## Prerequisites

- Python 3.12+
- Docker (only to run Postgres locally for now)
- Git

## Setup

### 1. Clone and create the virtualenv

```powershell
git clone <repo-url> rag-docs-chatbot
cd rag-docs-chatbot/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks `Activate.ps1`, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. Configure environment variables

Copy the example file and fill it in:

```powershell
Copy-Item ..\.env.example ..\.env
```

Minimum variables required at this stage:

```env
DJANGO_SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres:postgres@localhost:5432/rag
```

The `.env` lives at the **repo root** (not inside `backend/`) and is
gitignored.

### 3. Start Postgres

```powershell
docker run --name rag-pg `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_DB=rag `
  -p 5432:5432 -d postgres:18
```

### 4. Install Postgres extensions and migrate

```powershell
python manage.py init_extensions
python manage.py migrate
python manage.py createsuperuser
```

`init_extensions` installs `vector` (for embeddings) and `pg_trgm`
(for lexical search) on the database referenced by `DATABASE_URL`.
It must run before `migrate`, because the KB schema declares a
`vector(384)` column.

### 5. Run the dev server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` and log in.

## Project structure

```
rag-docs-chatbot/
|-- .env.example              # contract: required env vars
|-- .gitignore
|-- LICENSE                   # MIT
|-- README.md
|-- backend/
|   |-- manage.py
|   |-- requirements.txt
|   |-- config/               # Django project (settings, urls, wsgi, asgi)
|   `-- agent/                # Single app: models, admin, views, urls
|       |-- kb/               # Ingestion, search (semantic + lexical + RRF), reranker
|       |-- memory/           # Embeddings helper
|       `-- management/       # Custom manage.py commands
|-- eval/
`-- papers/                   # PDFs gitignored
```

## Common commands

```powershell
python manage.py check          # validate settings, no DB access
python manage.py makemigrations # generate migration files from model changes
python manage.py migrate        # apply migrations to the DB
python manage.py shell          # interactive Django shell
python manage.py runserver      # dev server on :8000
```

## Conventions

- **Commits**: Conventional Commits (`feat(scope): ...`, `chore: ...`,
  imperative mood, <=72 chars on the subject line).
- **Never commit** `.env`, `db.sqlite3`, `.venv/`, or `papers/*.pdf`.

## License

MIT. See [`LICENSE`](./LICENSE).
