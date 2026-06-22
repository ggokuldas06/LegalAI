# Legal AI Assistant

A production-grade legal document analysis system combining a multimodal agentic retrieval-augmented generation (RAG) pipeline with locally-hosted large language models. Built for document summarisation, contract clause extraction, IRAC-structured legal research, and cross-document agentic Q&A over user-uploaded PDFs, scanned documents, and images.

---

## Overview

The system provides four distinct analysis modes:

- **Mode A — Summariser** — extracts executive summaries, key obligations, risks, and deadlines from any legal document
- **Mode B — Clause Classifier** — identifies and classifies contract clauses by type (Termination, Indemnity, Confidentiality, IP, Liability Caps, Governing Law, etc.) with confidence scoring
- **Mode C — Case Law IRAC** — a full RAG pipeline that retrieves semantically relevant document chunks and answers legal questions in structured Issue / Rule / Application / Conclusion format, or as a direct answer for factual lookups
- **Mode D — Case Agentic Q&A** — an agentic RAG mode that operates over a user-defined **Case** (a named collection of multiple documents and images). A two-stage document routing agent selects which documents to search before retrieval, and the frontend renders an expandable agent trace showing its reasoning

All inference runs locally via Ollama. No data leaves the machine.

---

## Architecture

```
                          ┌───────────────────────────────┐
                          │        Vue 3 Frontend         │
                          │  Pinia  |  Vite  |  Bootstrap │
                          │  Cases  |  AgentTrace panel   │
                          └──────────────┬────────────────┘
                                         │ HTTP / SSE
                          ┌──────────────▼───────────────┐
                          │     Django REST Framework    │
                          │  JWT Auth  |  Rate Limiting  │
                          └──────┬──────────────┬────────┘
                                 │              │
              ┌──────────────────▼──┐    ┌──────▼────────────────────────────────┐
              │   Inference Layer   │    │         RAG Pipeline (v2)             │
              │                     │    │                                       │
              │  Ollama /api/chat   │    │  1. VisionExtractor (qwen2.5vl:7b)   │
              │  gemma4:latest      │    │     - Image file ingestion            │
              │  qwen2.5vl:7b       │    │     - Scanned PDF OCR fallback        │
              │  Simulated SSE      │    │  2. Hierarchical Chunker              │
              │  streaming          │    │  3. Embedding Service (MiniLM-L6-v2)  │
              └─────────────────────┘    │  4. ChromaDB + BM25 + RRF Fusion     │
                                         │  5. DocDescriber (LLM routing desc.) │
                                         │  6. DocRouter Agent (2-stage)        │
                                         │  7. CaseRetrievalService             │
                                         └───────────────────────────────────────┘
                                                    │
                          ┌─────────────────────────▼──────────────────────────┐
                          │                    Data Layer                      │
                          │  SQLite (metadata, cases, chat logs, audit trail)  │
                          │  ChromaDB (vectors + BM25 index)                   │
                          │  File system (PDFs, images, text files)            │
                          └────────────────────────────────────────────────────┘
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

Each chunk carries rich metadata: `heading`, `section_path` (breadcrumb trail like `Part I > Section 5 > 5.1`), `node_type` (`text` or `table`), `document_id`, `title`, `jurisdiction`, `year`, and `file_type`.

**Why this matters:** Naive character-based chunking splits legal clauses mid-sentence and severs the heading from its body. Structure-aware chunking ensures that retrieved chunks are semantically complete and self-contained.

---

### 2. Multimodal Document Ingestion (Vision Extraction)

The ingestion pipeline now handles three file types — PDFs, plain text/Markdown, and image files — using a local vision model (`qwen2.5vl:7b` via Ollama) for content that cannot be extracted by text parsers.

**Image files (PNG, JPG, JPEG, TIFF, BMP, WEBP, GIF):**
`VisionExtractor.extract_from_image()` base64-encodes the image and sends it to `qwen2.5vl:7b` with a structured prompt that handles typed text, handwritten text, tables, charts, and signatures. The extracted plain-text description is then fed into the standard hierarchical chunking pipeline.

**Scanned / sparse PDF pages:**
`VisionExtractor.extract_from_pdf_page()` uses `pymupdf` (`fitz`) to render each PDF page at 150 DPI to a PNG in memory. Pages where `pymupdf` text extraction returns fewer than 50 characters trigger this OCR fallback. The rendered pixmap is base64-encoded and sent to `qwen2.5vl:7b`. This lets the system process scanned court documents and signed contracts without any external OCR service.

| Input type | Extraction path |
|---|---|
| PDF (digital / native text) | `pymupdf` direct text extraction, per page |
| PDF (scanned / image-only page) | `pymupdf` renders page → `qwen2.5vl:7b` OCR |
| Image file (PNG, JPG, …) | Direct base64 → `qwen2.5vl:7b` |
| TXT / MD | UTF-8 file read |

---

### 3. Hybrid BM25 + Vector Search with Reciprocal Rank Fusion

Mode C and Mode D retrieval use two independent ranking signals fused together.

**Vector search** — each chunk is embedded at ingestion time using `all-MiniLM-L6-v2` (384-dimensional dense vectors) and stored in ChromaDB with HNSW cosine similarity indexing. At query time, the question is embedded and the top candidates are retrieved by cosine similarity.

**BM25 search** — a `BM25Okapi` index (from `rank_bm25`) is maintained in memory, built from all chunk texts on server startup and updated incrementally on ingestion. BM25 scores documents by term frequency weighted against inverse document frequency across the corpus. It excels at exact keyword matches that vector search can miss.

**Reciprocal Rank Fusion (RRF)** — neither score is normalized or weighted against the other. Instead, only the rank positions are used:

```
RRF_score(chunk) = sum over each ranked list: 1 / (k + rank + 1)
```

where `k = 60` is a smoothing constant. The two ranked lists (BM25 order and vector order) are merged by this formula. Chunks appearing in the top positions of both lists receive the highest combined scores. The top 8 fused results are passed to the LLM as context.

**Why RRF over score normalization:** BM25 scores are unbounded positive reals; cosine similarity scores are in [0, 1]. Normalizing and linearly combining them requires calibration. RRF requires no calibration — rank position is a stable, scale-invariant signal.

---

### 4. Cases — Multi-Document Workspace

A **Case** is a named, user-owned collection of documents and images that belong to the same legal matter. Cases enable the agentic RAG mode (Mode D) to search across multiple documents in a single query.

**Data model:**
- `Case` — title, description, owner (`user`), timestamps
- `CaseDocument` — junction table linking `Case` ↔ `Document` with an optional `role` annotation (`primary`, `evidence`, `reference`, `contract`, `exhibit`, `other`)

Documents can be added to multiple cases and retain their independent indexing. Deleting a case does not delete its documents.

**Frontend:** The Cases page (`/cases`) lists all user cases as cards. Clicking a case opens the Case Detail view (`/cases/:id`) which shows all documents in the case, allows adding/removing documents, and provides a chat interface pre-scoped to Mode D.

---

### 5. LLM-Generated Document Descriptions (DocDescriber)

At the end of each ingestion run, `DocDescriber` calls `gemma4:latest` to generate a structured JSON description of the document and stores it in `Document.doc_description`. This description is used exclusively by the document routing agent at query time.

**Output schema:**

```json
{
  "summary": "2–3 sentence overview of the document",
  "topics": ["topic1", "topic2"],
  "parties": ["party name or role"],
  "jurisdiction": "detected jurisdiction or empty",
  "key_sections": ["section name"],
  "document_type_detail": "e.g. employment contract, merger agreement, court ruling"
}
```

If the LLM call fails or returns invalid JSON, a minimal fallback is written so that routing still functions. Description generation runs after the indexing transaction completes and does not block the ingestion response.

---

### 6. Two-Stage Agentic Document Router (DocRouter)

When a Mode D query arrives, `DocRouter` selects which documents within the case are relevant before retrieval begins. This avoids injecting irrelevant context and improves answer precision when a case contains many documents.

**Stage 1 — Semantic pre-filter:**
For each document in the case, the system embeds a rich text representation of its `doc_description` (summary + topics + document_type_detail + title) and computes cosine similarity against the query embedding. The top 6 highest-scoring documents are passed to Stage 2.

**Stage 2 — LLM routing judge:**
`gemma4:latest` is given the query and a formatted list of the pre-filtered document descriptions. It returns a JSON object:

```json
{
  "selected_indices": [1, 3],
  "reasoning": "Document 1 contains the indemnity clauses; Document 3 is the relevant court ruling",
  "confidence": "high"
}
```

The LLM enforces a maximum of 4 selected documents. If the LLM call fails for any reason, the system falls back gracefully to the semantic pre-filter results.

**Why two stages:** Sending all document descriptions directly to the LLM becomes expensive as case size grows. The semantic pre-filter caps the LLM context at 6 candidates regardless of how many documents are in the case.

---

### 7. Cross-Document Agentic Retrieval (CaseRetrievalService)

`CaseRetrievalService` orchestrates the full Mode D retrieval pipeline and returns both ranked passages and an `agent_trace` that the frontend renders.

**Pipeline:**

1. Embed the incoming query with `all-MiniLM-L6-v2`
2. `DocRouter.route()` selects relevant documents (two-stage, see above)
3. For each selected document, run the hybrid BM25 + vector search scoped to that document's `document_id` in ChromaDB
4. Apply cross-document RRF fusion across all per-document ranked lists
5. Return the top 8 passages (with metadata) plus the `agent_trace`

**Agent trace payload:**

```json
{
  "total_docs": 5,
  "selected_docs": [
    {"id": 3, "title": "Employment Agreement", "file_type": "pdf", "reasoning": "..."},
    {"id": 7, "title": "Signed Addendum", "file_type": "image", "reasoning": "..."}
  ],
  "routing_reasoning": "Documents 3 and 7 contain the relevant termination clauses"
}
```

The agent trace is forwarded through the SSE stream inside the `start` event and rendered by the `AgentTrace.vue` component as a collapsible panel below the assistant's reply.

---

### 8. ChromaDB as the Vector Store

Vectors are persisted in a `chromadb.PersistentClient` at `data/chroma_db/`. The collection uses cosine distance and HNSW indexing for approximate nearest-neighbour search.

All chunk metadata is stored alongside vectors in ChromaDB. This enables server-side metadata filtering before retrieval — for example, scoping a query to a specific `document_id`, `jurisdiction`, or year range. Filters are translated to Chroma's `$and` / `$eq` / `$gte` / `$lte` where-clause format before the vector query is executed, so only matching chunks participate in both the vector search and the BM25 candidate list.

On document deletion, all corresponding Chroma documents are deleted by `document_id` filter and the BM25 index is fully rebuilt from the remaining corpus.

---

### 9. LLM Models

| Model | Role | Runtime |
|---|---|---|
| `gemma4:latest` | Chat inference (Modes A/B/C/D), DocDescriber, DocRouter | Ollama |
| `qwen2.5vl:7b` | Vision extraction (image files, scanned PDF pages) | Ollama |

**Known behaviour — thinking token budget (gemma4):** Gemma 4 uses internal chain-of-thought tokens that count against the `num_predict` parameter. On long legal prompts, a small `num_predict` value causes the model to exhaust its token budget on internal reasoning and return empty visible content. The engine enforces a minimum of `num_predict = max(requested_tokens, 2048)` on every request.

**Known behaviour — streaming with system messages (gemma4):** Gemma 4 in Ollama 0.23.x does not emit content tokens when streaming is enabled and a system message is present in the messages list. The workaround is simulated streaming: the full response is fetched from the non-streaming `/api/chat` endpoint, then delivered to the frontend word-by-word via `re.split(r'(\s+)', text)`. The frontend receives an identical Server-Sent Events stream and renders a typewriter effect with no visible difference.

---

### 10. Embedding Model

| Property | Value |
|---|---|
| Model | `all-MiniLM-L6-v2` |
| Framework | `sentence-transformers` |
| Embedding dimension | 384 |
| Max input tokens | 256 |
| Similarity metric | Cosine |
| Inference device | CPU (MPS-compatible on Apple Silicon) |

The model is loaded as a singleton on first access and held in memory for the lifetime of the Django process. It is used at ingestion time (to embed chunks), at query time for Modes C and D (to embed the incoming question), and by `DocRouter` Stage 1 (to embed document description text).

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
| LLM runtime | Ollama (`gemma4:latest`, `qwen2.5vl:7b`) |
| LLM HTTP client | httpx >= 0.27.0 |
| PDF parsing | pymupdf >= 1.24.0 (text extraction + page rendering for OCR) |
| Image handling | Pillow >= 10.0.0 |
| Sentence tokenization | NLTK 3.8+ (punkt) |
| Streaming | Django StreamingHttpResponse + Server-Sent Events |
| Database | SQLite (document metadata, cases, chat logs, audit trail) |

---

## Project Structure

```
legal-ai-assistant/
├── backend/
│   ├── api/
│   │   ├── inference/
│   │   │   ├── llm_engine.py         # Ollama HTTP client, simulated streaming
│   │   │   ├── prompts.py            # System + user message builders per mode (A/B/C/D)
│   │   │   ├── service.py            # Orchestrates prompts, LLM, post-processing
│   │   │   └── post_processor.py     # Citation extraction, IRAC parsing
│   │   ├── rag/
│   │   │   ├── chunker.py            # Hierarchical recursive chunker
│   │   │   ├── embeddings.py         # all-MiniLM-L6-v2 singleton
│   │   │   ├── chroma_store.py       # ChromaDB + BM25 hybrid store + RRF
│   │   │   ├── retrieval.py          # Query embedding + hybrid search (Mode C)
│   │   │   ├── ingestion.py          # Chunk + embed + index pipeline (PDF/image/text)
│   │   │   ├── vision_extractor.py   # qwen2.5vl:7b vision OCR for images & scanned PDFs
│   │   │   ├── doc_describer.py      # LLM-generated JSON routing descriptions
│   │   │   ├── doc_router.py         # Two-stage agentic document router
│   │   │   └── case_retrieval.py     # Cross-document agentic retrieval for Mode D
│   │   ├── views/
│   │   │   ├── chat_views.py         # /chat endpoint, SSE streaming (Modes A–D)
│   │   │   ├── document_views.py     # Upload, list, delete, describe
│   │   │   ├── case_views.py         # CRUD for Cases + document membership
│   │   │   └── rag_views.py          # /ingest, /search, /rag/stats
│   │   └── models.py                 # Document, Case, CaseDocument, Chunk, ChatLog, AuditLog
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── ChatView.vue           # Chat interface (Modes A/B/C)
│       │   ├── CasesView.vue          # Case list + create
│       │   ├── CaseDetailView.vue     # Case detail, document management, Mode D chat
│       │   └── DocumentsView.vue
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ModeSelector.vue   # Mode A/B/C/D selector
│       │   │   ├── CaseSelector.vue   # Case picker for Mode D
│       │   │   ├── AgentTrace.vue     # Collapsible agent routing trace panel
│       │   │   ├── ChatMessage.vue    # Message renderer with citations
│       │   │   └── DocumentSelector.vue
│       │   └── document/              # UploadModal, DocumentCard
│       ├── stores/
│       │   ├── chat.js                # Pinia: chat state, streaming
│       │   ├── cases.js               # Pinia: cases CRUD
│       │   └── documents.js
│       └── services/api.js            # Axios + SSE fetch client
└── data/
    ├── db.sqlite3
    └── chroma_db/                     # Persisted ChromaDB collection
