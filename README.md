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
| LLM | Ollama native API or any OpenAI-compatible endpoint (`LLM_PROVIDER`) |
| Orchestrator | LangGraph (corrective-RAG: router + retrieve + synthesise + verify loop) |
| Frontend | React + Vite SPA, SSE token streaming |
| Eval (optional) | Custom harness + Ragas metrics |
| Tracing (optional) | LangSmith |

## Two ways to run

- **All-in-one Docker stack** (db + redis + ollama + backend) -- see
  the *Docker* section below.
- **Local Python with Postgres in Docker** -- the dev flow documented
  next.

Either way the backend exposes a JSON/SSE API. The chat UI is a
separate React + Vite app under `frontend/` (see *Frontend* below);
the Django admin at `/admin/` is enough to poke the data without it.

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
ollama pull qwen3.5:9b
```

### 6. Run the dev server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` and log in to inspect data, or
start the frontend below for the chat UI.

## Frontend

A React + Vite single-page app under `frontend/`: a login form
(`/api/token/`) and a chat view that streams the agent's answer over
SSE from `/api/agent/chat/`, rendering the agent's step trace
(retrieve / synthesise / verify) as it runs.

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*`
to `http://127.0.0.1:8000`, so the backend must be running first.

## Docker stack

The repo ships a `docker-compose.yml` with `db` (pgvector image),
`redis`, `ollama` and `backend`. The backend container runs
`init_extensions`, `makemigrations` and `migrate` on startup before
serving with gunicorn.

```powershell
docker compose up -d --build
docker compose exec ollama ollama pull qwen3.5:9b
docker compose exec backend python manage.py createsuperuser
```

Backend listens on `http://localhost:8000`. Postgres is exposed on
`5433` (not `5432`, to avoid clashing with a native install).

### GPU access

Both `ollama` and `backend` declare an NVIDIA device reservation, so
they pick up a host GPU when available. Requirements on the host:

- Recent NVIDIA drivers.
- Docker Desktop 4.x+ (ships the NVIDIA Container Toolkit) or
  `nvidia-container-toolkit` installed manually on Linux / WSL2.

Verify the host -> container hand-off:

