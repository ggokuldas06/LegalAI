# **LegalAI – Offline Legal Assistant with Local LLM Inference**

LegalAI is a privacy-oriented, fully offline legal assistant designed for organizations requiring secure, local processing of sensitive legal data.
It combines a Vue.js frontend, a Django REST Framework backend, and an on-device LLaMA-2 inference pipeline (via llama-cpp-python).
The system provides structured legal reasoning, citation-backed outputs, document analysis, and optional local RAG — without making any external network calls.

---

## **1. Overview**

Modern legal AI systems often rely on cloud LLMs, creating confidentiality and compliance risks. LegalAI addresses this challenge by running entirely on local hardware, using quantized LLaMA models and domain-specific LoRA adapters.
It provides three core capabilities:

1. **A — Legal Document Summarization**
   Multi-layer executive summaries, obligations, risks, and citations.

2. **B — Clause Detection and Classification**
   Identification of key contract clauses with highlighted excerpts and confidence scores.

3. **C — Case-Law IRAC Reasoning**
   Structured IRAC responses with precise citations, filters, and legal grounding.

LegalAI emphasizes privacy, explainability, structured reasoning, and robust offline operation suitable for audit-intensive environments.

---

## **2. System Architecture**

### **Frontend Layer**

**Technologies:** Vue.js 3, Bootstrap
**Key Features:**

* Chat interface with support for modes A/B/C
* Real-time response streaming (token-by-token)
* JWT authentication (login & register)
* Conversation history with filtering and export
* Document picker and uploader with progress tracking
* Mode-specific result viewers:

  * **A:** Summary cards + JSON export
  * **B:** Clause list with excerpt highlighting
  * **C:** IRAC answer panel with citations and filters

---

### **Backend Layer**

**Framework:** Django REST Framework

**Core Endpoints**

* `POST /api/v1/auth/login` — JWT login
* `POST /api/v1/auth/register` — local user registration
* `POST /api/v1/chat` — streaming LLM responses (A/B/C modes)
* `GET /api/v1/history` — retrieve conversation logs
* `GET /api/v1/health/check` — health and readiness check
* **Optional RAG:**

  * `POST /api/v1/ingest` — upload/parse/chunk/embed documents
  * `POST /api/v1/search` — semantic/keyword search

**Middleware**

* JWT authentication
* Rate limiting
* CORS
* Structured logging (tokens, latency, citation count)

**Background Tasks**

* Celery workers for LLM batch jobs, document ingestion, embedding
* Redis as broker/backend

---

### **LLM Inference Layer**

**Runtime:** `llama-cpp-python` (CPU-only, offline)
**Model:** LLaMA-2-7B-Chat, quantized **Q4_K_M GGUF**
**Context Window:** 4096 tokens
**Threads:** 8 CPU threads
**LoRA Fine-Tuning:**

* Legal tone
* Structured reasoning
* Citation-focused behavior
  Loaded at runtime or merged into GGUF weights.

**Sampling Defaults**

```
temperature=0.7  
top_p=0.9  
top_k=50  
max_tokens=256  
streaming=True
```

---

### **Storage Layer**

**Database:** SQLite
**Stored Data:**

* Users & JWT tokens
* Conversation history
* Structured logs
* Legal corpus (documents, chunks, embeddings)

---

## **3. Feature Suite**

### **LegalAI’s Three Modes**

1. **A — Summarization**
   Multi-layer legal summaries with citations, risks, obligations, and executive bullets.

2. **B — Clause Classification**
   Identify and extract clauses such as:

   * Indemnity
   * Termination
   * Confidentiality
   * Limitation of Liability
   * IP Rights
   * Governing Law

3. **C — Case-Law IRAC Q&A**
   IRAC-structured reasoning, grounded in retrieved passages, jurisdiction/year filters, and mandatory citations.

---

## **4. Requirements and Non-Functional Constraints**

### **Primary Goals**

* Structured, citation-backed legal outputs
* JSON-valid responses for modes A/B
* Fast inference on CPU-only hardware
* Full offline capability with zero external calls

### **Success Criteria**

* P50 latency ≤ 3s for 50-token answers (CPU, Q4_K_M quant)
* JSON validity ≥ 95% (A/B)
* Clause extraction F1 ≥ 0.75
* C-mode: ≥ 90% sentences with citations; retrieval nDCG@10 ≥ 0.6
* Privacy compliance: No outbound network traffic