```

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- [Ollama](https://ollama.com) installed and running

---

## Running the Project

### 1. Pull the models into Ollama

```bash
# Text generation and routing agent
ollama pull gemma4:latest

# Vision model for image extraction and scanned PDF OCR
ollama pull qwen2.5vl:7b
```

Verify both are available:

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

# Run database migrations (includes v2 Cases + multimodal migration)
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
VISION_MODEL=qwen2.5vl:7b

TEMPERATURE=0.7
TOP_P=0.9
TOP_K=50
MAX_TOKENS=2048
```

---

## Using the Application

### Uploading and indexing a document

1. Navigate to the Documents page and upload a PDF, image (PNG/JPG/etc.), TXT, or MD file.
2. After upload, return to the Chat page and select the document in the sidebar.
3. If the document has not been indexed (chunk count shows "not indexed"), click **Index this document**. This runs the full ingestion pipeline: text/vision extraction, hierarchical chunking, embedding, ChromaDB indexing, and LLM description generation.

### Mode A — Summariser

Select a document and click **Summarise Document**. No text input is required. The full document text is passed directly to the LLM. Output is structured Markdown with Executive Summary, Key Points, Risks, and Obligations sections.

### Mode B — Clause Classifier

Select a document and click **Extract and Classify Clauses**. The model identifies clauses by type, assigns a confidence level, and includes a verbatim excerpt with the nearest section citation.

