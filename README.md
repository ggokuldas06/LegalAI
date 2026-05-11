# Legal AI Assistant

A production-grade legal document analysis system combining a hybrid retrieval-augmented generation (RAG) pipeline with a locally-hosted large language model. Built for document summarisation, contract clause extraction, and IRAC-structured legal research over user-uploaded documents.

---

## Overview

The system provides three distinct analysis modes:

- **Summariser** — extracts executive summaries, key obligations, risks, and deadlines from any legal document
- **Clause Classifier** — identifies and classifies contract clauses by type (Termination, Indemnity, Confidentiality, IP, Liability Caps, Governing Law, etc.) with confidence scoring
- **Case Law IRAC** — a full RAG pipeline that retrieves semantically relevant document chunks and answers legal questions in structured Issue / Rule / Application / Conclusion format, or as a direct answer for factual lookups

All inference runs locally. No data leaves the machine.

---

## Architecture

```
                          ┌─────────────────────────────┐
                          │        Vue 3 Frontend        │
                          │  Pinia  |  Vite  |  Bootstrap │
                          └──────────────┬──────────────┘
                                         │ HTTP / SSE
                          ┌──────────────▼──────────────┐
                          │     Django REST Framework    │
                          │  JWT Auth  |  Rate Limiting  │
                          └──────┬──────────────┬────────┘
                                 │              │
              ┌──────────────────▼──┐    ┌──────▼──────────────────┐
              │   Inference Layer   │    │      RAG Pipeline        │
              │                     │    │                          │
              │  Ollama /api/chat   │    │  1. Hierarchical Chunker │
              │  gemma4:latest      │    │  2. Embedding Service    │
              │  Simulated SSE      │    │  3. ChromaDB + BM25      │
              │  streaming          │    │  4. RRF Fusion           │
              └─────────────────────┘    └──────────────────────────┘
                                                    │
                          ┌─────────────────────────▼──────────────┐
                          │              Data Layer                  │
                          │  SQLite (metadata)  |  ChromaDB (vectors)│
                          │  File system (raw documents)             │
                          └────────────────────────────────────────┘
```

---

## Advanced Techniques

### 1. Structure-Aware Hierarchical Recursive Chunking

Documents are not split naively by character count. The chunker (`api/rag/chunker.py`) first parses the document's logical structure into a tree before any splitting occurs.

**Parsing pipeline:**

1. Tables are extracted atomically before structural parsing. Each table becomes a single indivisible chunk, preserving row and column relationships.
2. The remaining text is parsed into a heading hierarchy using two sets of patterns in parallel:
   - Markdown headings (`#`, `##`, `###`)
   - Legal document patterns: `PART / CHAPTER / TITLE` (H1), `SECTION / ARTICLE / §` or numbered headings like `1. DEFINITIONS` (H2), sub-clause patterns like `1.1`, `a)`, `(i)` (H3)
3. The parsed tree is flattened recursively. A node is emitted as a single chunk if it fits within `chunk_size=800` characters. If a section is too large, the algorithm recurses to H3, then to sentence-level splitting.
4. Sentence splitting uses NLTK punkt tokenizer with `chunk_overlap=150` characters of context carried between adjacent chunks to prevent retrieval gaps at chunk boundaries.

Each chunk carries rich metadata: `heading`, `section_path` (breadcrumb trail like `Part I > Section 5 > 5.1`), `node_type` (`text` or `table`), `document_id`, `title`, `jurisdiction`, and `year`.

**Why this matters:** Naive character-based chunking splits legal clauses mid-sentence and severs the heading from its body. Structure-aware chunking ensures that retrieved chunks are semantically complete and self-contained.

---

### 2. Hybrid BM25 + Vector Search with Reciprocal Rank Fusion

Mode C retrieval uses two independent ranking signals fused together.

**Vector search** — each chunk is embedded at ingestion time using `all-MiniLM-L6-v2` (384-dimensional dense vectors) and stored in ChromaDB with HNSW cosine similarity indexing. At query time, the question is embedded and the top candidates are retrieved by cosine similarity.

**BM25 search** — a `BM25Okapi` index (from `rank_bm25`) is maintained in memory, built from all chunk texts on server startup and updated incrementally on ingestion. BM25 scores documents by term frequency weighted against inverse document frequency across the corpus. It excels at exact keyword matches that vector search can miss.

**Reciprocal Rank Fusion (RRF)** — neither score is normalized or weighted against the other. Instead, only the rank positions are used:

```
RRF_score(chunk) = sum over each ranked list: 1 / (k + rank + 1)
```

