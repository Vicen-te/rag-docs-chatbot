# rag-docs-chatbot

Work-in-progress RAG chatbot over a corpus of papers.

This README documents what is wired up so far and how to run it.

## Stack

| Layer | Choice |
|---|---|
| Web framework | Django 6.0 + DRF |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Config | `django-environ` (12-factor `.env`) |
| Database | PostgreSQL 18 + `pgvector` + `pg_trgm` |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 384-dim) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM | Ollama via OpenAI-compatible client |
| Orchestrator | LangGraph |
| Tracing (optional) | LangSmith |

## Two ways to run

- **All-in-one Docker stack** (db + redis + ollama + backend) -- see
  the *Docker* section below.
- **Local Python with Postgres in Docker** -- the original dev flow,
  documented next.

## Local setup

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

Minimum variables:

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
  -p 5432:5432 -d pgvector/pgvector:pg18
```

### 4. Install Postgres extensions and migrate

```powershell
python manage.py init_extensions
python manage.py makemigrations agent
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run Ollama and pull a model

```powershell
ollama serve
ollama pull llama3.2:3b
```

### 6. Run the dev server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` and log in.

## Docker stack

The repo ships a `docker-compose.yml` with `db` (pgvector image),
`redis`, `ollama` and `backend`. The backend container runs
`init_extensions`, `makemigrations` and `migrate` on startup before
serving with gunicorn.

```powershell
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec backend python manage.py createsuperuser
```

Backend listens on `http://localhost:8000`. Postgres is exposed on
`5433` (not `5432`, to avoid clashing with a native install).

## Ingesting a corpus

Drop your PDFs/DOCX/HTML/TXT/MD files under `papers/` and run:

```powershell
python manage.py ingest_papers ../papers/
```

The command walks the tree, deduplicates by SHA-256 of the file
content, and persists chunks + embeddings. Re-running is safe; already
ingested files are reported as duplicates.

## API endpoints (require JWT)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/token/` | Obtain access + refresh token |
| `POST` | `/api/token/refresh/` | Refresh access token |
| `POST` | `/api/agent/chat/` | Chat with the agent (SSE stream) |
| `GET`  | `/api/agent/kb/search/?query=...&mode=hybrid` | Raw retrieval |
| `GET`, `POST` | `/api/agent/memory/semantic/` | List or create memory facts |
| `GET`, `PUT`, `DELETE` | `/api/agent/memory/semantic/<uuid>/` | Per-fact CRUD |
| `GET` | `/api/agent/conversations/` | List user conversations |
| `GET`, `DELETE` | `/api/agent/conversations/<uuid>/` | Detail or delete |
| `POST` | `/api/agent/feedback/` | Thumbs up / down on a message |

## Tunables

All knobs live in `.env` -- see `.env.example` for the full list with
defaults. The most impactful ones:

- `OLLAMA_MODEL` -- pick a bigger or smaller LLM.
- `AGENT_TOP_K` -- how many KB chunks feed the synthesis prompt.
- `KB_SEMANTIC_WEIGHT` / `KB_LEXICAL_WEIGHT` -- bias of the hybrid
  fusion (must sum to roughly 1.0).
- `AGENT_MAX_VERIFY_RETRIES` -- set to `0` to skip the verifier loop.

Prompts live in `backend/agent/orchestrator/prompts.py`.

## Project structure

```
rag-docs-chatbot/
|-- .env.example              # contract: required env vars
|-- .gitignore
|-- LICENSE                   # MIT
|-- README.md
|-- docker-compose.yml
|-- backend/
|   |-- Dockerfile
|   |-- manage.py
|   |-- requirements.txt
|   |-- config/               # Django project (settings, urls, wsgi, asgi)
|   `-- agent/                # Single app
|       |-- kb/               # Ingestion, search (semantic + lexical + RRF), reranker
|       |-- memory/           # Embeddings helper + read/write API
|       |-- orchestrator/     # Prompts, LLM client, router, guardrails, LangGraph
|       |-- tools/            # Tool registry exposed to the agent
|       `-- management/       # Custom manage.py commands
|-- eval/
`-- papers/                   # PDFs gitignored
```

## Common commands

```powershell
python manage.py check
python manage.py init_extensions
python manage.py makemigrations
python manage.py migrate
python manage.py ingest_papers ../papers/
python manage.py shell
python manage.py runserver
```

## Conventions

- **Commits**: Conventional Commits (`feat(scope): ...`, `chore: ...`,
  imperative mood, <=72 chars on the subject line).
- **Never commit** `.env`, `db.sqlite3`, `.venv/`, or `papers/*.pdf`.

## License

MIT. See [`LICENSE`](./LICENSE).
