# api/rag/retrieval.py
from typing import List, Dict, Optional
import logging

from .embeddings import embedding_service
from .chroma_store import get_vector_store

logger = logging.getLogger(__name__)


class RetrievalService:
    """Hybrid BM25 + vector retrieval with Reciprocal Rank Fusion."""

    def __init__(self):
        self.embedding_service = embedding_service
        self.vector_store = get_vector_store()

    def retrieve(
        self,
        query: str,
        k: int = 8,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Retrieve relevant chunks using hybrid search.

        Returns list of chunk dicts with text, heading, section_path, score, and
        full citation metadata (title, year, jurisdiction, source).
        """
        try:
            query_embedding = self.embedding_service.encode_single(query)

            results = self.vector_store.search(
                query_embedding=query_embedding,
                query_text=query,
                k=k,
                filters=filters,
            )

            formatted = []
            for r in results:
                formatted.append({
                    "chunk_id": r.get("chunk_id"),
                    "document_id": r.get("document_id"),
                    "title": r.get("title", "Untitled"),
                    "case_name": r.get("title", "Unknown"),
                    "year": r.get("year") or "n.d.",
                    "jurisdiction": r.get("jurisdiction", ""),
                    "source": r.get("source", ""),
                    "heading": r.get("heading", ""),
                    "section_path": r.get("section_path", ""),
                    "node_type": r.get("node_type", "text"),
                    "text": r.get("text", ""),
                    "score": r.get("score", 0.0),
                })

            logger.info(f"Retrieved {len(formatted)} chunks (hybrid RRF) for query")
            return formatted

        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)
            return []

    def retrieve_for_mode_c(
        self,
        question: str,
        document_id: Optional[int] = None,
        jurisdiction: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        keywords_include: Optional[List[str]] = None,
        keywords_exclude: Optional[List[str]] = None,
        k: int = 6,
    ) -> List[Dict]:
        filters: Dict = {}
        if document_id:
            filters["document_id"] = document_id
        if jurisdiction:
            filters["jurisdiction"] = jurisdiction
        if year_from:
            filters["year_from"] = year_from
        if year_to:
            filters["year_to"] = year_to

        results = self.retrieve(query=question, k=k, filters=filters or None)

        # Post-filter keyword include/exclude (not supported natively in Chroma)
        if keywords_include:
            kw = [w.lower() for w in keywords_include]
            results = [r for r in results if any(w in r["text"].lower() for w in kw)]
        if keywords_exclude:
            kw = [w.lower() for w in keywords_exclude]
            results = [r for r in results if not any(w in r["text"].lower() for w in kw)]

        return results


retrieval_service = RetrievalService()