where `k = 60` is a smoothing constant. The two ranked lists (BM25 order and vector order) are merged by this formula. Chunks appearing in the top positions of both lists receive the highest combined scores. The top 8 fused results are passed to the LLM as context.

**Why RRF over score normalization:** BM25 scores are unbounded positive reals; cosine similarity scores are in [0, 1]. Normalizing and linearly combining them requires calibration. RRF requires no calibration — rank position is a stable, scale-invariant signal.

---

### 3. ChromaDB as the Vector Store

Vectors are persisted in a `chromadb.PersistentClient` at `data/chroma_db/`. The collection uses cosine distance and HNSW indexing for approximate nearest-neighbour search.

All chunk metadata is stored alongside vectors in ChromaDB. This enables server-side metadata filtering before retrieval — for example, scoping a query to a specific `document_id`, `jurisdiction`, or year range. Filters are translated to Chroma's `$and` / `$eq` / `$gte` / `$lte` where-clause format before the vector query is executed, so only matching chunks participate in both the vector search and the BM25 candidate list.

On document deletion, all corresponding Chroma documents are deleted by `document_id` filter and the BM25 index is fully rebuilt from the remaining corpus.

---

### 4. LLM — Gemma 4 via Ollama

The generation model is `gemma4:latest` served locally by Ollama. The backend communicates with Ollama's REST API (`/api/chat`) over HTTP using `httpx`.

**Known behaviour — thinking token budget:** Gemma 4 uses internal chain-of-thought tokens that count against the `num_predict` parameter. On long legal prompts, a small `num_predict` value causes the model to exhaust its token budget on internal reasoning and return empty visible content. The engine enforces a minimum of `num_predict = max(requested_tokens, 2048)` on every request.

**Known behaviour — streaming with system messages:** Gemma 4 in Ollama 0.23.x does not emit content tokens when streaming is enabled and a system message is present in the messages list. The workaround is simulated streaming: the full response is fetched from the non-streaming `/api/chat` endpoint, then delivered to the frontend word-by-word via `re.split(r'(\s+)', text)`. The frontend receives an identical Server-Sent Events stream and renders a typewriter effect with no visible difference.

---

### 5. Embedding Model

| Property | Value |
|---|---|
| Model | `all-MiniLM-L6-v2` |
| Framework | `sentence-transformers` |
| Embedding dimension | 384 |
| Max input tokens | 256 |
| Similarity metric | Cosine |
| Inference device | CPU (MPS-compatible on Apple Silicon) |

The model is loaded as a singleton on first access and held in memory for the lifetime of the Django process. It is used only at ingestion time (to embed chunks) and at query time for Mode C (to embed the incoming question). Modes A and B do not use the embedding model.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, Vite 4, Pinia, Vue Router, Bootstrap 5, Bootstrap Icons |
| Backend | Django 4.2, Django REST Framework 3.14 |
| Authentication | djangorestframework-simplejwt (1h access / 7d refresh tokens) |
| Rate limiting | django-ratelimit (60 requests/hour per user) |
| Vector store | ChromaDB >= 0.5.0 (PersistentClient, HNSW cosine) |
| Sparse retrieval | rank-bm25 >= 0.2.2 (BM25Okapi) |
| Embeddings | sentence-transformers >= 2.2.2 (`all-MiniLM-L6-v2`, 384-dim) |
| LLM runtime | Ollama (`gemma4:latest`) |
| LLM HTTP client | httpx >= 0.27.0 |
| Document parsing | PyPDF2 3.0.1 (PDF), plain text (TXT, MD) |
| Sentence tokenization | NLTK 3.8+ (punkt) |
| Streaming | Django StreamingHttpResponse + Server-Sent Events |
| Database | SQLite (document metadata, chat logs, audit trail) |

---

## Project Structure

