# api/rag/doc_router.py
import json
import logging
import re
from typing import List, Tuple, Optional

import httpx
import numpy as np

from ..models import Document
from .embeddings import embedding_service

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
ROUTER_MODEL = "gemma4:latest"

_ROUTER_SYSTEM = (
    "You are a document routing agent. "
    "Given a legal query and descriptions of available documents, "
    "select which documents are relevant to answering the query. "
    "Output ONLY valid JSON — no markdown fences, no explanation."
)

_ROUTER_USER_TEMPLATE = """Query: {query}

Available Documents:
{doc_list}

Select the documents that contain information relevant to answering this query.
Output JSON exactly in this format:
{{
  "selected_indices": [<1-based index>, ...],
  "reasoning": "<brief explanation of why these documents were chosen>",
  "confidence": "high" | "medium" | "low"
}}

Rules:
- Use 1-based indices matching the list above
- Include ALL documents that could partially answer the query
- When uncertain, include rather than exclude
- Maximum 4 documents
- If no document is relevant, return an empty list"""


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _parse_router_json(text: str) -> Optional[dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


class DocRouter:
    """
    Two-stage document routing agent:
      Stage 1 — semantic pre-filter (cosine similarity against description embedding)
      Stage 2 — LLM judge picks from pre-filtered candidates

    Falls back to semantic pre-filter results if LLM fails.
    """

    SEMANTIC_CANDIDATES = 6   # How many docs pass to LLM stage
    MAX_SELECTED = 4          # Hard cap on selected docs

    def route(
        self,
        query: str,
        query_embedding: np.ndarray,
        case_documents: List[Document],
        max_docs: int = 4,
    ) -> List[Tuple[int, str]]:
        """
        Returns list of (document_id, reasoning) tuples, ordered by relevance.
        Falls back gracefully if LLM routing fails.
        """
        if not case_documents:
            return []

        # Stage 1: semantic pre-filter
        candidates = self._semantic_prefilter(query_embedding, case_documents)
        logger.info(f"DocRouter: {len(candidates)} semantic candidates from {len(case_documents)} docs")

        if not candidates:
            return [(doc.id, "semantic fallback") for doc in case_documents[:max_docs]]

        # Stage 2: LLM routing
        try:
            selected = self._llm_route(query, candidates, max_docs)
            if selected:
                logger.info(f"DocRouter: LLM selected {len(selected)} docs")
                return selected
        except Exception as e:
            logger.warning(f"DocRouter LLM stage failed, using semantic fallback: {e}")

        # Fallback: return semantic candidates ordered by score
        return [(doc.id, f"semantic score {score:.3f}") for doc, score in candidates[:max_docs]]

    # ------------------------------------------------------------------
    # Stage 1 — semantic pre-filter
    # ------------------------------------------------------------------

    def _semantic_prefilter(
        self,
        query_embedding: np.ndarray,
        documents: List[Document],
    ) -> List[Tuple[Document, float]]:
        """Score each document by cosine similarity between query and description embedding."""
        scored = []
        for doc in documents:
            if not doc.doc_description:
                # No description yet — include with neutral score
                scored.append((doc, 0.5))
                continue
            try:
                desc_data = json.loads(doc.doc_description)
                # Build a rich text representation of the description for embedding
                desc_text = " ".join([
                    desc_data.get("summary", ""),
                    " ".join(desc_data.get("topics", [])),
                    desc_data.get("document_type_detail", ""),
                    doc.title,
                ])
                desc_emb = embedding_service.encode_single(desc_text)
                sim = _cosine_similarity(query_embedding, desc_emb)
                scored.append((doc, sim))
            except Exception as e:
                logger.debug(f"Could not score doc {doc.id}: {e}")
                scored.append((doc, 0.3))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:self.SEMANTIC_CANDIDATES]

    # ------------------------------------------------------------------
    # Stage 2 — LLM routing judge
    # ------------------------------------------------------------------

    def _llm_route(
        self,
        query: str,
        candidates: List[Tuple[Document, float]],
        max_docs: int,
    ) -> List[Tuple[int, str]]:
        doc_lines = []
        for i, (doc, score) in enumerate(candidates, 1):
            desc = self._format_description(doc)
            doc_lines.append(f"[{i}] Title: {doc.title}\n    Type: {doc.doctype} | File: {doc.file_type}\n    {desc}")

        doc_list_str = "\n\n".join(doc_lines)
        user_msg = _ROUTER_USER_TEMPLATE.format(query=query, doc_list=doc_list_str)

        payload = {
            "model": ROUTER_MODEL,
            "messages": [
                {"role": "system", "content": _ROUTER_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            "stream": False,
            "options": {"num_predict": 512, "temperature": 0.1},
        }

        with httpx.Client(timeout=90.0) as client:
            resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
        raw = resp.json()["message"]["content"]

        parsed = _parse_router_json(raw)
        if not parsed or "selected_indices" not in parsed:
            raise ValueError(f"Router returned invalid JSON: {raw[:200]}")

        reasoning = parsed.get("reasoning", "")
        indices = parsed.get("selected_indices", [])

        # Validate and convert 1-based indices to document_ids
        result = []
        seen = set()
        for idx in indices:
            if not isinstance(idx, int):
                continue
            if idx < 1 or idx > len(candidates):
                continue
            doc, _ = candidates[idx - 1]
            if doc.id not in seen:
                result.append((doc.id, reasoning))
                seen.add(doc.id)

        return result[:max_docs]

    def _format_description(self, doc: Document) -> str:
        if not doc.doc_description:
            return "(no description available)"
        try:
            data = json.loads(doc.doc_description)
            return data.get("summary", "(no summary)")
        except Exception:
            return doc.doc_description[:200]


doc_router = DocRouter()