```powershell
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

Once the stack is up, confirm each service sees the GPU:

```powershell
docker compose exec ollama nvidia-smi
docker compose exec backend python -c "import torch; print('cuda:', torch.cuda.is_available())"
```

If you do not have an NVIDIA GPU, remove the `deploy.resources.reservations`
blocks from `ollama` and `backend` in `docker-compose.yml` -- the rest
of the stack runs on CPU without changes.

## Ingesting a corpus

Drop your PDFs/DOCX/HTML/TXT/MD files under `papers/` and run:

```powershell
python manage.py ingest_papers ../papers/
```

The command walks the tree, deduplicates by SHA-256 of the file
content, and persists chunks + embeddings. Re-running is safe; already
ingested files are reported as duplicates.

## Evaluating the RAG

A small harness in `eval/dataset.jsonl` (25 questions across
`single_hop`, `multi_hop`, `detail_tech`, `synthesis` and `negative`
categories) drives the same code paths as the chat API. Run it after
ingestion:

```powershell
$env:HF_HUB_OFFLINE = "1"; $env:TRANSFORMERS_OFFLINE = "1"
python manage.py eval_run
```

Each run writes `eval/results/<timestamp>/summary.md` (aggregate)
and `per_question.jsonl` (full answers and per-question metrics).

### Metrics

| metric | what it measures |
|---|---|
| `retrieval hit@k` | the expected paper appears in the top-k retrieved |
| `retrieval recall` | fraction of expected papers actually retrieved |
| `answer keyword hit` | the answer contains all `must_include` tokens |
| `answer cites a doc` | the answer carries a `[doc:UUID]` citation |
| `negatives abstained correctly` | off-corpus questions are refused, not invented |

### Healthy ranges

For this corpus (13 ML papers) and `qwen3.5:9b`:

| category | fine | needs work |
|---|---|---|
| single_hop hit@k | >= 95% | < 85% |
| multi_hop recall | >= 70% | < 50% |
| detail_tech kw hit | >= 70% | < 50% |
| synthesis kw hit | >= 60% | < 40% |
| negative abstain ok | >= 80% | < 60% |

If `single_hop` is high and `negative abstain` is high, retrieval is
doing its job. The other categories are tuning surface.

### Is the LLM actually using retrieval?

A 9B model already knows the famous papers in this corpus. A correct
answer, on its own, is not proof that retrieval contributed anything.
Three checks, ordered by cost:

1. **Negative category**. `neg-*` questions ask about content that is
   not in the corpus (e.g. "SAM 3", "yesterday's NVIDIA stock
   price"). If the model answers them with confidence instead of
   abstaining, it is leaking pretraining. A high
   `negatives abstained correctly` score is the cheapest evidence
   that answers are gated on the retrieved context.

2. **Citations**. Every grounded answer should carry a `[doc:UUID]`
   tag. The `answer cites a doc` metric tracks this. An answer
   without a citation is either off-corpus or the model bypassed the
   context.

3. **Paper-specific probes**. Ask for something only the paper
   contains -- a number from a table, an obscure ablation result, an
   exact named component. If the model returns the value verbatim
   **and** cites the right doc, the pipeline is using retrieval. A
   plausible-but-wrong number means it hallucinated.

In practice: run the eval, then open the API or frontend and fire
two or three paper-specific questions that are not in the dataset.
If the citations point at the right paper and the answer reuses
terminology from that paper, the RAG generalises beyond the eval
sample.

### Signs the RAG is misbehaving

- Answers without `[doc:...]` citations on questions whose answer is
  in the corpus -- the model is bypassing the retrieved context.
- High `retrieval hit@k` but low `answer keyword hit` -- retrieval
  finds the paper, the synthesis prompt is not using it. Check the
  prompts in `backend/agent/orchestrator/prompts.py` and
  `OLLAMA_NUM_CTX` (chunks may be getting truncated).
- Confident answers to `neg-*` questions -- the verifier is too
  lenient or the system prompt does not enforce abstention.
- Citations that point at the wrong document -- retrieval brings
  irrelevant chunks. Try `AGENT_USE_RERANKER=true` or rebalance
  `KB_SEMANTIC_WEIGHT` / `KB_LEXICAL_WEIGHT`.

### Iterating

Change one knob at a time, re-run the eval, diff the summaries:

- weak `multi_hop` -> raise `AGENT_TOP_K`, or
  `AGENT_USE_RERANKER=true`.
- weak `detail_tech` -> raise `OLLAMA_NUM_CTX`, or lower
  `KB_CHILD_CHUNK_SIZE` (requires re-ingest).
- weak `synthesis` -> tune prompts in
  `backend/agent/orchestrator/prompts.py`.
- weak `negative` -> tighten the verifier prompt or raise
  `AGENT_MAX_VERIFY_RETRIES`.
- weak `single_hop` (rare once retrieval works at all) -> revisit
  `KB_SEMANTIC_WEIGHT` / `KB_LEXICAL_WEIGHT`.

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

- `LLM_PROVIDER` -- `ollama` (native `/api/chat`, honours `num_ctx`)
  or `openai` (any OpenAI-compatible endpoint).
- `OLLAMA_MODEL` -- pick a bigger or smaller LLM.
- `OLLAMA_NUM_CTX` -- context window forwarded to Ollama; raise it
  when retrieved chunks risk truncation.
- `AGENT_TOP_K` -- how many KB chunks feed the synthesis prompt.
- `AGENT_USE_RERANKER` -- enable the cross-encoder reranking pass.
- `KB_SEMANTIC_WEIGHT` / `KB_LEXICAL_WEIGHT` -- bias of the hybrid
  fusion (must sum to roughly 1.0).
- `AGENT_MAX_VERIFY_RETRIES` -- set to `0` to skip the verifier loop.
- `RAGAS_JUDGE_PROVIDER` -- judge LLM for `ragas_run` (`ollama` or
  `openai`).

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
|       `-- management/       # Custom manage.py commands (ingest, eval, ragas)
|-- frontend/                 # React + Vite SPA (login + streaming chat)
|-- eval/                     # dataset.jsonl + generated results/ (gitignored)
`-- papers/                   # PDFs gitignored
```

## Common commands

```powershell
python manage.py check
python manage.py init_extensions
python manage.py makemigrations
python manage.py migrate
python manage.py ingest_papers ../papers/
python manage.py eval_run                          # score retrieval + chat
python manage.py eval_compare <run-a> <run-b>      # diff two runs
python manage.py ragas_run <run-dir>               # Ragas metrics on a run
python manage.py shell
python manage.py runserver
```

## Conventions

- **Commits**: Conventional Commits (`feat(scope): ...`, `chore: ...`,
  imperative mood, <=72 chars on the subject line).
- **Never commit** `.env`, `db.sqlite3`, `.venv/`, or `papers/*.pdf`.

## License

MIT. See [`LICENSE`](./LICENSE).