```
legal-ai-assistant/
├── backend/
│   ├── api/
│   │   ├── inference/
│   │   │   ├── llm_engine.py       # Ollama HTTP client, simulated streaming
│   │   │   ├── prompts.py          # System + user message builders per mode
│   │   │   ├── service.py          # Orchestrates prompts, LLM, post-processing
│   │   │   └── post_processor.py   # Citation extraction, IRAC parsing
│   │   ├── rag/
│   │   │   ├── chunker.py          # Hierarchical recursive chunker
│   │   │   ├── embeddings.py       # all-MiniLM-L6-v2 singleton
│   │   │   ├── chroma_store.py     # ChromaDB + BM25 hybrid store + RRF
│   │   │   ├── retrieval.py        # Query embedding + hybrid search
│   │   │   └── ingestion.py        # Chunk + embed + index pipeline
│   │   ├── views/
│   │   │   ├── chat_views.py       # /chat endpoint, SSE streaming
│   │   │   ├── document_views.py   # Upload, list, delete
│   │   │   └── rag_views.py        # /ingest, /search, /rag/stats
│   │   └── models.py               # Document, Chunk, ChatLog, AuditLog
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── ChatView.vue
│       │   └── DocumentsView.vue
│       ├── components/
│       │   ├── chat/               # ModeSelector, DocumentSelector, ChatMessage
│       │   └── document/           # UploadModal, DocumentCard
│       ├── stores/                 # Pinia: auth, chat, documents, history
│       └── services/api.js         # Axios + SSE fetch client
└── data/
    ├── db.sqlite3
    └── chroma_db/                  # Persisted ChromaDB collection
```

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- [Ollama](https://ollama.com) installed and running
- Redis (required by Celery; can be skipped if not using async tasks)

---

## Running the Project

### 1. Pull the model into Ollama

```bash
ollama pull gemma4:latest
```

Verify it is available:

```bash
ollama list
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK tokenizer data
python3 -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Copy and configure environment variables
cp .env.example .env              # edit OLLAMA_URL, MODEL_NAME, SECRET_KEY as needed

# Run database migrations
python manage.py migrate

# Create a superuser (optional)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

### 3. Frontend setup

```bash
cd frontend

npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

### 4. Start Ollama (if not already running as a service)

```bash
ollama serve
```

---

## Environment Variables

All backend configuration lives in `backend/.env`:

```
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173

DATABASE_PATH=../data/db.sqlite3
REDIS_URL=redis://localhost:6379/0

OLLAMA_URL=http://localhost:11434
MODEL_NAME=gemma4:latest

TEMPERATURE=0.7
TOP_P=0.9
TOP_K=50
MAX_TOKENS=2048
```

---

## Using the Application

### Uploading and indexing a document

1. Navigate to the Documents page and upload a PDF, TXT, or MD file.
2. After upload, return to the Chat page and select the document in the sidebar.
3. If the document has not been indexed (chunk count shows "not indexed"), click the **Index this document** button that appears inline. This runs the full ingestion pipeline: hierarchical chunking, embedding, and ChromaDB indexing.

### Mode A — Summariser

Select a document and click **Summarise Document**. No text input is required. The full document text is passed directly to the LLM. Output is structured Markdown with Executive Summary, Key Points, Risks, and Obligations sections.

### Mode B — Clause Classifier

Select a document and click **Extract and Classify Clauses**. The model identifies clauses by type, assigns a confidence level, and includes a verbatim excerpt with the nearest section citation.

### Mode C — Case Law IRAC

Type a legal question in the input box. Optionally select a document in the sidebar to scope retrieval to that document only; if no document is selected, the search runs across all indexed documents.

- Factual questions (who, what, how much, which section) receive a direct 1–3 sentence answer with a source citation.
- Analytical questions (whether X is permitted, what are the obligations if Y, analyse clause Z) receive a full IRAC-structured response.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Obtain JWT tokens |
| POST | `/api/v1/auth/token/refresh` | Refresh access token |
| GET | `/api/v1/documents` | List uploaded documents |
| POST | `/api/v1/documents/upload` | Upload a document (PDF / TXT / MD) |
| DELETE | `/api/v1/documents/{id}/delete` | Delete a document and its chunks |
| POST | `/api/v1/ingest` | Chunk, embed, and index a document |
| POST | `/api/v1/chat` | Send a chat message (streaming or non-streaming) |
| GET | `/api/v1/history` | List past chat sessions |
| POST | `/api/v1/search` | Direct vector + BM25 search (debug) |
| GET | `/api/v1/rag/stats` | Vector store statistics |
| GET | `/api/v1/health/check` | Model and service health |

All endpoints except `/auth/register`, `/auth/login`, and `/auth/token/refresh` require a `Bearer` JWT token in the `Authorization` header.

Streaming chat (`stream: true`) uses Server-Sent Events. The response is a `text/event-stream` where each event is a JSON object of the form:

```
data: {"type": "start", "mode": "C", "tokens_in": 312}
data: {"type": "token", "token": "The "}
data: {"type": "token", "token": "parties "}
...
data: {"type": "done", "disclaimer": "...", "chat_log_id": 42}
```

---

## Supported File Types

| Format | Ingestion method | Notes |
|---|---|---|
| PDF | PyPDF2 text extraction | Scanned PDFs without OCR layer will produce poor results |
| TXT | Plain text read (UTF-8) | |
| MD | Plain text read (UTF-8) | Markdown headings parsed natively by the hierarchical chunker |