### Mode C — Case Law IRAC

Type a legal question in the input box. Optionally select a document in the sidebar to scope retrieval to that document only; if no document is selected, the search runs across all indexed documents.

- Factual questions (who, what, how much, which section) receive a direct 1–3 sentence answer with a source citation.
- Analytical questions (whether X is permitted, what are the obligations if Y, analyse clause Z) receive a full IRAC-structured response.

### Mode D — Case Agentic Q&A

1. Navigate to the **Cases** page and create a case.
2. Open the case and add documents (any mix of PDFs, images, and text files, all previously indexed).
3. Ask a question in the chat interface. The two-stage routing agent will:
   - Compute semantic similarity between the query and each document's LLM-generated description
   - Call `gemma4:latest` to select the most relevant documents (up to 4)
   - Run per-document hybrid search and cross-document RRF fusion
4. The response includes an expandable **Agent Trace** panel showing which documents were selected and the routing reasoning.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Obtain JWT tokens |
| POST | `/api/v1/auth/token/refresh` | Refresh access token |
| GET | `/api/v1/documents` | List uploaded documents |
| POST | `/api/v1/documents/upload` | Upload a document (PDF / image / TXT / MD) |
| GET | `/api/v1/documents/{id}` | Document detail |
| DELETE | `/api/v1/documents/{id}/delete` | Delete a document and its chunks |
| POST | `/api/v1/documents/{id}/describe` | (Re-)generate LLM routing description |
| GET | `/api/v1/cases` | List user's cases |
| POST | `/api/v1/cases` | Create a case |
| GET | `/api/v1/cases/{id}` | Case detail with documents |
| PATCH | `/api/v1/cases/{id}` | Update case title / description |
| DELETE | `/api/v1/cases/{id}` | Delete a case (not its documents) |
| POST | `/api/v1/cases/{id}/documents` | Add documents to a case |
| DELETE | `/api/v1/cases/{id}/documents/{doc_id}` | Remove a document from a case |
| POST | `/api/v1/ingest` | Chunk, embed, and index a document |
| POST | `/api/v1/ingest/batch` | Batch ingest multiple documents |
| POST | `/api/v1/chat` | Send a chat message (Modes A/B/C/D, streaming or non-streaming) |
| GET | `/api/v1/history` | List past chat sessions |
| POST | `/api/v1/search` | Direct vector + BM25 search (debug) |
| GET | `/api/v1/rag/stats` | Vector store statistics |
| GET | `/api/v1/health/check` | Model and service health |

