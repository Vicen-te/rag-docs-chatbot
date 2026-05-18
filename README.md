# rag-docs-chatbot

A corrective-RAG chatbot over a corpus of deep learning
papers. Hybrid retrieval (pgvector + pg_trgm + RRF) feeds a
LangGraph retrieve -> synthesise -> verify loop; a
deterministic eval harness and Ragas back every number in
this README.

## Table of contents

- [Overview](#overview)
  - [Stack](#stack)
  - [Architecture](#architecture)
  - [Project structure](#project-structure)
- [Getting started](#getting-started)
  - [Two ways to run](#two-ways-to-run)
  - [Local setup](#local-setup)
  - [Frontend](#frontend)
  - [Docker stack](#docker-stack)
- [Usage](#usage)
  - [Ingesting a corpus](#ingesting-a-corpus)
  - [API endpoints (require JWT)](#api-endpoints-require-jwt)
- [Evaluation and results](#evaluation-and-results)
  - [Reproducing the full results](#reproducing-the-full-results)
  - [Metrics](#metrics)
  - [Results](#results)
  - [Healthy ranges](#healthy-ranges)
  - [Is the LLM actually using retrieval?](#is-the-llm-actually-using-retrieval)
  - [Signs the RAG is misbehaving](#signs-the-rag-is-misbehaving)
  - [Iterating](#iterating)
- [Reference](#reference)
  - [Tunables](#tunables)
  - [Observability](#observability)
  - [Common commands](#common-commands)
  - [Conventions](#conventions)
  - [License](#license)

## Overview

### Stack

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
| Tracing (optional) | LangSmith (`@traceable` LLM + LangGraph nodes) |

### Architecture

The agent is a corrective-RAG state machine (LangGraph). `intake`
loads memory, `classify` routes conversational turns away from
retrieval, and the `verify` node loops back to `synthesise` until the
answer is grounded or the retry budget is spent. Rendered from the
compiled graph (`GRAPH.get_graph().draw_mermaid()`):

```mermaid
graph TD;
	__start__([__start__]):::first
	intake(intake)
	classify(classify)
	conversational(conversational)
	retrieve(retrieve)
	synthesise(synthesise)
	verify(verify)
	__end__([__end__]):::last
	__start__ --> intake;
	classify -.-> conversational;
	classify -.-> retrieve;
	intake --> classify;
	retrieve --> synthesise;
	synthesise --> verify;
	verify -. respond .-> __end__;
	verify -. retry .-> synthesise;
	conversational --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

### Project structure

```
rag-docs-chatbot/
|-- .env.example              # contract: required env vars
|-- .gitignore
|-- LICENSE                   # MIT
|-- README.md
|-- docker-compose.yml
|-- docs/                     # README screenshot assets
|-- backend/
|   |-- Dockerfile
|   |-- entrypoint.sh         # migrate + collectstatic + gunicorn
|   |-- manage.py
|   |-- requirements.txt
|   |-- config/               # Django project (settings, urls, wsgi, asgi)
|   `-- agent/                # Single app
|       |-- kb/               # Ingestion, search (semantic + lexical + RRF), reranker
|       |-- memory/           # Embeddings helper + read/write API
|       |-- orchestrator/     # Prompts, LLM client, router, guardrails, LangGraph
|       |-- tools/            # Tool registry exposed to the agent
|       `-- management/       # Custom manage.py commands (ingest, eval, ragas)
|-- frontend/                 # React + Vite SPA (login + streaming chat); nginx Dockerfile
|-- eval/                     # dataset.jsonl + generated results/ (gitignored)
`-- papers/                   # PDFs gitignored
```

## Getting started

### Two ways to run

- **All-in-one Docker stack** (db + redis + ollama + model auto-pull
  + backend + frontend) -- one command, UI on port 80. See the
  *Docker stack* section below.
- **Fully local (no Docker)** -- Python, PostgreSQL 18 (with
  `pgvector` + `pg_trgm`) and Ollama all running natively; the dev
  flow documented next. The React UI runs separately via Vite (see
  *Frontend*).

Either way the backend exposes a JSON/SSE API. In the Docker stack the
React UI is served by nginx and proxies the API; for local dev the
Django admin at `/admin/` is enough to poke the data without the UI.

### Local setup

#### 1. Clone and create the virtualenv

```powershell
git clone <repo-url> rag-docs-chatbot
cd rag-docs-chatbot/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks `Activate.ps1`, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

#### 2. Configure environment variables

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

#### 3. Provision PostgreSQL 18 (pgvector + pg_trgm)

Install PostgreSQL 18 natively. `pg_trgm` ships with the standard
contrib package; `pgvector` is a separate extension -- install it
into that Postgres by following the upstream guide for your platform:
<https://github.com/pgvector/pgvector#installation>. Then create the
database `DATABASE_URL` points at (use the `postgres` superuser
password you set during install -- the `.env` example assumes
`postgres`):

```powershell
psql -U postgres -c "CREATE DATABASE rag;"
```

`init_extensions` (next step) runs `CREATE EXTENSION` for both, so the
extension binaries must already be present on the server.

#### 4. Install Postgres extensions and migrate

```powershell
python manage.py init_extensions
python manage.py makemigrations agent
python manage.py migrate
python manage.py createsuperuser
```

#### 5. Run Ollama and pull a model

```powershell
ollama serve
ollama pull qwen3.5:9b
```

#### 6. Run the dev server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` and log in to inspect data, or
start the frontend below for the chat UI.

### Frontend

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
For a no-Node setup the Docker stack builds and serves this same SPA
behind nginx on port 80 -- see *Docker stack*.

The UI surfaces the agent's behaviour directly: the collapsible
"process" panel shows the graph's steps, answers render Markdown +
KaTeX, and every grounded claim carries a `[doc:<name>]` citation.
The four behaviours the eval exercises, in the product:

| | |
|---|---|
| Conversational routing -- no retrieval | Single-hop, one source (rendered KaTeX) |
| ![chitchat routed to the conversational node, no retrieve step](docs/ui-conversational.png) | ![single-hop answer citing one paper with a rendered formula](docs/ui-single-hop.png) |
| Multi-hop, two sources | Abstention on an off-corpus question |
| ![multi-hop answer citing vit.pdf and attention.pdf](docs/ui-multi-hop.png) | ![the model refuses an off-corpus question instead of inventing](docs/ui-abstain.png) |

The corrective loop is visible to the user too -- `verify` rejects
the first draft and the answer is revised before it is shown
(`retry 1 ... accepted after 2` in the step trace):

![the corrective retry loop shown in the chat UI step trace](docs/ui-corrective.png)

### Docker stack

The repo ships a `docker-compose.yml` with `db` (pgvector), `redis`,
`ollama`, `backend` (gunicorn behind a shared entrypoint that runs
`init_extensions`, `makemigrations`, `migrate` and `collectstatic`)
and `frontend` (the React SPA built and served by nginx). One command
brings up the whole stack:

```powershell
docker compose up -d --build
```

The `ollama` service serves and, on first boot, pulls `OLLAMA_MODEL`
(default `qwen3.5:9b`) into the `ollama_data` volume; it only reports
healthy once the model is present, and `backend` waits on that, so no
manual `ollama pull` is needed (subsequent boots reuse the cached
model). Create an admin user when you want one:

```powershell
docker compose exec backend python manage.py createsuperuser
```

The UI is at `http://localhost` (port 80) -- the only port this stack
publishes. nginx proxies `/api/`, `/admin/` and `/static/` to the
backend, so the API and Django admin are reachable through the same
origin. `db`, `redis`, `ollama` and `backend` stay internal to the
compose network, so the stack needs no host ports of its own beyond
80 and coexists with native dev services (Postgres, Ollama, a dev
server) already bound on the host.

Compose overrides `DATABASE_URL`, `OLLAMA_BASE_URL` and `REDIS_URL`
with the in-network service hostnames, so `.env` can keep its
localhost values for native dev without conflict. Embedding and
reranker model downloads persist in the `hf_cache` volume across
restarts.

#### GPU access

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

## Usage

### Ingesting a corpus

Drop your PDFs/DOCX/HTML/TXT/MD files under `papers/` and run:

```powershell
python manage.py ingest_papers ../papers/
```

The command walks the tree, deduplicates by SHA-256 of the file
content, and persists chunks + embeddings. Re-running is safe; already
ingested files are reported as duplicates.

### API endpoints (require JWT)

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

## Evaluation and results

A small harness in `eval/dataset.jsonl` (25 questions across
`single_hop`, `multi_hop`, `detail_tech`, `synthesis` and `negative`
categories) drives the same code paths as the chat API. Run it after
ingestion:

```powershell
python manage.py eval_run
```

Each run writes `eval/results/<timestamp>/summary.md` (aggregate)
and `per_question.jsonl` (full answers and per-question metrics).

### Reproducing the full results

From `backend/`, with the corpus ingested. `HF_HUB_OFFLINE`,
`AGENT_TOP_K` and `AGENT_USE_RERANKER` come from `.env` (see
`.env.example`); no shell exports needed.

```powershell
# Retrieval + answer scoring, three modes. Local only -- free.
# Each prints "results: <DIR>" at the end; note the three dirs.
python manage.py eval_run --retrieval hybrid      # ~6-10 min (chat)
python manage.py eval_run --retrieval semantic    # ~5-8 min
python manage.py eval_run --retrieval none        # ~2-4 min (no retrieval)

# A/B tables (instant, free). Drop straight into this README.
python manage.py eval_compare <DIR_HYBRID> <DIR_SEMANTIC> --out ../eval/ab_hybrid_vs_semantic.md
python manage.py eval_compare <DIR_HYBRID> <DIR_NONE>     --out ../eval/ab_hybrid_vs_none.md

# Ragas metrics on the hybrid run. Uses the judge in RAGAS_JUDGE_PROVIDER.
# Local "ollama" judge is free but a poor structured-output judge;
# "anthropic"/"openai" need an API key and cost ~$0.5 (claude-haiku-4-5,
# --workers 3 stays under a 50 req/min org limit).
python manage.py ragas_run <DIR_HYBRID> --workers 3
```

Retrieval-only sweeps are much faster -- add `--no-chat` to skip
generation (scores `hit@k`/`recall` in seconds, no Ollama, no cost).
`eval_run` never calls a paid API; only `ragas_run` with a cloud
judge does.

### Metrics

| metric | what it measures |
|---|---|
| `retrieval hit@k` | the expected paper appears in the top-k retrieved |
| `retrieval recall` | fraction of expected papers actually retrieved |
| `answer keyword hit` | the answer contains all `must_include` tokens |
| `answer cites a doc` | the answer carries a `[doc:<name>]` citation |
| `negatives abstained correctly` | off-corpus questions are refused, not invented |

### Results

Run: `qwen3.5:9b` generation, `bge-small-en-v1.5` embeddings,
reranker off, 25 questions (22 non-negative + 3 negatives).
Retrieval/answer metrics are deterministic; Ragas is judged by
`claude-haiku-4-5`.

**Retrieval mode ablation** (canonical `top_k=12`, thinking
disabled; full A/B in `eval/ab_hybrid_vs_*.md`):

| metric | hybrid (RRF) | semantic only | no retrieval |
|---|---|---|---|
| retrieval hit@12 | 100% | 100% | -- |
| retrieval recall | 93.94% | 93.94% | -- |
| answer keyword hit | 95.45% | 95.45% | 36.36% |
| answer cites a doc | 100% | 100% | 18.18% |

`hybrid` vs `semantic only`: byte-identical -- every A/B delta is
exactly +0.0pp, and that exactness is the tell. The lexical channel
filters with pg_trgm `content % query` and ranks by `similarity()`
(trigrams shared over the trigrams of the union, default 0.3
threshold). With ~512-token child chunks and a short query, that
similarity sits structurally far below 0.3 for any query --
sentence or single keyword -- so `_lexical_search` returns ~0 rows,
RRF fuses ~12 dense hits with ~0 lexical, and hybrid degenerates to
pure dense on every query. So on this setup hybrid retrieval *is*
dense retrieval, by mechanism: `%`/`similarity` is the wrong tool
for short-query-vs-long-document, so the pg_trgm channel as wired
is effectively inert. The numbers are unaffected -- dense alone
hits 100% / 93.94% recall and the no-retrieval ablation below shows
retrieval is still load-bearing -- but the honest reading is that
the lexical half of "hybrid" is not contributing here; making it
real (pg_trgm `word_similarity` / `<%`, or a `tsvector` full-text
channel) would change retrieval and require re-measuring.

`hybrid` vs `no retrieval` is the load-bearing comparison: stripping
the context drops answer keyword hit from 95.45% to 36.36%
(-59.1pp) and citations from 100% to 18%. The 9B model knows these
famous papers, yet retrieval still contributes ~59pp of answer
accuracy -- evidence the pipeline works, not that the model
memorised the corpus.

**Tuning `top_k`.** Sweeping the candidate count against retrieval
recall:

| top_k | single_hop | multi_hop | synthesis | overall |
|---|---|---|---|---|
| 8 | 100% | 67% | 78% | 88% |
| 12 | 100% | 83% | 89% | 94% |
| 26 | 100% | 92% | 89% | 96% |
| 32 | 100% | 92% | 100% | 98% |

The knee is at 12 (`multi_hop` +16.7pp, overall +6pp); past it,
recall grows slowly while prompt noise and latency grow fast, so
`AGENT_TOP_K` defaults to 12. Canonical chat eval at the default
`top_k=12` (hybrid), run `20260518T193827Z`:

| metric | value |
|---|---|
| retrieval hit@12 (non-negative) | 100% |
| retrieval recall (non-negative) | 93.94% |
| answer keyword hit | 95.45% (21/22) |
| answer cites a doc | 100% |
| negatives abstained correctly | 2/3 |

`keyword_hit` was a brittle substring check. Two early misses were
metric artifacts, not wrong answers: `sh-07` answered "reward score"
vs the token `feedback`; `mh-02` wrote "quantization" vs the British
stem `quantis`. Tokens now accept `a|b` alternatives. The one
remaining miss (95.45%, 21/22) is `mh-02`, which has a real
retrieval gap -- recall 0.50, `lora.pdf` ranked past `top_k=12` so
only `qlora.pdf` is retrieved. Whether the answer still surfaces the
LoRA/`adapter` token varies run to run on that thin context; it is
recorded honestly as the `multi_hop` recall miss, not masked.

Generation runs with the model's chain-of-thought disabled
(`think:false`): this client consumes `message.content`, and a
qwen3-class model otherwise spends its token budget in a separate
`thinking` field (yielding empty answers and multi-minute runs).
The corrective-RAG graph is the reasoning structure, so nothing is
lost; chat latency drops ~5x (p50 ~15s) and every number here is
measured in this configuration. Citations are the readable source
filename, e.g. `[doc:attention.pdf]`.

Ragas (22 non-negative questions, canonical `top_k=12` run;
negatives are abstention tests, not answers, scored by abstention).
`ragas_run` computes only the three reference-free metrics -- the
dataset has no gold answers, so the reference-based
`context_precision`/`context_recall` would mis-attribute and are
not computed:

| metric | mean | reference-free? |
|---|---|---|
| faithfulness | 0.907 | yes |
| answer relevancy | 0.930 | yes |
| llm_context_precision_without_reference | 0.385 | yes |

`faithfulness` and `answer_relevancy` need no reference: generation
is well grounded in the retrieved context (0.907) and on-topic
(0.930).

`llm_context_precision_without_reference` is 0.385, and that low
number is the correct number for this operating point, for two
compounding reasons -- neither a retrieval defect, both measured:

1. It is mechanically modest at the recall-tuned `top_k=12`. The
   metric is Average-Precision over the 12 retrieved chunks. `top_k`
   sits at the recall knee (see the sweep above): with only ~1-3
   truly-supporting chunks among 12 and a retriever tuned to put the
   right chunk somewhere in the top-12 rather than at rank 1, AP@12
   is bounded low by construction. Raising it means forcing the best
   chunk to rank 1 -- exactly a cross-encoder reranker's job -- and
   the reranker table below shows two models measured net-negative
   here. `faithfulness` 0.907 confirms the model uses the supporting
   chunks and ignores the rest.
2. Per-chunk precision penalises abstractive answers. Three
   questions score exactly 0.0 -- `mh-04`, `syn-02`, `syn-03` --
   all multi-hop/synthesis answers that abstract across several
   papers, so the per-chunk judge cannot map a synthesised narrative
   back to any single raw chunk and returns all-zero, even though
   their deterministic recall and keyword hit are fine. Excluding
   the three, the precision mean rises from 0.385 to 0.446.

The trustworthy retrieval evidence is the deterministic `hit@k` /
`recall` figures plus the no-retrieval ablation, not this per-chunk
precision number.

The remaining weak spot is `multi_hop` retrieval recall: 83% at the
default `top_k=12` (up from 67% at 8). A cross-encoder reranker makes
it **worse**, and this was checked with two models, not assumed:

| multi_hop recall (top_k=12) | overall |
|---|---|
| hybrid only: **83%** | **94%** |
| + `ms-marco-MiniLM-L-6-v2`: 67% | 89% |
| + `bge-reranker-base`: 75% | 92% |

Rescoring the 36-candidate pool, both rerankers demote `react.pdf`
(rank 9) -- already inside plain hybrid's top-12 -- out of the final
12, and neither rescues `lora.pdf` (rank 26, in the pool) for mh-02.
The stronger `bge` reranker beats the tiny MiniLM but still loses to
no reranker: the dense `top_k=12` ranking is already strong for
this domain, so any re-sort of a candidate pool mostly risks
dropping documents it had right. The reranker stays off by default.

Query decomposition (split a multi-hop question into sub-queries,
retrieve each, merge round-robin into the same `top_k` budget) was
implemented and measured too: also net-negative -- multi_hop recall
83 -> 75%. It does fix the case it targets (`mh-02`: a "what is
LoRA?" sub-query lifts `lora.pdf` from rank 26, recall 0.50 -> 1.00)
but breaks two questions the single query already answered (`mh-01`,
`mh-05`: 1.00 -> 0.50) -- splitting a fixed 12-chunk budget across
sub-queries halves per-topic depth, dropping chunks hybrid had
captured. Kept opt-in (`AGENT_QUERY_DECOMPOSITION`).

So every standard "advanced RAG" lever -- reranking (two models),
query decomposition, and the per-chunk precision metric itself --
was measured, not assumed, and none changes the verdict: well-tuned
dense retrieval at `top_k=12` -- what hybrid reduces to here, the
lexical channel being inert (above) -- is the measured optimum on
this corpus.
The low per-chunk precision reflects that deliberate recall-tuned
`k=12` operating point and a known weakness of per-chunk precision
on abstractive answers, not a retrieval defect. The residual
`multi_hop` gap is a known limitation (e.g. `mh-06`'s
`attention.pdf` at rank 68 is past any sane candidate pool).
Negatives are scored by abstention, not Ragas: 2/3 here -- one
off-corpus question ("SAM 3") was answered instead of refused, a
known limitation.

### Healthy ranges

For this corpus (13 deep learning papers) and `qwen3.5:9b`:

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

2. **Citations**. Every grounded answer should carry a `[doc:<name>]`
   tag (e.g. `[doc:attention.pdf]`). The `answer cites a doc` metric
   tracks this. An answer without a citation is either off-corpus or
   the model bypassed the context.

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
  irrelevant chunks. Rebalance `KB_SEMANTIC_WEIGHT` /
  `KB_LEXICAL_WEIGHT` (the reranker was measured to *reduce* recall
  here -- see Results).

### Iterating

Change one knob at a time, re-run the eval, diff the summaries:

- weak `multi_hop` -> raise `AGENT_TOP_K`. The reranker and query
  decomposition were both measured net-negative here (see Results);
  the residual gap is a known limitation.
- weak `detail_tech` -> raise `OLLAMA_NUM_CTX`, or lower
  `KB_CHILD_CHUNK_SIZE` (requires re-ingest).
- weak `synthesis` -> tune prompts in
  `backend/agent/orchestrator/prompts.py`.
- weak `negative` -> tighten the verifier prompt or raise
  `AGENT_MAX_VERIFY_RETRIES`.
- weak `single_hop` (rare once retrieval works at all) -> revisit
  `KB_SEMANTIC_WEIGHT` / `KB_LEXICAL_WEIGHT`.

## Reference

### Tunables

All knobs live in `.env` -- see `.env.example` for the full list with
defaults. The most impactful ones:

- `LLM_PROVIDER` -- `ollama` (native `/api/chat`, honours `num_ctx`)
  or `openai` (any OpenAI-compatible endpoint).
- `OLLAMA_MODEL` -- pick a bigger or smaller LLM.
- `OLLAMA_NUM_CTX` -- context window forwarded to Ollama; raise it
  when retrieved chunks risk truncation.
- `AGENT_TOP_K` -- how many KB chunks feed the synthesis prompt
  (defaults to 12, chosen from a recall sweep -- see Results).
- `AGENT_USE_RERANKER` -- enable the cross-encoder reranking pass.
  Off by default: measured to *reduce* multi_hop recall on this
  corpus (the MS-MARCO reranker mis-ranks academic prose -- see
  Results), kept for corpora where ranking order matters.
- `AGENT_QUERY_DECOMPOSITION` -- split multi-hop questions into
  sub-queries. Off by default: also measured net-negative here
  (see Results), kept opt-in.
- `KB_SEMANTIC_WEIGHT` / `KB_LEXICAL_WEIGHT` -- bias of the hybrid
  fusion (must sum to roughly 1.0). Note: on prose corpora the
  pg_trgm lexical channel returns ~0 (see Results), so this split
  has no measurable effect until that channel is reworked.
- `AGENT_MAX_VERIFY_RETRIES` -- set to `0` to skip the verifier loop.
- `RAGAS_JUDGE_PROVIDER` -- judge LLM for `ragas_run` (`ollama` or
  `openai`).

Prompts live in `backend/agent/orchestrator/prompts.py`.

### Observability

Tracing is off unless `LANGSMITH_API_KEY` is set. With no key the
`@traceable` decorators are a transparent pass-through (zero
overhead). To enable it, set in `.env`:

```env
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=rag-docs-chatbot
```

An EU-workspace key also needs
`LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`; its traces
then live at `eu.smith.langchain.com`, not the default US dashboard.

Each chat request then produces one trace under the project showing:

- the LangGraph pipeline node by node (`intake`, `classify`, then
  either `conversational` or `retrieve` -> `synthesise` -> `verify`,
  including the verify -> synthesise retry loop);
- the `retrieve` span with the query and the retrieved chunks;
- the `synthesise` and `verify` spans, each wrapping the
  `chat_completion` LLM call with the exact prompt sent to the model
  and the raw response.

The clean RAG path -- a single pass, `verify` accepts the first
draft (`verify_iterations: 1`):

![LangSmith trace of the corrective-RAG graph for one chat request](docs/langsmith-trace.png)

The "corrective" in corrective-RAG, captured live on a synthesis
question: `verify` rejects the first draft, the graph loops back to
`synthesise`, and the revised answer is accepted
(`verify_iterations: 2`):

![LangSmith trace where verify rejects the first answer and the graph loops back to synthesise](docs/langsmith-retry.png)

Both screenshots are captured by hand from the LangSmith dashboard
and saved under `docs/`.

### Common commands

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

### Conventions

- **Commits**: Conventional Commits (`feat(scope): ...`, `chore: ...`,
  imperative mood, <=72 chars on the subject line).
- **Never commit** `.env`, `db.sqlite3`, `.venv/`, or `papers/*.pdf`.

### License

MIT. See [`LICENSE`](./LICENSE).