### **Non-Functional Requirements**

* Offline-first
* Privacy-preserving
* Auditable logging
* Portable across Linux/Windows
* Graceful fallback if LoRA not available

---

## **5. Users & Stakeholders**

* Legal teams and analysts
* Contract management groups
* Compliance and audit teams
* Researchers evaluating legal reasoning systems
* Administrators of secure/offline deployments

---

## **6. Functional Specification**

### **6.1 API Endpoints**

#### **Authentication**

* `POST /api/v1/auth/login`
* `POST /api/v1/auth/register`

#### **Chat**

* `POST /api/v1/chat`
  Body example:

```
{
  "mode": "C",
  "message": "What is the EU standard for injunctions?",
  "filters": { "jurisdiction": "EU", "year_from": 2015 }
}
```

#### **History**

* `GET /api/v1/history?mode=&limit=&offset=`

#### **RAG (Optional, Admin)**

* `POST /api/v1/ingest`
* `POST /api/v1/search`

---

### **6.2 Backend Behaviors**

* Strict prompt templates for A/B/C
* Citation-first reply logic
* Refusal mode if grounding is insufficient
* Streaming via SSE or chunked responses

### **6.3 Inference Details**

* Loaded using `llama_cpp.Llama()`
* LoRA applied at runtime or merged + quantized

---

## **7. Fine-Tuning Plan (PEFT / LoRA)**

### **Training Data Composition**

* **A (≈400 examples):** Legal summaries with citations
* **B (≈600 examples):** Clause classification with excerpts
* **C (≈300 examples):** IRAC reasoning with grounded source text

### **Training Setup**

* Base model: `LLaMA-2-7B-Chat HF`
* QLoRA (4-bit)
* Target modules: q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj

### **Export Options**

* Runtime LoRA adapters (llama.cpp compatible)
* Merged → GGUF → quantized Q4_K_M

---

## **8. Architecture Summary**

* **Frontend:** Vue 3, Bootstrap
* **Backend:** Django REST Framework, JWT, CORS, rate limit
* **Background:** Celery, Redis
* **Inference:** llama-cpp-python, LLaMA-2-7B (Q4_K_M)
* **Storage:** SQLite + local corpus directory

---

## **9. Security, Privacy, and Safety**

* No external network access
* Strict JWT handling
* Rate limiting per user
* Redacted logging for sensitive content
* Automatic legal disclaimer appended to responses
* Strict file type validation for document ingestion

---

## **10. Testing & Evaluation**

### **Unit Tests**

* Tokenization
* Prompt builder (A/B/C)
* Citation checker
* RAG retrieval
* Rate limiting

### **Performance Tests**

* Model load time < 10s
* p50/p95 latency tracking

### **Quality Metrics**

* JSON validity
* Hallucination checks
* Clause extraction F1
* IRAC citation coverage
* Retrieval ranking metrics

---

## **11. Deliverables**

* Frontend + backend source code
* Finetuned LoRA adapters
* Optional merged quantized GGUF model
* Admin guide (deployment, ingestion, backups)
* Evaluation and benchmarking report
* Privacy & safety specification

---

## **12. Abstract**

LegalAI is an offline, privacy-oriented legal assistant designed for organizations handling sensitive legal data. It integrates a Vue.js frontend and a Django REST Framework backend, providing interactive chat capabilities for legal summarization, clause detection, and case-law reasoning using LLaMA-2 via llama-cpp-python. Domain-specific LoRA tuning enhances legal tone, structure, and citation accuracy.

Most existing legal AI solutions rely on cloud-based models, raising concerns around confidentiality and data governance. LegalAI operates entirely offline, offering organizations full data control. It emphasizes structured reasoning, source citations, and verifiable outputs, making it suitable for compliance-intensive settings.

Users can upload contracts or case documents, stream model responses, and export structured JSON results. The backend supports authentication, rate limiting, logging, and Celery-based asynchronous tasks. Optional RAG enables grounded reasoning over a local corpus.

LegalAI prioritizes privacy, explainability, and accuracy, producing citation-backed responses with no external dependencies. It provides a practical and auditable platform for legal analysis, research, and internal decision support.

