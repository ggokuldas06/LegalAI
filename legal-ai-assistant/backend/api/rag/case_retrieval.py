# api/rag/case_retrieval.py
from typing import List, Dict, Optional, Tuple
import logging

from ..models import Case, Document
from .embeddings import embedding_service
from .chroma_store import get_vector_store
from .doc_router import doc_router

logger = logging.getLogger(__name__)


def _rrf(ranked_lists: List[List[str]], k: int = 60) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion across multiple ranked chunk-id lists."""
    scores: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, id_ in enumerate(ranked):
            scores[id_] = scores.get(id_, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class CaseRetrievalService:
    """
    Agentic RAG retrieval for a Case:
      1. Embed the query
      2. DocRouter selects which documents are relevant
      3. Run hybrid search within each selected document
      4. Cross-document RRF fusion
      5. Return top-k passages with agent trace metadata
    """

    def __init__(self):
        self.embedding_service = embedding_service
        self.vector_store = get_vector_store()

    def retrieve_for_case(
        self,
        query: str,
        case_id: int,
        user_id: int,
        k: int = 8,
        per_doc_k: int = 6,
    ) -> Dict:
        """
        Returns:
          {
            "passages": [...],          # top-k chunks across all selected docs
            "agent_trace": {
              "total_docs": N,
              "selected_docs": [{"id": ..., "title": ..., "reasoning": ...}, ...],
              "confidence": "high"|"medium"|"low"
            }
          }
        """
        try:
            case = Case.objects.get(id=case_id, user_id=user_id)
        except Case.DoesNotExist:
            logger.error(f"Case {case_id} not found for user {user_id}")
            return {"passages": [], "agent_trace": {"error": "Case not found"}}

        docs = list(case.documents.filter(chunks__isnull=False).distinct())
        if not docs:
            logger.warning(f"Case {case_id} has no indexed documents")
            return {"passages": [], "agent_trace": {"total_docs": 0, "selected_docs": []}}

        # Step 1: embed query
        query_embedding = self.embedding_service.encode_single(query)

        # Step 2: agent routes to relevant docs
        routed = doc_router.route(
            query=query,
            query_embedding=query_embedding,
            case_documents=docs,
            max_docs=4,
        )

        # Build agent trace
        doc_map = {d.id: d for d in docs}
        selected_doc_infos = []
        selected_doc_ids = []
        reasoning_str = ""
        for doc_id, reasoning in routed:
            if doc_id in doc_map:
                selected_doc_ids.append(doc_id)
                selected_doc_infos.append({
                    "id": doc_id,
                    "title": doc_map[doc_id].title,
                    "file_type": doc_map[doc_id].file_type,
                    "reasoning": reasoning,
                })
                if not reasoning_str:
                    reasoning_str = reasoning

        if not selected_doc_ids:
            # Fallback: use all docs
            selected_doc_ids = [d.id for d in docs]
            selected_doc_infos = [
                {"id": d.id, "title": d.title, "file_type": d.file_type, "reasoning": "fallback (no routing result)"}
                for d in docs
            ]

        logger.info(f"Case {case_id}: routing selected {len(selected_doc_ids)} of {len(docs)} docs")

        # Step 3: per-doc hybrid search
        per_doc_ranked: List[List[str]] = []
        all_chunk_results: Dict[str, Dict] = {}

        for doc_id in selected_doc_ids:
            results = self.vector_store.search(
                query_embedding=query_embedding,
                query_text=query,
                k=per_doc_k,
                filters={"document_id": doc_id},
            )
            ranked_ids = [r["chunk_id"] for r in results]
            per_doc_ranked.append(ranked_ids)
            for r in results:
                all_chunk_results[r["chunk_id"]] = r

        # Step 4: cross-doc RRF
        fused = _rrf(per_doc_ranked)
        top_ids = [id_ for id_, _ in fused[:k]]

        # Step 5: assemble passages
        id_to_score = {id_: score for id_, score in fused}
        passages = []
        for chunk_id in top_ids:
            if chunk_id not in all_chunk_results:
                continue
            r = all_chunk_results[chunk_id].copy()
            r["score"] = id_to_score.get(chunk_id, 0.0)
            passages.append({
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
                "file_type": r.get("file_type", "pdf"),
                "text": r.get("text", ""),
                "score": r["score"],
            })

        agent_trace = {
            "total_docs": len(docs),
            "selected_docs": selected_doc_infos,
            "routing_reasoning": reasoning_str,
        }

        logger.info(f"Case {case_id}: returning {len(passages)} passages from {len(selected_doc_ids)} docs")
        return {"passages": passages, "agent_trace": agent_trace}


case_retrieval_service = CaseRetrievalService()