All endpoints except `/auth/register`, `/auth/login`, and `/auth/token/refresh` require a `Bearer` JWT token in the `Authorization` header.

### Streaming chat (Modes A–D)

`stream: true` uses Server-Sent Events. The `start` event for Mode D includes the agent trace:

```
data: {"type": "start", "mode": "D", "tokens_in": 892, "agent_trace": {"total_docs": 5, "selected_docs": [...], "routing_reasoning": "..."}}
data: {"type": "token", "token": "The "}
data: {"type": "token", "token": "termination "}
...
data: {"type": "done", "disclaimer": "...", "chat_log_id": 87}
```

### Mode D chat request body

```json
{
  "mode": "D",
  "message": "What are the notice requirements for termination?",
  "case_id": 3,
  "stream": true
}
```

---

## Supported File Types

| Format | Ingestion method | Notes |
|---|---|---|
| PDF (digital) | pymupdf text extraction, per page | Full text and table extraction |
| PDF (scanned) | pymupdf renders page → qwen2.5vl:7b OCR | Per-page OCR fallback when text < 50 chars |
| PNG / JPG / JPEG / TIFF / BMP / WEBP / GIF | qwen2.5vl:7b vision extraction | Handles typed text, handwriting, tables, diagrams |
| TXT | Plain text read (UTF-8) | |
| MD | Plain text read (UTF-8) | Markdown headings parsed natively by hierarchical chunker |
